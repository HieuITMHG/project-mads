from sqlalchemy import Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from api.models.base import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_file_id: Mapped[int] = mapped_column(ForeignKey("session_files.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict] = mapped_column(JSON, nullable=True) 
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)