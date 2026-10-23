from decimal import Decimal
from typing import Dict

from rest_framework.test import APIClient

from core.domain.entities import Category, Product
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.security import Principal
from core.tests.api.fake_identity_keys import FakeIdentityKeys
from core.tests.api.json_response import JsonResponse

TRACE = "trace-session-32"
SELLER = Principal(principal_id="seller-1", email="seller@example.test", role="seller")
RIVAL = Principal(principal_id="rival-1", email="rival@example.test", role="seller")
ADMIN = Principal(principal_id="admin-1", email="admin@example.test", role="admin")
CUSTOMER = Principal(principal_id="customer-1", email="customer@example.test", role="customer")
VERIFIER_ENV: Dict[str, str] = {
    "JWT_ISSUER": "https://identity.test",
    "JWT_AUDIENCE": "kinetix",
    "IDENTITY_JWKS_URL": "http://127.0.0.1:1/.well-known/jwks.json",
}
KEYS = FakeIdentityKeys(VERIFIER_ENV["JWT_ISSUER"], VERIFIER_ENV["JWT_AUDIENCE"])
ERROR_SHAPE_KEYS = frozenset({"error", "message", "traceId", "field", "product_count"})


def refusal(response: JsonResponse, status: int, code: str) -> Dict[str, object]:
    assert response.status_code == status
    assert response["Content-Type"].startswith("application/json")
    body = response.json()
    assert isinstance(body, dict)
    assert body["error"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert body["traceId"] == TRACE
    assert set(body) <= ERROR_SHAPE_KEYS, f"keys outside the error shape: {set(body) - ERROR_SHAPE_KEYS}"

    return body


def category_named(slug: str = "footwear") -> Category:
    return DjangoProductRepository().save_category(Category(id=None, name=slug.title(), slug=slug))


def product_listed(sku: str, category: Category, merchant: str = "seller-1") -> Product:
    return DjangoProductRepository().save(
        Product(
            id=None,
            sku=sku,
            title=f"Shoe {sku}",
            description="",
            price=Decimal("150000.00"),
            currency="IDR",
            image_url="",
            category=category,
            merchant_principal_id=merchant,
            weight_grams=500,
        )
    )


def signed_in_as(principal: Principal) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {KEYS.sign(principal)}")

    return client
