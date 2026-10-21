import importlib
import sys
from decimal import Decimal
from typing import Dict, Iterator, cast

import pytest
from django.test import Client
from jwt import PyJWKClient
from rest_framework.test import APIClient

from core.api import di
from core.api.views import HealthView
from core.domain.entities import Category, Product
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.security import Principal, SigningKeySet, TokenVerifier
from core.tests.api.fake_identity_keys import FakeIdentityKeys
from core.tests.api.json_response import JsonResponse
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort

TRACE = "trace-session-32"
SELLER = Principal(principal_id="seller-1", email="seller@example.test", role="seller")
RIVAL = Principal(principal_id="rival-1", email="rival@example.test", role="seller")
ADMIN = Principal(principal_id="admin-1", email="admin@example.test", role="admin")
VERIFIER_ENV: Dict[str, str] = {
    "JWT_ISSUER": "https://identity.test",
    "JWT_AUDIENCE": "kinetix",
    "IDENTITY_JWKS_URL": "http://127.0.0.1:1/.well-known/jwks.json",
}
KEYS = FakeIdentityKeys(VERIFIER_ENV["JWT_ISSUER"], VERIFIER_ENV["JWT_AUDIENCE"])


def _refusal(response: JsonResponse, status: int, code: str) -> Dict[str, object]:
    assert response.status_code == status
    assert response["Content-Type"].startswith("application/json")
    body = response.json()
    assert isinstance(body, dict)
    assert body["error"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert body["traceId"] == TRACE

    return body


def _shelf(slug: str = "footwear") -> Category:
    return DjangoProductRepository().save_category(Category(id=None, name=slug.title(), slug=slug))


def _listed(sku: str, shelf: Category, merchant: str = "seller-1") -> Product:
    return DjangoProductRepository().save(
        Product(
            id=None,
            sku=sku,
            title=f"Shoe {sku}",
            description="",
            price=Decimal("150000.00"),
            currency="IDR",
            image_url="",
            category=shelf,
            merchant_principal_id=merchant,
            weight_grams=500,
        )
    )


def _as(principal: Principal) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {KEYS.sign(principal)}")

    return client


@pytest.fixture(autouse=True)
def identity_signs_tokens(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name, value in VERIFIER_ENV.items():
        monkeypatch.setenv(name, value)
    verifier = TokenVerifier()
    monkeypatch.setattr(verifier, "_keys", SigningKeySet(cast(PyJWKClient, KEYS)))
    monkeypatch.setattr(TokenVerifier, "_instance", verifier)
    yield


@pytest.mark.django_db
class TestPathsWithoutTheirTrailingSlash:
    def test_every_read_is_served_with_or_without_the_slash(self) -> None:
        shelf = _shelf()
        _listed("SHOE-1", shelf)
        client = APIClient()

        for path in ["/api/products", "/api/products/SHOE-1", "/api/categories", f"/api/categories/{shelf.id}"]:
            bare = client.get(path)
            slashed = client.get(path + "/")

            assert bare.status_code == 200, path
            assert bare.json() == slashed.json(), path

    def test_every_write_is_served_without_the_slash(self) -> None:
        shelf = _shelf()
        client = _as(SELLER)

        created = client.post(
            "/api/products/create",
            {"sku": "SHOE-2", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
        )
        assert created.status_code == 201
        product_id = created.json()["id"]

        updated = client.put(f"/api/products/manage/{product_id}", {"title": "Shoe, renamed"}, format="json")
        assert updated.status_code == 200

        withdrawn = client.delete(f"/api/products/manage/{product_id}")
        assert withdrawn.status_code == 204

    def test_a_category_is_managed_without_the_slash(self) -> None:
        client = _as(ADMIN)

        created = client.post("/api/categories", {"name": "Bags", "slug": "bags"}, format="json")
        assert created.status_code == 201
        category_id = created.json()["id"]

        renamed = client.put(f"/api/categories/{category_id}", {"name": "Totes", "slug": "totes"}, format="json")
        assert renamed.status_code == 200

        deleted = client.delete(f"/api/categories/{category_id}")
        assert deleted.status_code == 204


@pytest.mark.django_db
class TestUnhandledFailuresAreJson:
    def test_a_failure_inside_the_api_is_json_with_its_trace_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def broken(*args: object, **kwargs: object) -> None:
            raise RuntimeError("the database fell over")

        monkeypatch.setattr(DjangoProductRepository, "find_page", broken)

        response = APIClient().get("/api/products/", HTTP_X_REQUEST_ID=TRACE)

        body = _refusal(response, 500, "INTERNAL_ERROR")
        assert "fell over" not in str(body["message"])

    def test_a_failure_outside_drf_is_json_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def broken(view: object, request: object) -> None:
            raise RuntimeError("health broke")

        monkeypatch.setattr(HealthView, "get", broken)

        response = Client(raise_request_exception=False).get("/health", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 500, "INTERNAL_ERROR")

    def test_a_path_nothing_serves_is_a_json_404(self) -> None:
        response = Client().get("/api/nothing-is-here/", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 404, "NOT_FOUND")


@pytest.mark.django_db
class TestQueriesThatAreNoPage:
    @pytest.mark.parametrize(
        "query",
        [
            {"page": "²"},
            {"page_size": "²"},
            {"page": "١٢"},
            {"page": "100000000000000000000"},
            {"page": "9" * 5000},
            {"page": "10001"},
        ],
    )
    def test_a_page_that_cannot_be_served_is_a_400_not_a_500(self, query: Dict[str, str]) -> None:
        response = APIClient().get("/api/products/", query, HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 400, "INVALID_INPUT")

    @pytest.mark.parametrize("field", ["category", "q"])
    def test_a_filter_postgres_could_not_hold_is_a_400_not_a_500(self, field: str) -> None:
        response = APIClient().get("/api/products/", {field: "a\x00b"}, HTTP_X_REQUEST_ID=TRACE)

        body = _refusal(response, 400, "INVALID_INPUT")
        assert body["field"] == field

    def test_a_sku_postgres_could_not_hold_is_not_found_not_a_500(self) -> None:
        response = APIClient().get("/api/products/a%00b/", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 404, "PRODUCT_NOT_FOUND")


@pytest.mark.django_db
class TestCategoryRoutes:
    @pytest.mark.parametrize(
        ("method", "path"),
        [("put", "/api/categories/"), ("delete", "/api/categories/"), ("post", "/api/categories/1/")],
    )
    def test_a_method_a_category_route_does_not_serve_is_a_405(self, method: str, path: str) -> None:
        response = getattr(_as(ADMIN), method)(path, HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 405, "METHOD_NOT_ALLOWED")
        assert method.upper() not in response["Allow"]

    @pytest.mark.parametrize(
        "body",
        [
            {"name": None, "slug": "shoes"},
            {"name": "Shoes", "slug": None},
            {"name": 12, "slug": "shoes"},
            {"slug": "shoes"},
            {"name": "Sho\x00es", "slug": "shoes"},
        ],
    )
    def test_a_category_is_not_created_from_a_name_or_slug_that_is_not_text(self, body: Dict[str, object]) -> None:
        response = _as(ADMIN).post("/api/categories/", body, format="json", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 400, "INVALID_INPUT")
        assert DjangoProductRepository().find_all_categories() == []

    def test_a_category_is_not_renamed_to_none(self) -> None:
        shelf = _shelf()

        response = _as(ADMIN).put(
            f"/api/categories/{shelf.id}/",
            {"name": None, "slug": "footwear"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        _refusal(response, 400, "INVALID_INPUT")
        assert DjangoProductRepository().find_category_by_id(shelf.id or 0) == shelf

    def test_a_seller_may_not_manage_categories(self) -> None:
        response = _as(SELLER).post("/api/categories/", {"name": "Bags", "slug": "bags"}, format="json", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 403, "ADMIN_REQUIRED")

    def test_an_unknown_category_is_a_404(self) -> None:
        response = APIClient().get("/api/categories/999999/", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 404, "CATEGORY_NOT_FOUND")

    def test_a_category_holding_products_is_not_deleted(self) -> None:
        shelf = _shelf()
        _listed("SHOE-1", shelf)

        response = _as(ADMIN).delete(f"/api/categories/{shelf.id}/", HTTP_X_REQUEST_ID=TRACE)

        body = _refusal(response, 409, "CATEGORY_IN_USE")
        assert body["product_count"] == 1


@pytest.mark.django_db
class TestTokensOnPublicReads:
    @pytest.mark.parametrize("token", [KEYS.sign(SELLER, lifetime_seconds=-60), "not-a-jwt"], ids=["expired", "garbage"])
    def test_a_stale_token_does_not_close_a_public_read(self, token: str) -> None:
        shelf = _shelf()
        _listed("SHOE-1", shelf)
        client = APIClient()

        for path in ["/api/products/", "/api/products/SHOE-1/", "/api/categories/", f"/api/categories/{shelf.id}/"]:
            response = client.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")

            assert response.status_code == 200, path

    def test_a_public_read_does_not_wait_on_identitys_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(TokenVerifier, "_instance", TokenVerifier())
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {KEYS.sign(SELLER)}", HTTP_X_REQUEST_ID=TRACE)

        read = client.get("/api/products/")
        write = client.post("/api/products/create/", {}, format="json")

        assert read.status_code == 200
        _refusal(write, 503, "IDENTITY_KEYS_UNAVAILABLE")

    @pytest.mark.parametrize("token", [KEYS.sign(SELLER, lifetime_seconds=-60), "not-a-jwt"], ids=["expired", "garbage"])
    def test_a_bad_token_on_a_write_is_still_a_401(self, token: str) -> None:
        response = APIClient().post(
            "/api/products/create/",
            {},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_REQUEST_ID=TRACE,
        )

        _refusal(response, 401, "AUTHENTICATION_FAILED")
        assert response["WWW-Authenticate"] == "Bearer"

    def test_a_write_without_a_token_is_a_401(self) -> None:
        response = APIClient().post("/api/products/create/", {}, format="json", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 401, "NOT_AUTHENTICATED")
        assert response["WWW-Authenticate"] == "Bearer"


class TestTheHttpServerNeedsItsTokenSettings:
    @pytest.mark.parametrize("missing", sorted(VERIFIER_ENV))
    def test_it_does_not_start_without_one(self, monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
        monkeypatch.delenv(missing)
        monkeypatch.setattr(TokenVerifier, "_instance", None)
        monkeypatch.delitem(sys.modules, "config.wsgi", raising=False)

        with pytest.raises(RuntimeError, match=missing):
            importlib.import_module("config.wsgi")

    def test_it_starts_with_all_three(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(TokenVerifier, "_instance", None)
        monkeypatch.delitem(sys.modules, "config.wsgi", raising=False)

        importlib.import_module("config.wsgi")

        assert TokenVerifier._instance is not None


@pytest.mark.django_db
class TestOneShapeForProducts:
    def test_the_list_answers_the_slug_it_filters_by(self) -> None:
        _listed("SHOE-1", _shelf("running-shoes"))

        response = APIClient().get("/api/products/", {"category": "running-shoes"})

        summary = response.json()["results"][0]
        assert summary["category_slug"] == "running-shoes"
        assert summary["category"] == "Running-Shoes"

    def test_an_update_answers_the_fields_a_create_and_a_read_do(self) -> None:
        shelf = _shelf()
        client = _as(SELLER)
        created = client.post(
            "/api/products/create/",
            {"sku": "SHOE-3", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
        )

        updated = client.put(f"/api/products/manage/{created.json()['id']}/", {"title": "Shoe, renamed"}, format="json")
        read = APIClient().get("/api/products/SHOE-3/")

        assert updated.status_code == 200
        assert set(updated.json()) == set(created.json())
        assert updated.json()["category_id"] == shelf.id
        assert set(read.json()) - {"warehouse_stock"} <= set(updated.json())
        assert updated.json()["title"] == read.json()["title"] == "Shoe, renamed"

    def test_a_sku_cannot_change_once_the_product_exists(self) -> None:
        product = _listed("SHOE-4", _shelf())

        response = _as(SELLER).put(
            f"/api/products/manage/{product.id}/",
            {"sku": "SHOE-4-NEW", "title": "Renamed"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        body = _refusal(response, 400, "INVALID_INPUT")
        assert body["field"] == "sku"
        assert DjangoProductRepository().find_by_id(product.id or 0) == product

    def test_a_bad_body_is_a_400_even_while_identity_is_down(self) -> None:
        shelf = _shelf()
        di._identity_client = FakeIdentityServicePort(unavailable=True)

        response = _as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-5", "title": "Shoe", "price": "-1", "category_id": shelf.id, "weight_grams": 300},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        body = _refusal(response, 400, "INVALID_INPUT")
        assert body["field"] == "price"

    def test_a_good_body_while_identity_is_down_is_a_503(self) -> None:
        shelf = _shelf()
        di._identity_client = FakeIdentityServicePort(unavailable=True)

        response = _as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-6", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        _refusal(response, 503, "IDENTITY_UNAVAILABLE")
        assert response["Retry-After"] == "15"

    def test_a_body_that_is_not_an_object_is_refused(self) -> None:
        response = _as(SELLER).post("/api/products/create/", ["sku"], format="json", HTTP_X_REQUEST_ID=TRACE)

        body = _refusal(response, 400, "INVALID_INPUT")
        assert body["field"] == "body"

    @pytest.mark.parametrize("field", ["sku", "title", "description", "image_url"])
    def test_text_postgres_could_not_hold_is_a_400_not_a_500(self, field: str) -> None:
        shelf = _shelf()
        body: Dict[str, object] = {
            "sku": "SHOE-10",
            "title": "Shoe",
            "description": "",
            "image_url": "https://img.example.test/shoe.png",
            "price": "1000.00",
            "category_id": shelf.id,
            "weight_grams": 300,
        }
        body[field] = "https://img.example.test/a\x00b.png" if field == "image_url" else "a\x00b"

        response = _as(SELLER).post("/api/products/create/", body, format="json", HTTP_X_REQUEST_ID=TRACE)

        refused = _refusal(response, 400, "INVALID_INPUT")
        assert refused["field"] == field

    def test_a_merchant_identity_refuses_is_a_403(self) -> None:
        shelf = _shelf()
        di._identity_client = FakeIdentityServicePort(status="pending", may_sell=False)

        response = _as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-7", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        _refusal(response, 403, "MERCHANT_MAY_NOT_SELL")

    def test_another_merchants_product_is_a_403(self) -> None:
        product = _listed("SHOE-8", _shelf())

        response = _as(RIVAL).put(f"/api/products/manage/{product.id}/", {"title": "Mine"}, format="json", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 403, "NOT_PRODUCT_OWNER")

    def test_a_taken_sku_is_a_409(self) -> None:
        shelf = _shelf()
        _listed("SHOE-9", shelf, merchant="rival-1")

        response = _as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-9", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        _refusal(response, 409, "SKU_TAKEN")

    @pytest.mark.parametrize(
        ("method", "path"),
        [("get", "/api/products/NO-SUCH-SKU/"), ("put", "/api/products/manage/999999/"), ("delete", "/api/products/manage/999999/")],
    )
    def test_an_unknown_product_is_a_404(self, method: str, path: str) -> None:
        response = getattr(_as(SELLER), method)(path, {}, format="json", HTTP_X_REQUEST_ID=TRACE)

        _refusal(response, 404, "PRODUCT_NOT_FOUND")
