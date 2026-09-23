from abc import ABC, abstractmethod
from typing import Dict, Sequence

from core.domain.entities.stock_info import StockInfo

class BinStockServicePort(ABC):
    @abstractmethod
    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        pass

    @abstractmethod
    def get_bin_stock_for(
        self, skus: Sequence[str], merchant_principal_id: str
    ) -> Dict[str, StockInfo]:
        """Stock for a page of products, in one call."""
