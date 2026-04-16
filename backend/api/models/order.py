from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import  Mapped, mapped_column, relationship

from models.base import Base

class Order(Base):
    __tablename__ = "olist_orders"

    order_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("olist_customers.customer_id"))
    order_status: Mapped[str] = mapped_column(String(20))
    
    # Các mốc thời gian (có thể null nếu đơn bị hủy hoặc chưa giao)
    order_purchase_timestamp: Mapped[datetime] = mapped_column(DateTime)
    order_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    order_delivered_carrier_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    order_delivered_customer_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    order_estimated_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order")
    payments: Mapped[List["OrderPayment"]] = relationship(back_populates="order")