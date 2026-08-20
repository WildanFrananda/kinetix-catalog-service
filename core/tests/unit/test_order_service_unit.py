from decimal import Decimal
from core.application.dto import CreateOrderInputDTO, OrderItemDTO, ReserveCartStockInputDTO
from core.application.services import OrderService
from core.tests.unit.fake_order_repository import FakeOrderRepository
from core.tests.unit.fake_fulfillment_service_port import FakeFulfillmentServicePort
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort

class TestOrderServiceUnit:
    def test_checkout_successfully_creates_order_and_dispatches_grpc(self) -> None:
        repo = FakeOrderRepository()
        port = FakeFulfillmentServicePort()
        service = OrderService(order_repo=repo, fulfillment_port=port)

        dto = CreateOrderInputDTO(
            merchant_api_key="TEST_KEY",
            buyer_name="Alice Smith",
            buyer_phone="0811223344",
            street_address="Jl. Sudirman No 45",
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

    def test_reserve_cart_stock_reserves_via_bin_stock_port(self) -> None:
        repo = FakeOrderRepository()
        fulfillment_port = FakeFulfillmentServicePort()
        bin_stock_port = FakeBinStockServicePort()
        service = OrderService(order_repo=repo, fulfillment_port=fulfillment_port, bin_stock_port=bin_stock_port)

        dto = ReserveCartStockInputDTO(sku="TSHIRT-BLK-M", quantity=2)
        res = service.reserve_cart_stock(dto)

        assert res.success is True
        assert res.sku == "TSHIRT-BLK-M"
