from dataclasses import dataclass
from typing import Optional

from core.domain.entities.stock_status import StockStatus

@dataclass(frozen=True)
class WarehouseStockDTO:
    sku: str
    bin_location: Optional[str]
    available_quantity: Optional[int]
    reserved_quantity: Optional[int]
    stock_status: StockStatus
