from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class ProductSummaryDTO:
    id: int
    sku: str
    title: str
    category: str
    price: Decimal
    currency: str
    image_url: str
    available_stock: int
    is_in_stock: bool
