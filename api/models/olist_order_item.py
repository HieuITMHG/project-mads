from datetime import datetime
from sqlalchemy import  Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base

class OrderItem(Base):
    __tablename__ = "olist_order_items"

    # Sử dụng Composite Primary Key (Khóa chính kép) vì một đơn có thể có nhiều item
    order_id: Mapped[str] = mapped_column(ForeignKey("olist_orders.order_id"), primary_key=True)
    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    product_id: Mapped[str] = mapped_column(ForeignKey("olist_products.product_id"))
    seller_id: Mapped[str] = mapped_column(ForeignKey("olist_sellers.seller_id"))
    
    shipping_limit_date: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[float] = mapped_column(Float)
    freight_value: Mapped[float] = mapped_column(Float)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
    seller: Mapped["Seller"] = relationship(back_populates="order_items")