from decimal import Decimal
from typing import Dict, Any
import pytest
from core.application.dto import CreateOrderInputDTO, OrderItemDTO, ReserveCartStockInputDTO
from core.application.services import OrderService
from core.tests.unit.fake_order_repository import FakeOrderRepository
from core.tests.unit.fake_fulfillment_service_port import FakeFulfillmentServicePort
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort

class FailingFulfillmentServicePort(FakeFulfillmentServicePort):
    def submit_fulfillment_order(self, order: object, merchant_api_key: str) -> Dict[str, Any]:
        return {"success": False, "error": "Warehouse server connection reset"}

class TestOrderServiceUnit:
    def test_checkout_successfully_creates_order_and_dispatches_grpc(self) -> None:
        repo = FakeOrderRepository()
        port = FakeFulfillmentServicePort()
        service = OrderService(order_repo=repo, fulfillment_port=port)

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="Alice Smith",
            buyer_phone="0811223344",
            street_address="123 Main Street",
            city="Jakarta",
            postal_code="10210",
            items=[
                OrderItemDTO(sku="TSHIRT-BLK-M", product_name="Black Tee M", quantity=2, price=Decimal("150000.00"))
            ]
        )

        result = service.checkout(dto)

        assert result.success is True
        assert result.order_id == 1
        assert result.status == "received"

    def test_checkout_idempotency_key_prevents_duplicate_orders(self) -> None:
        repo = FakeOrderRepository()
        port = FakeFulfillmentServicePort()
        service = OrderService(order_repo=repo, fulfillment_port=port)

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="Alice Smith",
            buyer_phone="0811223344",
            street_address="123 Main Street",
            city="Jakarta",
            postal_code="10210",
            items=[
                OrderItemDTO(sku="TSHIRT-BLK-M", product_name="Black Tee M", quantity=1, price=Decimal("150000.00"))
            ],
            idempotency_key="UNIQUE_IDEMPOTENCY_KEY_123"
        )

        first_res = service.checkout(dto)
        assert first_res.success is True

        second_res = service.checkout(dto)
        assert second_res.success is True
        assert second_res.order_id == first_res.order_id
        assert second_res.order_number == first_res.order_number
        assert "Duplicate request detected" in second_res.message

    def test_checkout_atomic_stock_reservation_failure_rejects_order(self) -> None:
        repo = FakeOrderRepository()
        fulfillment_port = FakeFulfillmentServicePort()

        class FailingBinStockPort(FakeBinStockServicePort):
            def reserve_stock(self, sku: str, quantity: int) -> Dict[str, Any]:
                return {"success": False, "message": "Out of stock"}

        service = OrderService(order_repo=repo, fulfillment_port=fulfillment_port, bin_stock_port=FailingBinStockPort())

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="Bob Jones",
            buyer_phone="0811223355",
            street_address="456 Market St",
            city="Bandung",
            postal_code="40115",
            items=[
                OrderItemDTO(sku="SOLD-OUT-SKU", product_name="Limited Edition Watch", quantity=1, price=Decimal("500000.00"))
            ]
        )

        with pytest.raises(ValueError, match="Insufficient stock"):
            service.checkout(dto)

    def test_checkout_saga_compensation_marks_order_failed_on_grpc_failure(self) -> None:
        repo = FakeOrderRepository()
        port = FailingFulfillmentServicePort()
        service = OrderService(order_repo=repo, fulfillment_port=port)

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="Charlie Brown",
            buyer_phone="0811223366",
            street_address="789 Park Ave",
            city="Surabaya",
            postal_code="60281",
            items=[
                OrderItemDTO(sku="TSHIRT-BLK-L", product_name="Black Tee L", quantity=1, price=Decimal("150000.00"))
            ]
        )

        result = service.checkout(dto)

        assert result.success is False
        assert result.status == "failed"
        assert "Fulfillment submission failed" in result.message

        assert result.order_id is not None
        saved_order = repo.find_by_id(result.order_id)
        assert saved_order is not None
        assert saved_order.status == "failed"

    def test_reserve_cart_stock_reserves_via_bin_stock_port(self) -> None:
        repo = FakeOrderRepository()
        fulfillment_port = FakeFulfillmentServicePort()
        bin_stock_port = FakeBinStockServicePort()
        service = OrderService(order_repo=repo, fulfillment_port=fulfillment_port, bin_stock_port=bin_stock_port)

        dto = ReserveCartStockInputDTO(sku="TSHIRT-BLK-M", quantity=2)
        res = service.reserve_cart_stock(dto)

        assert res.success is True
        assert res.sku == "TSHIRT-BLK-M"
