from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from typing import List

from api.models.base import Base

class Customer(Base):
    __tablename__ = "olist_customers"

    customer_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_unique_id: Mapped[str] = mapped_column(String(50), index=True)
    customer_zip_code_prefix: Mapped[str] = mapped_column(String(10))
    customer_city: Mapped[str] = mapped_column(String(100))
    customer_state: Mapped[str] = mapped_column(String(2))

    # Relationship ngược lại với Orders
    orders: Mapped[List["Order"]] = relationship(back_populates="customer")


    