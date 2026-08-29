from decimal import Decimal
import pytest
from core.domain.entities import Product, Category
from core.application.dto import ProductFilterDTO
from core.application.services import ProductService
from core.application.services.category_service import CategoryService
from core.tests.unit.fake_product_repository import FakeProductRepository
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort

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
        product = service.create_product(merchant_id=50, data={
            "sku": "SHOES-RUN-42",
            "title": "Running Shoes 42",
            "description": "Pro running shoes",
            "price": "500000.00",
            "category_id": cat.id
        })

        assert product.id is not None
        assert product.sku == "SHOES-RUN-42"
        assert product.merchant_id == 50

    def test_update_product_idor_protection_rejects_other_merchant(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        p = service.create_product(merchant_id=50, data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id
        })

        assert p.id is not None
        with pytest.raises(PermissionError, match="Product does not belong to this merchant"):
            service.update_product(product_id=p.id, merchant_id=999, data={"title": "Hacked Title"})

    def test_delete_product_idor_protection_rejects_other_merchant(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port)
        p = service.create_product(merchant_id=50, data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id
        })

        assert p.id is not None
        with pytest.raises(PermissionError, match="Product does not belong to this merchant"):
            service.delete_product(product_id=p.id, merchant_id=999)

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
