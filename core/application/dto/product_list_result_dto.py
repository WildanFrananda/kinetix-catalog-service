from dataclasses import dataclass
from typing import List
from core.application.dto.product_summary_dto import ProductSummaryDTO

@dataclass(frozen=True)
class ProductListResultDTO:
    count: int
    page: int
    page_size: int
    results: List[ProductSummaryDTO]
