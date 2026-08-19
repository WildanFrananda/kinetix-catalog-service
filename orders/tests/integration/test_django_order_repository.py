from decimal import Decimal
import pytest
from orders.domain.entities import Order, OrderItem, Money, Address
from orders.infrastructure.repositories import DjangoOrderRepository
from orders.infrastructure.models import OrderModel


@pytest.mark.django_db
class TestDjangoOrderRepositoryIntegration:
    def test_save_and_retrieve_order_from_database(self) -> None:
        repo = DjangoOrderRepository()

        domain_order = Order(
            id=None,
            order_number="ORD-TEST-INT-100",
            buyer_name="Bob Johnson",
            buyer_phone="0855667788",
            shipping_address=Address(
                recipient_name="Bob Johnson",
                phone_number="0855667788",
                street_address="Gatot Subroto 12",
                city="Jakarta",
                postal_code="12930"
            ),
            total_amount=Money(currency="IDR", amount=Decimal("200000.00")),
            items=[
                OrderItem(sku="HAT-RED-OS", product_name="Red Hat", quantity=1, price=Money(currency="IDR", amount=Decimal("200000.00")))
            ],
            status="pending"
        )

        saved = repo.save(domain_order)

        assert saved.id is not None
        assert saved.order_number == "ORD-TEST-INT-100"
        assert OrderModel.objects.count() == 1

        found = repo.find_by_order_number("ORD-TEST-INT-100")
        assert found is not None
        assert found.buyer_name == "Bob Johnson"
        assert len(found.items) == 1
        assert found.items[0].sku == "HAT-RED-OS"
