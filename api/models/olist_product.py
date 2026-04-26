from typing import Optional, List
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base

class Product(Base):
    __tablename__ = "olist_products"

    product_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    product_category_name: Mapped[Optional[str]] = mapped_column(String(100))
    product_name_lenght: Mapped[Optional[int]] = mapped_column(Integer)
    product_description_lenght: Mapped[Optional[int]] = mapped_column(Integer)
    product_photos_qty: Mapped[Optional[int]] = mapped_column(Integer)
    product_weight_g: Mapped[Optional[int]] = mapped_column(Integer)
    product_length_cm: Mapped[Optional[int]] = mapped_column(Integer)
    product_height_cm: Mapped[Optional[int]] = mapped_column(Integer)
    product_width_cm: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationship
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="product")