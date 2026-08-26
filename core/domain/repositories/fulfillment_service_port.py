from abc import ABC, abstractmethod
from typing import Dict, Any
from core.domain.entities import Order

class FulfillmentServicePort(ABC):
    @abstractmethod
    def submit_fulfillment_order(self, order: Order) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_fulfillment_status(self, order_id: int) -> Dict[str, Any]:
        pass
