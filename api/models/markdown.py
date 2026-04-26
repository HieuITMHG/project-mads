from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from api.models.base import Base

class MarkDown(Base):
    __tablename__ = "markdowns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_file_id: Mapped[int] = mapped_column(ForeignKey("session_files.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)