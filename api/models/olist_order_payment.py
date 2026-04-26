from sqlalchemy import String, Integer, Float,  ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base

class OrderPayment(Base):
    __tablename__ = "olist_order_payments"

    # Composite Primary Key tương tự bảng Items
    order_id: Mapped[str] = mapped_column(ForeignKey("olist_orders.order_id"), primary_key=True)
    payment_sequential: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    payment_type: Mapped[str] = mapped_column(String(20))
    payment_installments: Mapped[int] = mapped_column(Integer)
    payment_value: Mapped[float] = mapped_column(Float)

    # Relationship
    order: Mapped["Order"] = relationship(back_populates="payments")