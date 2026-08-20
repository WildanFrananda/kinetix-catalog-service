from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ProductFilterDTO:
    category_slug: Optional[str] = None
    search_query: Optional[str] = None
    page: int = 1
    page_size: int = 10
