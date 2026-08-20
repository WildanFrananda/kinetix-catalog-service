from abc import ABC, abstractmethod
from typing import Dict, Any
from core.domain.entities.order import Order

class FulfillmentServicePort(ABC):
    @abstractmethod
    def submit_fulfillment_order(self, order: Order, merchant_api_key: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_fulfillment_status(self, order_id: int, merchant_api_key: str) -> Dict[str, Any]:
        pass
