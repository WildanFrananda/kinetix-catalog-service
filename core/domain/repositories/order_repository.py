from abc import ABC, abstractmethod
from typing import Optional, List
from core.domain.entities.order import Order

class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> Order:
        pass

    @abstractmethod
    def find_by_id(self, order_id: int) -> Optional[Order]:
        pass

    @abstractmethod
    def find_by_order_number(self, order_number: str) -> Optional[Order]:
        pass

    @abstractmethod
    def list_all(self) -> List[Order]:
        pass
