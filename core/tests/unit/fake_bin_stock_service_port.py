from typing import Any, Dict

from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

class FakeBinStockServicePort(BinStockServicePort):
    def __init__(self) -> None:
        self.principals_seen: list[str] = []

    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        self.principals_seen.append(merchant_principal_id)
        return StockInfo(
            sku=sku, bin_location="Bin A-04", available_quantity=30, reserved_quantity=2
        )

    def reserve_stock(self, sku: str, quantity: int, merchant_principal_id: str) -> Dict[str, Any]:
        self.principals_seen.append(merchant_principal_id)
        return {"success": True, "bin_location": "Bin A-04", "remaining_available": 28}
