from decimal import Decimal

import pytest

from core.application.services.category_service import CategoryService
from core.domain.entities import Category, Product
from core.domain.errors import CategoryInUseError, CategoryTakenError, InvalidInputError
from core.tests.unit.fake_product_repository import FakeProductRepository


class TestCategoryRulesUnit:
    @pytest.mark.parametrize(("name", "slug", "field"), [("", "shoes", "name"), ("  ", "shoes", "name"), ("Shoes", "", "slug"), ("Shoes", "has space", "slug"), ("Shoes", "a/b", "slug")])
    def test_a_category_needs_a_name_and_a_url_safe_slug(self, name: str, slug: str, field: str) -> None:
        with pytest.raises(InvalidInputError) as refused:
            CategoryService(FakeProductRepository()).create_category(name=name, slug=slug)
        assert refused.value.field == field

    def test_a_second_category_cannot_take_a_name_or_slug(self) -> None:
        service = CategoryService(FakeProductRepository())
        service.create_category(name="Shoes", slug="shoes")

        with pytest.raises(CategoryTakenError):
            service.create_category(name="Shoes", slug="footwear")
        with pytest.raises(CategoryTakenError):
            service.create_category(name="Footwear", slug="shoes")

    def test_a_category_still_holding_a_withdrawn_product_is_not_deleted(self) -> None:
        repo = FakeProductRepository()
        service = CategoryService(repo)
        shoes = service.create_category(name="Shoes", slug="shoes")
        repo.save(
            Product(
                id=None, sku="SHOE-1", title="Shoe", description="", price=Decimal("1.00"), currency="IDR",
                image_url="", category=shoes, merchant_principal_id="shop-1", is_active=False,
            )
        )

        with pytest.raises(CategoryInUseError) as refused:
            service.delete_category(shoes.id or 0)
        assert refused.value.product_count == 1
        assert service.get_category_by_id(shoes.id or 0) == shoes

    def test_renaming_a_category_keeps_it_one_category(self) -> None:
        repo = FakeProductRepository()
        service = CategoryService(repo)
        shoes = service.create_category(name="Shoes", slug="shoes")

        service.update_category(shoes.id or 0, name="Footwear", slug="footwear")

        assert service.list_categories() == [Category(id=shoes.id, name="Footwear", slug="footwear")]
