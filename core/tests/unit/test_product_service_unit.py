from decimal import Decimal
from typing import Optional
import pytest
from core.domain.entities import Product, Category, StockStatus
from core.domain.errors import IdentityUnavailableError
from core.application.dto import ProductFilterDTO
from core.application.services import ProductService
from core.application.services.category_service import CategoryService
from core.tests.unit.fake_product_repository import FakeProductRepository
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort
from core.tests.unit.fake_unreachable_bin_stock_service_port import (
    FakeUnreachableBinStockServicePort,
)

class TestProductServiceUnit:
    def test_list_products_returns_paginated_summaries(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        res = service.list_products(ProductFilterDTO(page=1, page_size=10))

        assert res.count == 1
        assert res.results[0].sku == "SKU-1"

    def test_get_product_detail_returns_warehouse_stock(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        detail = service.get_product_detail("SKU-1")

        assert detail is not None
        assert detail.sku == "SKU-1"
        assert detail.warehouse_stock.bin_location == "Bin A-04"

    def test_create_product_success(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        product = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-RUN-42",
            "title": "Running Shoes 42",
            "description": "Pro running shoes",
            "price": "500000.00",
            "category_id": cat.id
        })

        assert product.id is not None
        assert product.sku == "SHOES-RUN-42"
        assert product.merchant_principal_id == "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3"

    def test_update_product_idor_protection_rejects_other_merchant(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        p = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id
        })

        assert p.id is not None
        with pytest.raises(PermissionError, match="Product does not belong to this merchant"):
            service.update_product(product_id=p.id, merchant_principal_id="9f1d4a3e-1c62-4d0a-9a7b-2f5c8e0b41d7", data={"title": "Hacked Title"})

    def test_delete_product_idor_protection_rejects_other_merchant(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        p = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id
        })

        assert p.id is not None
        with pytest.raises(PermissionError, match="Product does not belong to this merchant"):
            service.delete_product(product_id=p.id, merchant_principal_id="9f1d4a3e-1c62-4d0a-9a7b-2f5c8e0b41d7")

    def test_unreachable_warehouse_lists_stock_as_unknown_not_zero(self) -> None:
        """The estate's house bug: an outage rendered as a confident 'out of stock'."""
        repo = FakeProductRepository()
        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=FakeUnreachableBinStockServicePort())
        summary = service.list_products(ProductFilterDTO(page=1, page_size=10)).results[0]

        assert summary.available_stock is None
        assert summary.is_in_stock is None
        assert summary.stock_status is StockStatus.UNKNOWN

    def test_unreachable_warehouse_details_stock_as_unknown_not_zero(self) -> None:
        repo = FakeProductRepository()
        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=FakeUnreachableBinStockServicePort())
        detail = service.get_product_detail("SKU-1")

        assert detail is not None
        assert detail.warehouse_stock.available_quantity is None
        assert detail.warehouse_stock.bin_location is None
        assert detail.warehouse_stock.stock_status is StockStatus.UNKNOWN

    def test_a_warehouse_that_answers_zero_is_out_of_stock_not_unknown(self) -> None:
        """The other half of the distinction: a real sell-out must still read as a real zero."""
        repo = FakeProductRepository()
        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(available_quantity=0))
        summary = service.list_products(ProductFilterDTO(page=1, page_size=10)).results[0]

        assert summary.available_stock == 0
        assert summary.is_in_stock is False
        assert summary.stock_status is StockStatus.OUT_OF_STOCK

    def test_identity_outage_is_not_reported_as_an_unverified_merchant(self) -> None:
        """PermissionError becomes HTTP 403 'your account is not verified'. An outage is not that."""
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(unavailable=True),
        )

        with pytest.raises(IdentityUnavailableError):
            service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
                "sku": "SHOES-RUN-42",
                "title": "Running Shoes 42",
                "price": "500000.00",
                "category_id": cat.id
            })

    @pytest.mark.parametrize("merchant_status", ["pending", None])
    def test_a_real_negative_from_identity_is_still_a_permission_error(
        self, merchant_status: Optional[str]
    ) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(status=merchant_status),
        )

        with pytest.raises(PermissionError, match="not verified/active"):
            service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
                "sku": "SHOES-RUN-42",
                "title": "Running Shoes 42",
                "price": "500000.00",
                "category_id": cat.id
            })

    def test_identity_outage_blocks_update_and_delete_too(self) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))
        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort())
        created = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id
        })

        assert created.id is not None
        offline = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(unavailable=True),
        )

        with pytest.raises(IdentityUnavailableError):
            offline.update_product(product_id=created.id, merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={"title": "New"})
        with pytest.raises(IdentityUnavailableError):
            offline.delete_product(product_id=created.id, merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3")

    def test_category_crud_operations(self) -> None:
        repo = FakeProductRepository()
        cat_service = CategoryService(product_repo=repo)

        cat = cat_service.create_category(name="Gadgets", slug="gadgets")
        assert cat.id is not None
        assert cat.name == "Gadgets"

        updated = cat_service.update_category(category_id=cat.id, name="Smart Gadgets", slug="smart-gadgets")
        assert updated is not None
        assert updated.name == "Smart Gadgets"

        deleted = cat_service.delete_category(cat.id)
        assert deleted is True
