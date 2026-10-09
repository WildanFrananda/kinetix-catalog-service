from dataclasses import replace
from decimal import Decimal

import pytest

from core.application.services import ProductService
from core.domain.entities import Category, Product
from core.domain.errors import SkuTakenError
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort
from core.tests.unit.fake_product_repository import FakeProductRepository

SELLER = "merchant-of-the-seller"
RIVAL = "merchant-of-a-rival"


def _service(repo: FakeProductRepository) -> ProductService:
    return ProductService(
        product_repo=repo,
        bin_stock_port=FakeBinStockServicePort(),
        identity_port=FakeIdentityServicePort(),
    )


def _listed(repo: FakeProductRepository, sku: str, merchant: str) -> Product:
    category = repo.save_category(Category(id=None, name=f"Shelf {sku}", slug=f"shelf-{sku.lower()}"))
    return repo.save(
        Product(
            id=None,
            sku=sku,
            title=f"{merchant}'s listing",
            description="",
            price=Decimal("500000.00"),
            currency="IDR",
            image_url="",
            category=category,
            merchant_principal_id=merchant,
        )
    )


class TestProductOwnershipUnit:
    def test_a_product_with_no_merchant_cannot_be_claimed_by_editing_it(self) -> None:
        repo = FakeProductRepository()
        orphan = _listed(repo, "ORPHAN-1", RIVAL)
        repo.save(replace(orphan, merchant_principal_id=None, is_active=False))

        with pytest.raises(PermissionError, match="does not belong to this merchant"):
            _service(repo).update_product(orphan.id or 0, SELLER, {"price": "1"})

        assert repo.find_by_id(orphan.id or 0) == replace(orphan, merchant_principal_id=None, is_active=False)

    def test_a_product_with_no_merchant_cannot_be_withdrawn_by_a_seller(self) -> None:
        repo = FakeProductRepository()
        orphan = _listed(repo, "ORPHAN-2", RIVAL)
        repo.save(replace(orphan, merchant_principal_id=None))

        with pytest.raises(PermissionError, match="does not belong to this merchant"):
            _service(repo).delete_product(orphan.id or 0, SELLER)

    def test_a_new_product_cannot_take_another_merchants_sku(self) -> None:
        repo = FakeProductRepository()
        victim = _listed(repo, "VICTIM-1", RIVAL)

        with pytest.raises(SkuTakenError):
            _service(repo).create_product(
                SELLER,
                {"sku": "VICTIM-1", "title": "mine now", "price": "1", "category_id": victim.category.id},
            )

        assert repo.find_by_sku("VICTIM-1") == victim

    def test_renaming_a_product_to_another_merchants_sku_is_refused(self) -> None:
        repo = FakeProductRepository()
        victim = _listed(repo, "VICTIM-2", RIVAL)
        own = _listed(repo, "OWN-1", SELLER)

        with pytest.raises(SkuTakenError):
            _service(repo).update_product(own.id or 0, SELLER, {"sku": "VICTIM-2", "price": "2"})

        assert repo.find_by_sku("VICTIM-2") == victim
        assert repo.find_by_sku("OWN-1") == own
