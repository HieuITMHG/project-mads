from api.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, func, ForeignKey, UniqueConstraint
from datetime import datetime

class SessionFile(Base):
    __tablename__ = "session_files"
    """
    Bảng này giải quyết bài toán CÔ LẬP FILE.
    Một file vật lý có thể nằm ở nhiều Chatbox khác nhau với tên gọi khác nhau do User đặt.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chatbox_id: Mapped[int] = mapped_column(ForeignKey("chatboxes.id", ondelete="CASCADE"), nullable=False)
    physic_file_id: Mapped[int] = mapped_column(ForeignKey("physic_files.id", ondelete="RESTRICT"), nullable=False)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False) # Tên file hiển thị cho user
    status: Mapped[str] = mapped_column(String(50), default="PENDING") # PENDING, EMBEDDING, READY, FAILED
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # RÀNG BUỘC CỰC QUAN TRỌNG: 1 file vật lý không được add 2 lần vào cùng 1 chatbox
    __table_args__ = (
        UniqueConstraint('chatbox_id', 'physic_file_id', name='uix_chatbox_physic_file'),
    )