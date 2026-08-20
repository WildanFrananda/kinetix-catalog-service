from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class StockInfo:
    sku: str
    bin_location: str
    available_quantity: int
    reserved_quantity: int
    last_synced_at: Optional[datetime] = None
