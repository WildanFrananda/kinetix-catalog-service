from abc import ABC, abstractmethod
from typing import Dict, Any
from core.domain.entities.stock_info import StockInfo

class BinStockServicePort(ABC):
    @abstractmethod
    def get_bin_stock_info(self, sku: str) -> StockInfo:
        pass

    @abstractmethod
    def reserve_stock(self, sku: str, quantity: int) -> Dict[str, Any]:
        pass
