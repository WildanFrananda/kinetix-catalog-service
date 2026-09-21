from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

class FakeBinStockServicePort(BinStockServicePort):
    def __init__(self, available_quantity: int = 30) -> None:
        self.principals_seen: list[str] = []
        self._available_quantity = available_quantity

    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        self.principals_seen.append(merchant_principal_id)
        return StockInfo(
            sku=sku,
            bin_location="Bin A-04",
            available_quantity=self._available_quantity,
            reserved_quantity=2,
        )

