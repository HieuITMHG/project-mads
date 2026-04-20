from api.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, func, ForeignKey
from datetime import datetime

class ChatBox(Base):
    __tablename__ = "chatboxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Quan hệ
    messages = relationship("Message", backref="chatbox", cascade="all, delete-orphan")
    session_files = relationship("SessionFile", backref="chatbox", cascade="all, delete-orphan")