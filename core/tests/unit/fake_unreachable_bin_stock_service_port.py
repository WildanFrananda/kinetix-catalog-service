from typing import Dict, Sequence

from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

class FakeUnreachableBinStockServicePort(BinStockServicePort):
    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        return StockInfo.unknown(sku)

    def get_bin_stock_for(
        self, skus: Sequence[str], merchant_principal_id: str
    ) -> Dict[str, StockInfo]:
        return {sku: StockInfo.unknown(sku) for sku in skus}
