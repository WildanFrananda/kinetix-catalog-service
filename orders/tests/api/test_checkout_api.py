import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
class TestCheckoutAPI:
    def test_post_checkout_creates_order_and_returns_201_created(self) -> None:
        client = APIClient()
        url = reverse("checkout")

        payload = {
            "merchant_api_key": "GRPC_TEST_KEY_123",
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
        data = response.json()
        assert data["success"] is True
        assert data["order_id"] is not None
        assert data["order_number"].startswith("ORD-STF-")
        assert data["total_amount"] == "450000.00"
