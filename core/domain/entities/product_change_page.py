from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.domain.entities.product import Product


@dataclass(frozen=True)
class ProductChangePage:
    upserted: List[Product]
    removed_skus: List[str]
    next_updated_through: Optional[datetime]
    next_last_sku: str
    has_more: bool
