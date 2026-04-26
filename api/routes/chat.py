from fastapi import APIRouter, Depends, HTTPException, File
from sqlalchemy.orm import Session
from typing import List

from core.postgres import get_db
from api.models.chat_box import ChatBox
from api.models.message import Message

from api.deps import get_current_active_user
from api.schemas.chat import ChatBoxResponse, MessageResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatBoxResponse)
def create_new_chat(db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    new_chat = ChatBox(user_id=current_user.id, title="Cuộc trò chuyện mới")
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat

@router.get("/", response_model=List[ChatBoxResponse])
def get_user_chats(db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    return db.query(ChatBox).filter(ChatBox.user_id == current_user.id).order_by(ChatBox.created_at.desc()).all()

@router.get("/{chatbox_id}/messages", response_model=List[MessageResponse])
def get_chat_history(chatbox_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    chat = db.query(ChatBox).filter(ChatBox.id == chatbox_id, ChatBox.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")
    
    return db.query(Message).filter(Message.chatbox_id == chatbox_id).order_by(Message.created_at.asc()).all()