from typing import Optional, List, Dict
from core.domain.entities import Order
from core.domain.repositories import OrderRepository

class FakeOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self._store: Dict[int, Order] = {}
        self._next_id = 1

    def save(self, order: Order) -> Order:
        order_id = order.id or self._next_id
        if not order.id:
            self._next_id += 1

        saved_order = Order(
            id=order_id,
            order_number=order.order_number,
            buyer_name=order.buyer_name,
            buyer_phone=order.buyer_phone,
            shipping_address=order.shipping_address,
            total_amount=order.total_amount,
            items=order.items,
            status=order.status,
            created_at=order.created_at
        )
        self._store[order_id] = saved_order
        return saved_order

    def find_by_id(self, order_id: int) -> Optional[Order]:
        return self._store.get(order_id)

    def find_by_order_number(self, order_number: str) -> Optional[Order]:
        for o in self._store.values():
            if o.order_number == order_number:
                return o
        return None

    def list_all(self) -> List[Order]:
        return list(self._store.values())
