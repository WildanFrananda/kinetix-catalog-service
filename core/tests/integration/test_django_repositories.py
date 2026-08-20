from decimal import Decimal
import pytest
from core.domain.entities import Product, Category, Order, OrderItem, Money, Address
from core.infrastructure.repositories import DjangoProductRepository, DjangoOrderRepository
from core.infrastructure.models import ProductModel, OrderModel

@pytest.mark.django_db
class TestDjangoRepositoriesIntegration:
    def test_save_and_find_products(self) -> None:
        repo = DjangoProductRepository()

        cat = repo.save_category(Category(id=None, name="Footwear", slug="footwear"))
        product = Product(
            id=None,
            sku="SHOE-WHT-41",
            title="White Running Shoes",
            description="Lightweight mesh running shoes",
            price=Decimal("750000.00"),
            currency="IDR",
            image_url="",
            category=cat
        )

        saved = repo.save(product)
        assert saved.id is not None
        assert ProductModel.objects.count() == 1

        found = repo.find_by_sku("SHOE-WHT-41")
        assert found is not None
        assert found.title == "White Running Shoes"

    def test_save_and_find_orders(self) -> None:
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
        assert OrderModel.objects.count() == 1
