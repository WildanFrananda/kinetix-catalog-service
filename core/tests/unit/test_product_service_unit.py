from decimal import Decimal
from core.domain.entities import Product, Category
from core.application.dto import ProductFilterDTO
from core.application.services import ProductService
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

        assert detail.sku == "SKU-1"
        assert detail.warehouse_stock.bin_location == "Bin A-04"
