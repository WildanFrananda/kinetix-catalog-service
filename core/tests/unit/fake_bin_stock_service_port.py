from typing import Dict, Any
from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

class FakeBinStockServicePort(BinStockServicePort):
    def get_bin_stock_info(self, sku: str) -> StockInfo:
        return StockInfo(
            sku=sku,
            bin_location="Bin A-04",
            available_quantity=30,
            reserved_quantity=2
        )

    def reserve_stock(self, sku: str, quantity: int) -> Dict[str, Any]:
        return {"success": True, "bin_location": "Bin A-04", "remaining_available": 28}
