from api.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, func, ForeignKey, UniqueConstraint, Text
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

class Message(Base):
    __tablename__ = "messages"
    """
    Gộp Prompt và AI Response vào chung 1 bảng là best practice của các app chat AI.
    Sử dụng cột 'role' để phân biệt ai là người nói.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chatbox_id: Mapped[int] = mapped_column(ForeignKey("chatboxes.id", ondelete="CASCADE"), nullable=False)
    
    role: Mapped[str] = mapped_column(String(20), nullable=False) 
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_data: Mapped[dict] = mapped_column(JSONB, nullable=True) 

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())