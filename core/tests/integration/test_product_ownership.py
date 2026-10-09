from dataclasses import replace
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from core.domain.entities import Category, Product
from core.domain.errors import CategoryInUseError, CategoryTakenError, SkuTakenError
from core.infrastructure.models import CategoryModel, ProductModel
from core.infrastructure.repositories import DjangoProductRepository


def _listing(category: Category, sku: str, merchant: str, price: str = "500000.00") -> Product:
    return Product(
        id=None,
        sku=sku,
        title=f"{merchant}'s listing",
        description="",
        price=Decimal(price),
        currency="IDR",
        image_url="",
        category=category,
        merchant_principal_id=merchant,
    )


@pytest.mark.django_db
class TestProductOwnershipIntegration:
    def test_a_new_product_with_a_taken_sku_leaves_the_owner_s_product_alone(self) -> None:
        repo = DjangoProductRepository()
        shelf = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        victim = repo.save(_listing(shelf, "VICTIM-1", "merchant-victim"))

        with pytest.raises(SkuTakenError):
            repo.save(_listing(shelf, "VICTIM-1", "merchant-attacker", price="1.00"))

        row = ProductModel.objects.get(sku="VICTIM-1")
        assert (row.id, row.merchant_principal_id, row.price, row.title) == (
            victim.id, "merchant-victim", Decimal("500000.00"), "merchant-victim's listing",
        )
        assert ProductModel.objects.count() == 1

    def test_renaming_a_product_onto_a_taken_sku_changes_neither_row(self) -> None:
        repo = DjangoProductRepository()
        shelf = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        repo.save(_listing(shelf, "VICTIM-2", "merchant-victim"))
        own = repo.save(_listing(shelf, "OWN-1", "merchant-attacker"))

        with pytest.raises(SkuTakenError):
            repo.save(replace(own, sku="VICTIM-2", price=Decimal("2.00")))

        assert ProductModel.objects.get(sku="VICTIM-2").merchant_principal_id == "merchant-victim"
        assert ProductModel.objects.get(sku="OWN-1").id == own.id

    def test_an_update_is_by_id_so_a_free_sku_renames_the_same_row(self) -> None:
        repo = DjangoProductRepository()
        shelf = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        own = repo.save(_listing(shelf, "OLD-SKU", "merchant-a"))

        renamed = repo.save(replace(own, sku="NEW-SKU"))

        assert renamed.id == own.id
        assert list(ProductModel.objects.values_list("sku", flat=True)) == ["NEW-SKU"]

    def test_the_database_refuses_a_product_on_sale_with_no_merchant(self) -> None:
        shelf = CategoryModel.objects.create(name="Shoes", slug="shoes")

        for merchant in (None, ""):
            with pytest.raises(IntegrityError), transaction.atomic():
                ProductModel.objects.create(
                    sku=f"ORPHAN-{merchant!r}", title="orphan", price=Decimal("1.00"),
                    category=shelf, merchant_principal_id=merchant, is_active=True,
                )

        ProductModel.objects.create(
            sku="WITHDRAWN-ORPHAN", title="withdrawn", price=Decimal("1.00"),
            category=shelf, merchant_principal_id=None, is_active=False,
        )


@pytest.mark.django_db
class TestCategoryRulesIntegration:
    def test_a_category_holding_a_withdrawn_product_is_kept_with_its_products(self) -> None:
        repo = DjangoProductRepository()
        shelf = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        repo.save(replace(_listing(shelf, "SHOE-1", "merchant-a"), is_active=False))

        with pytest.raises(CategoryInUseError) as refused:
            repo.delete_category(shelf.id or 0)

        assert refused.value.product_count == 1
        assert ProductModel.objects.filter(sku="SHOE-1").exists()
        assert CategoryModel.objects.filter(id=shelf.id).exists()

    def test_an_empty_category_is_deleted(self) -> None:
        repo = DjangoProductRepository()
        shelf = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        assert repo.delete_category(shelf.id or 0) is True
        assert not CategoryModel.objects.exists()

    def test_renaming_a_category_changes_it_in_place(self) -> None:
        repo = DjangoProductRepository()
        shelf = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        repo.save_category(Category(id=shelf.id, name="Footwear", slug="footwear"))

        assert list(CategoryModel.objects.values_list("id", "slug")) == [(shelf.id, "footwear")]

    def test_a_taken_name_or_slug_is_refused(self) -> None:
        repo = DjangoProductRepository()
        repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        with pytest.raises(CategoryTakenError):
            repo.save_category(Category(id=None, name="Shoes", slug="other"))
        with pytest.raises(CategoryTakenError):
            repo.save_category(Category(id=None, name="Other", slug="shoes"))
        assert CategoryModel.objects.count() == 1
