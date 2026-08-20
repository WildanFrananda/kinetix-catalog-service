from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import datetime
from core.domain.entities.category import Category
from core.domain.entities.stock_info import StockInfo

@dataclass(frozen=True)
class Product:
    id: Optional[int]
    sku: str
    title: str
    description: str
    price: Decimal
    currency: str
    image_url: str
    category: Category
    stock_info: Optional[StockInfo] = None
    created_at: Optional[datetime] = None
