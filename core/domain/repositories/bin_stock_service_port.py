from abc import ABC, abstractmethod

from core.domain.entities.stock_info import StockInfo

class BinStockServicePort(ABC):
    @abstractmethod
    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        pass
