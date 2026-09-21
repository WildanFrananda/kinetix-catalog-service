from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from core.api import di
from core.domain.entities import Category, Product
from core.infrastructure.repositories import DjangoProductRepository
from core.tests.unit.fake_unreachable_bin_stock_service_port import (
    FakeUnreachableBinStockServicePort,
)

@pytest.mark.django_db
class TestStorefrontAPI:
    def test_get_products_list_returns_200(self) -> None:
        client = APIClient()
        repo = DjangoProductRepository()
        cat = repo.save_category(Category(id=None, name="Apparel", slug="apparel"))
        repo.save(Product(id=None, sku="TSHIRT-TEST", title="Test Tee", description="Desc", price=Decimal("150000.00"), currency="IDR", image_url="", category=cat))

        url = reverse("product-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_stock_warehouse_could_not_answer_for_is_reported_as_unknown(self) -> None:
        client = APIClient()
        repo = DjangoProductRepository()
        cat = repo.save_category(Category(id=None, name="Apparel", slug="apparel"))
        repo.save(Product(id=None, sku="TSHIRT-UNKNOWN", title="Test Tee", description="Desc", price=Decimal("150000.00"), currency="IDR", image_url="", category=cat))
        di._bin_stock_client = FakeUnreachableBinStockServicePort()

        response = client.get(reverse("product-list"))

        assert response.status_code == 200
        summary = response.json()["results"][0]
        assert summary["stock_status"] == "unknown"
        assert summary["available_stock"] is None
        assert summary["is_in_stock"] is None
