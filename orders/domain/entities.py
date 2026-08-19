from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True)
class Money:
    currency: str
    amount: Decimal

@dataclass(frozen=True)
class Address:
    recipient_name: str
    phone_number: str
    street_address: str
    city: str
    postal_code: str

@dataclass(frozen=True)
class OrderItem:
    sku: str
    product_name: str
    quantity: int
    price: Money
    bin_location: Optional[str] = None

@dataclass(frozen=True)
class Order:
    id: Optional[int]
    order_number: str
    buyer_name: str
    buyer_phone: str
    shipping_address: Address
    total_amount: Money
    items: List[OrderItem]
    status: str
    created_at: Optional[datetime] = None
