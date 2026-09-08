from typing import Any, Dict

from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

class FakeUnreachableBinStockServicePort(BinStockServicePort):
    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        return StockInfo.unknown(sku)

    def reserve_stock(self, sku: str, quantity: int, merchant_principal_id: str) -> Dict[str, Any]:
        return {
            "success": False,
            "unavailable": True,
            "sent": False,
            "error": "warehouse was not called, so no stock was reserved",
        }
