from datetime import datetime, timezone
from typing import List

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.api import di
from core.infrastructure.models import ProductModel
from core.infrastructure.security import Principal, TokenVerifier
from core.tests.api.api_fixtures import (
    ADMIN,
    CUSTOMER,
    KEYS,
    RIVAL,
    SELLER,
    TRACE,
    category_named,
    product_listed,
    refusal,
    signed_in_as,
)
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort
from core.tests.unit.fake_unreachable_bin_stock_service_port import FakeUnreachableBinStockServicePort

COURIER = Principal(principal_id="courier-1", email="courier@example.test", role="courier")


def _skus(body: object) -> List[str]:
    assert isinstance(body, dict)
    results = body["results"]
    assert isinstance(results, list)

    return [str(row["sku"]) for row in results]


@pytest.mark.django_db
class TestASellersOwnProducts:
    def test_lists_the_callers_products_withdrawn_ones_included_and_no_one_elses(self) -> None:
        shelf = category_named()
        product_listed("SHOE-1", shelf)
        withdrawn = product_listed("SHOE-2", shelf)
        product_listed("RIVAL-1", shelf, merchant=RIVAL.principal_id)
        assert withdrawn.id is not None
        ProductModel.objects.filter(id=withdrawn.id).update(is_active=False)

        response = signed_in_as(SELLER).get("/api/products/mine/")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert sorted(_skus(body)) == ["SHOE-1", "SHOE-2"]
        states = {row["sku"]: row["is_active"] for row in body["results"]}
        assert states == {"SHOE-1": True, "SHOE-2": False}

    def test_a_row_is_the_record_a_create_answers(self) -> None:
        shelf = category_named()
        client = signed_in_as(SELLER)
        created = client.post(
            "/api/products/create/",
            {"sku": "SHOE-3", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
        )

        listed = client.get("/api/products/mine/").json()

        assert listed["results"] == [created.json()]

    def test_is_served_with_and_without_the_trailing_slash(self) -> None:
        product_listed("SHOE-1", category_named())
        client = signed_in_as(SELLER)

        bare = client.get("/api/products/mine")
        slashed = client.get("/api/products/mine/")

        assert bare.status_code == slashed.status_code == 200
        assert bare.json() == slashed.json()
        assert reverse("product-mine") == "/api/products/mine/"

    def test_pages_are_newest_first_and_every_product_appears_once(self) -> None:
        shelf = category_named()
        for n in range(5):
            product_listed(f"SHOE-{n}", shelf)
        client = signed_in_as(SELLER)

        pages = [client.get("/api/products/mine/", {"page": page, "page_size": 2}).json() for page in (1, 2, 3)]

        assert [page["count"] for page in pages] == [5, 5, 5]
        assert [page["page"] for page in pages] == [1, 2, 3]
        assert [page["page_size"] for page in pages] == [2, 2, 2]
        assert [sku for page in pages for sku in _skus(page)] == ["SHOE-4", "SHOE-3", "SHOE-2", "SHOE-1", "SHOE-0"]

    def test_products_written_at_the_same_instant_keep_one_order_across_pages(self) -> None:
        shelf = category_named()
        for n in range(6):
            product_listed(f"SHOE-{n}", shelf)
        ProductModel.objects.update(created_at=datetime(2026, 10, 22, tzinfo=timezone.utc))
        client = signed_in_as(SELLER)

        walked = [
            sku
            for page in (1, 2, 3)
            for sku in _skus(client.get("/api/products/mine/", {"page": page, "page_size": 2}).json())
        ]

        assert walked == ["SHOE-5", "SHOE-4", "SHOE-3", "SHOE-2", "SHOE-1", "SHOE-0"]

    def test_filters_like_the_public_listing(self) -> None:
        shoes = category_named("footwear")
        bags = category_named("bags")
        product_listed("SHOE-1", shoes)
        product_listed("BAG-1", bags)

        response = signed_in_as(SELLER).get("/api/products/mine/", {"category": "bags"})

        assert _skus(response.json()) == ["BAG-1"]

    def test_a_query_that_is_not_a_page_is_a_400(self) -> None:
        response = signed_in_as(SELLER).get("/api/products/mine/", {"page": "0"}, HTTP_X_REQUEST_ID=TRACE)

        body = refusal(response, 400, "INVALID_INPUT")
        assert body["field"] == "page"

    def test_neither_identity_nor_warehouse_is_asked(self) -> None:
        product_listed("SHOE-1", category_named())
        di._identity_client = FakeIdentityServicePort(unavailable=True)
        di._bin_stock_client = FakeUnreachableBinStockServicePort()

        response = signed_in_as(SELLER).get("/api/products/mine/")

        assert response.status_code == 200
        assert _skus(response.json()) == ["SHOE-1"]


@pytest.mark.django_db
class TestOnlyASellerMayAsk:
    def test_without_a_token_is_a_401(self) -> None:
        response = APIClient().get("/api/products/mine/", HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 401, "NOT_AUTHENTICATED")
        assert response["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize("token", [KEYS.sign(SELLER, lifetime_seconds=-60), "not-a-jwt"], ids=["expired", "garbage"])
    def test_a_bad_token_is_a_401(self, token: str) -> None:
        response = APIClient().get(
            "/api/products/mine/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 401, "AUTHENTICATION_FAILED")

    @pytest.mark.parametrize("principal", [CUSTOMER, COURIER, ADMIN], ids=["customer", "courier", "admin"])
    def test_an_account_that_is_not_a_seller_is_a_403(self, principal: Principal) -> None:
        response = signed_in_as(principal).get("/api/products/mine/", HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 403, "SELLER_REQUIRED")

    def test_identitys_keys_unreachable_is_a_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(TokenVerifier, "_instance", TokenVerifier())

        response = signed_in_as(SELLER).get("/api/products/mine/", HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 503, "IDENTITY_KEYS_UNAVAILABLE")


@pytest.mark.django_db
class TestASkuNamedLikeTheListing:
    def test_is_refused_at_create(self) -> None:
        shelf = category_named()

        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {"sku": "mine", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        body = refusal(response, 400, "INVALID_INPUT")
        assert body["field"] == "sku"
