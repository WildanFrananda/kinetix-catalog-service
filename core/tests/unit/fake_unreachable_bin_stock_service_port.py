from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

class FakeUnreachableBinStockServicePort(BinStockServicePort):
    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        return StockInfo.unknown(sku)
