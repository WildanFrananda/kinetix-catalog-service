from decimal import Decimal
import pytest
from core.domain.entities import Product, Category
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.models import ProductModel

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
