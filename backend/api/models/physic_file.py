from api.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, func
from datetime import datetime

class PhysicFile(Base):
    __tablename__ = "physic_files"
    """
    Bảng này giải quyết bài toán CHKSUM / CACHE TỐI ƯU DUNG LƯỢNG.
    Nếu 100 User cùng upload 1 cuốn sách PDF giống hệt nhau, MinIO chỉ lưu 1 bản duy nhất.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Mã băm của file (SHA-256). Đánh index và unique để check trùng lặp cực nhanh
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False) 
    
    s3_path: Mapped[str] = mapped_column(String, nullable=False) # Đường dẫn thật trong MinIO
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100)) # vd: application/pdf

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())