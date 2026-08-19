from decimal import Decimal
from typing import Optional, List, Dict, Any
import pytest

from orders.domain.entities import Order
from orders.domain.repositories import OrderRepository, FulfillmentServicePort
from orders.application.dto import CreateOrderInputDTO, OrderItemDTO
from orders.application.services import CheckoutOrderService

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

class FakeFulfillmentServicePort(FulfillmentServicePort):
    def __init__(self, return_success: bool = True) -> None:
        self.return_success = return_success
        self.last_submitted_order: Optional[Order] = None

    def submit_fulfillment_order(self, order: Order, merchant_api_key: str) -> Dict[str, Any]:
        self.last_submitted_order = order
        return {
            "success": self.return_success,
            "order_id": order.id,
            "status": "received" if self.return_success else "failed"
        }

    def get_fulfillment_status(self, order_id: int, merchant_api_key: str) -> Dict[str, Any]:
        return {"order_id": order_id, "status": "received"}


class TestCheckoutOrderServiceUnit:
    def test_checkout_successfully_creates_order_and_dispatches_grpc(self) -> None:
        repo = FakeOrderRepository()
        port = FakeFulfillmentServicePort()
        service = CheckoutOrderService(order_repo=repo, fulfillment_port=port)

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="Alice Smith",
            buyer_phone="0811223344",
            street_address="Jl. Sudirman No 45",
            city="Jakarta",
            postal_code="10210",
            items=[
                OrderItemDTO(sku="TSHIRT-BLK-M", product_name="Black Tee M", quantity=2, price=Decimal("150000.00")),
                OrderItemDTO(sku="JEANS-BLU-32", product_name="Blue Jeans 32", quantity=1, price=Decimal("350000.00"))
            ]
        )

        result = service.execute(dto)

        assert result.success is True
        assert result.order_id == 1
        assert result.status == "received"
        assert result.total_amount == Decimal("650000.00")
        assert len(repo.list_all()) == 1
        assert port.last_submitted_order is not None
        assert port.last_submitted_order.buyer_name == "Alice Smith"

    def test_checkout_raises_error_when_buyer_name_blank(self) -> None:
        repo = FakeOrderRepository()
        port = FakeFulfillmentServicePort()
        service = CheckoutOrderService(order_repo=repo, fulfillment_port=port)

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="   ",
            buyer_phone="0811223344",
            street_address="Jl. Sudirman No 45",
            city="Jakarta",
            postal_code="10210",
            items=[OrderItemDTO(sku="TSHIRT", product_name="Tee", quantity=1, price=Decimal("100000.00"))]
        )

        with pytest.raises(ValueError, match="Buyer name cannot be blank"):
            service.execute(dto)
