from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class Geolocation(Base):
    __tablename__ = "olist_geolocation"

    # Bảng này trong data thực tế có nhiều dòng trùng zip_code (do nhiều tọa độ). 
    # Bắt buộc phải tạo thêm 1 surrogate key (id tự tăng) cho PostgreSQL.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geolocation_zip_code_prefix: Mapped[str] = mapped_column(String(10), index=True)
    geolocation_lat: Mapped[float] = mapped_column(Float)
    geolocation_lng: Mapped[float] = mapped_column(Float)
    geolocation_city: Mapped[str] = mapped_column(String(100))
    geolocation_state: Mapped[str] = mapped_column(String(2))

