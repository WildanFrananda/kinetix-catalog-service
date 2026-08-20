from dataclasses import dataclass
from typing import Optional
from core.domain.entities.money import Money

@dataclass(frozen=True)
class OrderItem:
    sku: str
    product_name: str
    quantity: int
    price: Money
    bin_location: Optional[str] = None
