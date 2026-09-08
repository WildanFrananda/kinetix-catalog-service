from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from core.domain.entities.stock_status import StockStatus

@dataclass(frozen=True)
class ProductSummaryDTO:
    id: int
    sku: str
    title: str
    category: str
    price: Decimal
    currency: str
    image_url: str
    available_stock: Optional[int]
    is_in_stock: Optional[bool]
    stock_status: StockStatus
