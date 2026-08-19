from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from orders.domain.entities import Order

class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> Order:
        """Persist an order entity to database storage."""
        pass

    @abstractmethod
    def find_by_id(self, order_id: int) -> Optional[Order]:
        """Retrieve an order by its unique integer ID."""
        pass

    @abstractmethod
    def find_by_order_number(self, order_number: str) -> Optional[Order]:
        """Retrieve an order by its unique order_number string."""
        pass

    @abstractmethod
    def list_all(self) -> List[Order]:
        """List all stored orders."""
        pass

class FulfillmentServicePort(ABC):
    @abstractmethod
    def submit_fulfillment_order(self, order: Order, merchant_api_key: str) -> Dict[str, Any]:
        """Send order fulfillment request via gRPC to Warehouse OMS."""
        pass

    @abstractmethod
    def get_fulfillment_status(self, order_id: int, merchant_api_key: str) -> Dict[str, Any]:
        """Fetch real-time fulfillment status via gRPC from Warehouse OMS."""
        pass
