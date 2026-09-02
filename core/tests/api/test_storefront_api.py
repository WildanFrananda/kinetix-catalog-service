from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from core.domain.entities import Category, Product
from core.infrastructure.repositories import DjangoProductRepository

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

# Two tests were removed here: test_post_checkout_returns_201_created and
# test_post_reserve_cart_stock_returns_200. They called reverse("checkout") and
# reverse("cart-reserve-stock"), routes that do not exist in core/urls.py and must not — the
# checkout and stock-reservation payloads belong to order-service and warehouse-service. Their
# serializers were the four removed in S2 for the same reason; these were the test-side
# remnant of the same domain-boundary violation. Restoring the views to make them pass would
# reinstate it.
