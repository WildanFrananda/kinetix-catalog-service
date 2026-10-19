from decimal import Decimal
from typing import Optional

import pytest
from django.db import IntegrityError, transaction
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
            category=cat,
            merchant_principal_id="shop-1",
        )

        saved = repo.save(product)
        assert saved.id is not None
        assert ProductModel.objects.count() == 1

        found = repo.find_by_sku("SHOE-WHT-41")
        assert found is not None
        assert found.title == "White Running Shoes"

    def test_a_weight_is_kept_and_a_missing_one_stays_missing(self) -> None:
        repo = DjangoProductRepository()
        cat = repo.save_category(Category(id=None, name="Footwear", slug="footwear"))

        def shoe(sku: str, grams: Optional[int]) -> Product:
            return Product(
                id=None,
                sku=sku,
                title=f"Shoe {sku}",
                description="",
                price=Decimal("750000.00"),
                currency="IDR",
                image_url="",
                category=cat,
                merchant_principal_id="shop-1",
                weight_grams=grams,
            )

        repo.save(shoe("SHOE-HEAVY-44", 1200))
        repo.save(shoe("SHOE-OLD-40", None))

        heavy = repo.find_by_sku("SHOE-HEAVY-44")
        old = repo.find_by_sku("SHOE-OLD-40")
        assert heavy is not None and heavy.weight_grams == 1200
        assert old is not None and old.weight_grams is None

    def test_the_database_refuses_a_weight_of_nothing(self) -> None:
        repo = DjangoProductRepository()
        cat = repo.save_category(Category(id=None, name="Footwear", slug="footwear"))

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductModel.objects.create(
                    sku="SHOE-ZERO-40",
                    title="Weightless",
                    price=Decimal("1.00"),
                    category_id=cat.id,
                    merchant_principal_id="shop-1",
                    weight_grams=0,
                )

