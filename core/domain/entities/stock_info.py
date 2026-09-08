from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class StockInfo:
    sku: str
    bin_location: Optional[str]
    available_quantity: Optional[int]
    reserved_quantity: Optional[int]
    last_synced_at: Optional[datetime] = None

    @staticmethod
    def unknown(sku: str) -> "StockInfo":
        return StockInfo(
            sku=sku, bin_location=None, available_quantity=None, reserved_quantity=None
        )
