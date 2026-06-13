import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat
from api.routes import user
from api.routes import doc
from api.utils.logging_config import setup_logging, get_logger

# Khởi tạo logging ngay khi module được load
setup_logging()
logger = get_logger(__name__)

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

    logger.info("Đang kết nối MCP server tại: %s", settings.mcp_server_url)

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
        logger.info("Đã load thành công %d tools từ MCP server", len(cp.dynamic_mcp_tools))
        for t in cp.dynamic_mcp_tools:
            logger.debug("  → MCP tool: %s", t.name)
    except Exception as e:
        logger.error("Không kết nối được MCP Server: %s", e, exc_info=True)
        await mcp_stack.aclose()

    graph = build_agent_graph()

    cp.agent_app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["tools"]
    )

    logger.info("Agent graph đã compile thành công (interrupt_before=[tools])")

    yield

    if cp.agent_checkpointer_pool:
        await cp.agent_checkpointer_pool.close()
        logger.info("Đã đóng kết nối Checkpointer Pool an toàn")

app = FastAPI(title="MADS APP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(chat.router)
app.include_router(user.router)
app.include_router(doc.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "running"}