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

    def test_post_checkout_returns_201_created(self) -> None:
        client = APIClient()
        url = reverse("checkout")

        payload = {
            "buyer_name": "Charlie Brown",
            "buyer_phone": "0899887766",
            "street_address": "Jl. MH Thamrin 9",
            "city": "Jakarta",
            "postal_code": "10350",
            "items": [
                {
                    "sku": "HOODIE-GRY-L",
                    "product_name": "Grey Hoodie L",
                    "quantity": 1,
                    "price": "450000.00"
                }
            ]
        }

        response = client.post(url, payload, format="json")
        assert response.status_code == 201

    def test_post_reserve_cart_stock_returns_200(self) -> None:
        client = APIClient()
        url = reverse("cart-reserve-stock")

        payload = {
            "sku": "TSHIRT-BLK-M",
            "quantity": 2
        }

        response = client.post(url, payload, format="json")
        assert response.status_code == 200
