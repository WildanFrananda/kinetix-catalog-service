from dataclasses import dataclass
from typing import List

from core.domain.entities import Product


@dataclass(frozen=True)
class MerchantProductListResultDTO:
    count: int
    page: int
    page_size: int
    results: List[Product]
