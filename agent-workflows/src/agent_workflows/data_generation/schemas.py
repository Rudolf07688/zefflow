"""Sample row schemas. Add your own here."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class Customer(BaseModel):
    customer_id: int = Field(ge=1)
    full_name: str
    email: EmailStr
    country: str
    signup_date: date
    tier: Literal["free", "pro", "enterprise"]


class Product(BaseModel):
    product_id: int = Field(ge=1)
    sku: str
    name: str
    category: Literal["hardware", "software", "service", "subscription"]
    unit_price: Decimal = Field(decimal_places=2)
    in_stock: bool


class Order(BaseModel):
    order_id: int = Field(ge=1)
    customer_id: int
    product_id: int
    quantity: int = Field(ge=1)
    order_total: Decimal = Field(decimal_places=2)
    placed_at: datetime
    status: Literal["pending", "shipped", "delivered", "cancelled"]
