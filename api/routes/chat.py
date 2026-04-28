from fastapi import APIRouter, Depends, HTTPException, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from core.postgres import get_db
from api.models.chat_box import ChatBox
from api.models.message import Message

from api.deps import get_current_active_user
from api.schemas.chat import ChatBoxResponse, MessageResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatBoxResponse)
async def create_new_chat(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    new_chat = ChatBox(user_id=current_user.id, title="Cuộc trò chuyện mới")
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return new_chat

@router.get("/", response_model=List[ChatBoxResponse])
async def get_user_chats(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    result = await db.execute(select(ChatBox).filter(ChatBox.user_id == current_user.id).order_by(ChatBox.created_at.desc()))
    return result.scalars().all()

@router.get("/{chatbox_id}/messages", response_model=List[MessageResponse])
async def get_chat_history(chatbox_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    chat_req = await db.execute(select(ChatBox).filter(ChatBox.id == chatbox_id, ChatBox.user_id == current_user.id))
    chat = chat_req.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")
    
    msgs_req = await db.execute(select(Message).filter(Message.chatbox_id == chatbox_id).order_by(Message.created_at.asc()))
    return msgs_req.scalars().all()