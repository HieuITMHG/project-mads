from api.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, func
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

class PhysicFile(Base):
    __tablename__ = "physic_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False) 
    
    s3_path: Mapped[str] = mapped_column(String, nullable=False) 
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100)) 

    metadata_data: Mapped[dict] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())