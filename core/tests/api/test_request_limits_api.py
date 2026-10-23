from typing import Dict

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from core.infrastructure.repositories import DjangoProductRepository
from core.tests.api.api_fixtures import (
    ADMIN,
    SELLER,
    TRACE,
    category_named,
    product_listed,
    refusal,
    signed_in_as,
)


def _too_many_fields() -> Dict[str, str]:
    return {f"field{n}": "x" for n in range(settings.DATA_UPLOAD_MAX_NUMBER_FIELDS + 1)}


def _larger_than_the_limit() -> str:
    return "x" * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)


@pytest.mark.django_db
class TestBodiesTooLargeToRead:
    def test_a_json_product_larger_than_the_limit_is_a_413_and_not_created(self) -> None:
        shelf = category_named()

        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {
                "sku": "SHOE-HUGE",
                "title": "Shoe",
                "description": _larger_than_the_limit(),
                "price": "1000.00",
                "category_id": shelf.id,
                "weight_grams": 300,
            },
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")
        assert DjangoProductRepository().find_by_sku("SHOE-HUGE") is None

    def test_a_json_category_larger_than_the_limit_is_a_413(self) -> None:
        response = signed_in_as(ADMIN).post(
            "/api/categories/",
            {"name": _larger_than_the_limit(), "slug": "bags"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")

    def test_a_multipart_body_larger_than_the_limit_is_a_413_not_a_500(self) -> None:
        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-FORM", "description": _larger_than_the_limit()},
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")

    def test_a_product_update_larger_than_the_limit_is_a_413(self) -> None:
        product = product_listed("SHOE-1", category_named())

        response = signed_in_as(SELLER).put(
            f"/api/products/manage/{product.id}/",
            {"description": _larger_than_the_limit()},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")
        assert DjangoProductRepository().find_by_id(product.id or 0) == product


@pytest.mark.django_db
class TestRequestsWithTooManyFields:
    def test_a_form_body_with_too_many_fields_is_a_400_not_a_500(self) -> None:
        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            _too_many_fields(),
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "TOO_MANY_FIELDS")

    def test_an_urlencoded_body_with_too_many_fields_is_a_400_not_a_500(self) -> None:
        body = "&".join(f"{name}={value}" for name, value in _too_many_fields().items())

        response = signed_in_as(ADMIN).generic(
            "POST",
            "/api/categories/",
            body,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "TOO_MANY_FIELDS")

    def test_a_listing_query_with_too_many_fields_is_a_400_not_a_500(self) -> None:
        response = APIClient().get("/api/products/", _too_many_fields(), HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 400, "TOO_MANY_FIELDS")


@pytest.mark.django_db
class TestTheFormatParameterIsNotAnOverride:
    @pytest.mark.parametrize("value", ["xml", "api", "yaml", "json"])
    def test_a_listing_answers_the_same_whatever_format_is_named(self, value: str) -> None:
        product_listed("SHOE-1", category_named())
        client = APIClient()

        plain = client.get("/api/products/")
        named = client.get("/api/products/", {"format": value})

        assert named.status_code == 200
        assert named.json() == plain.json()

    def test_a_product_page_answers_whatever_format_is_named(self) -> None:
        product_listed("SHOE-1", category_named())

        response = APIClient().get("/api/products/SHOE-1/", {"format": "xml"})

        assert response.status_code == 200
        assert response.json()["sku"] == "SHOE-1"

    def test_a_refusal_with_a_format_named_keeps_the_error_shape(self) -> None:
        response = APIClient().get("/api/categories/999999/", {"format": "xml"}, HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 404, "CATEGORY_NOT_FOUND")
