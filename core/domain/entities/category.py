from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Category:
    id: Optional[int]
    name: str
    slug: str
