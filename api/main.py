from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat
from api.routes import user
from api.routes import doc

from core.postgres import engine
from api.models.base import Base
from api.models.user import User
from api.models.chat_box import ChatBox
from api.models.message import Message
from api.models.physic_file import PhysicFile
from api.models.session_file import SessionFile

from core.config import settings
from core.minio import ensure_bucket_exists

from contextlib import asynccontextmanager
import core.checkpointer as cp
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from mcp import ClientSession
from mcp.client.sse import sse_client

from langchain_mcp_adapters.tools import load_mcp_tools

from api.agents.graph import build_agent_graph

from contextlib import AsyncExitStack

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    ensure_bucket_exists(settings.olist_data)
    ensure_bucket_exists(settings.upload_bucket)

    CHECKPOINTER_DB_URI = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

    cp.agent_checkpointer_pool = AsyncConnectionPool(
        conninfo=CHECKPOINTER_DB_URI,
        max_size=10, 
        kwargs={"autocommit": True},
        open=False
    )

    await cp.agent_checkpointer_pool.open()

    checkpointer = AsyncPostgresSaver(cp.agent_checkpointer_pool)
    await checkpointer.setup()

    print("Đang lấy danh sách tool từ MCP server")

    mcp_stack = AsyncExitStack()

    try:
        streams = await mcp_stack.enter_async_context(
            sse_client(
                        settings.mcp_server_url,
                        headers={
                                "Accept": "text/event-stream",
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                            },
                        )
        )

        session = await mcp_stack.enter_async_context(
            ClientSession(streams[0], streams[1])
        )

        await session.initialize()

        cp.dynamic_mcp_tools = await load_mcp_tools(session)
        print(f"Đã lấy thành công {len(cp.dynamic_mcp_tools)} tools từ MCP!")
    except Exception as e:
        print(f"Không kết nối được MCP Server: {e}")
        await mcp_stack.aclose()

    graph = build_agent_graph()

    cp.agent_app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["tools"]
    )

    print("agent đã compile thành công")

    yield

    if cp.agent_checkpointer_pool:
        await cp.agent_checkpointer_pool.close()
        print("Đã đóng kết nối Checkpointer Pool an toàn.")

app = FastAPI(title="MADS APP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các origin (bạn có thể thay đổi để bảo mật hơn)
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả HTTP methods (GET, POST, PUT, DELETE, v.v.)
    allow_headers=["*"],  # Cho phép tất cả headers
)

app.include_router(chat.router)
app.include_router(user.router)
app.include_router(doc.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "running"}