from abc import ABC, abstractmethod
from typing import Any, Dict

from core.domain.entities.stock_info import StockInfo


class BinStockServicePort(ABC):
    @abstractmethod
    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        pass

    @abstractmethod
    def reserve_stock(self, sku: str, quantity: int, merchant_principal_id: str) -> Dict[str, Any]:
        pass
