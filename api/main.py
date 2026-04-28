from fastapi import FastAPI
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    ensure_bucket_exists(settings.olist_data)
    ensure_bucket_exists(settings.upload_bucket)
    yield

app = FastAPI(title="MADS APP", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(user.router)
app.include_router(doc.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "running"}