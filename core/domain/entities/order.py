from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from core.domain.entities.money import Money
from core.domain.entities.address import Address
from core.domain.entities.order_item import OrderItem

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
