from typing import Iterator

import pytest
from django.db import connection
from prometheus_client import REGISTRY
from rest_framework.test import APIClient

from core.tests.api.api_fixtures import (
    ADMIN,
    SELLER,
    TRACE,
    category_named,
    product_listed,
    refusal,
    signed_in_as,
)


@pytest.fixture
def database_unreachable() -> Iterator[None]:
    settings = connection.settings_dict
    host, port = settings["HOST"], settings["PORT"]
    connection.close()
    settings["HOST"], settings["PORT"] = "127.0.0.1", "1"
    try:
        yield
    finally:
        connection.close()
        settings["HOST"], settings["PORT"] = host, port


@pytest.mark.django_db(transaction=True)
class TestTheDatabaseCannotBeReached:
    @pytest.mark.parametrize(
        "path",
        ["/api/products/", "/api/products/SHOE-1/", "/api/categories/", "/api/categories/1/", "/api/products/mine/"],
    )
    def test_a_read_is_a_503_not_a_500(self, path: str, database_unreachable: None) -> None:
        response = signed_in_as(SELLER).get(path, HTTP_X_REQUEST_ID=TRACE)

        body = refusal(response, 503, "DATABASE_UNAVAILABLE")
        assert "127.0.0.1" not in str(body["message"])
        assert response["Retry-After"]

    def test_a_category_write_is_a_503_and_audited_as_failed(self, database_unreachable: None) -> None:
        labels = {"action": "catalog.category_create", "outcome": "failed"}
        before = REGISTRY.get_sample_value("kinetix_admin_actions_total", labels) or 0.0

        response = signed_in_as(ADMIN).post(
            "/api/categories/",
            {"name": "Bags", "slug": "bags"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 503, "DATABASE_UNAVAILABLE")
        assert REGISTRY.get_sample_value("kinetix_admin_actions_total", labels) == before + 1

    def test_a_product_write_is_a_503_not_a_500(self, database_unreachable: None) -> None:
        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-2", "title": "Shoe", "price": "1000.00", "category_id": 1, "weight_grams": 300},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 503, "DATABASE_UNAVAILABLE")

    def test_the_catalogue_answers_again_once_the_database_is_back(self) -> None:
        product_listed("SHOE-1", category_named())

        response = APIClient().get("/api/products/SHOE-1/")

        assert response.status_code == 200
