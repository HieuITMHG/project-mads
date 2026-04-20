from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from typing import List

from models.base import Base

class Seller(Base):
    __tablename__ = "olist_sellers"

    seller_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    seller_zip_code_prefix: Mapped[str] = mapped_column(String(10))
    seller_city: Mapped[str] = mapped_column(String(100))
    seller_state: Mapped[str] = mapped_column(String(2))

    # Relationship
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="seller")