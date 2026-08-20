from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class OrderItemDTO:
    sku: str
    product_name: str
    quantity: int
    price: Decimal
