import re

from django.urls import ResolverMatch

from core.infrastructure.metrics import UNMATCHED_ROUTE, http_method_label, route_template
from core.infrastructure.metrics.http_method_label import OTHER_METHOD


def _match(route: str) -> ResolverMatch:
    return ResolverMatch(func=lambda request: None, args=(), kwargs={}, route=route)


class TestRouteTemplate:
    def test_a_capture_becomes_a_placeholder_not_the_value_that_filled_it(self) -> None:
        assert route_template(_match("api/products/<str:sku>/")) == "/api/products/{sku}/"

    def test_every_capture_in_the_route_is_replaced(self) -> None:
        template = route_template(_match("api/categories/<int:category_id>/items/<slug:name>/"))

        assert template == "/api/categories/{category_id}/items/{name}/"

    def test_a_capture_without_a_converter_is_still_a_placeholder(self) -> None:
        assert route_template(_match("api/products/<sku>/")) == "/api/products/{sku}/"

    def test_a_route_with_no_captures_is_left_alone(self) -> None:
        assert route_template(_match("api/products/")) == "/api/products/"

    def test_an_unmatched_request_gets_one_bucket_rather_than_its_path(self) -> None:
        assert route_template(None) == UNMATCHED_ROUTE

    def test_no_route_this_service_declares_can_carry_a_digit_where_an_id_would_go(self) -> None:
        declared = [
            "admin/",
            "api/categories/",
            "api/categories/<int:category_id>/",
            "api/products/",
            "api/products/create/",
            "api/products/manage/<int:product_id>/",
            "api/products/<str:sku>/",
            "health",
            "health/ready",
            "metrics",
        ]

        templates = [route_template(_match(route)) for route in declared]

        assert [template for template in templates if re.search(r"/[0-9]+", template)] == []
        assert "/api/products/manage/{product_id}/" in templates


class TestHttpMethodLabel:
    def test_a_method_the_web_has_is_kept(self) -> None:
        assert http_method_label("DELETE") == "DELETE"

    def test_a_method_the_caller_invented_is_not(self) -> None:
        assert http_method_label("HUNTER2") == OTHER_METHOD

    def test_a_request_with_no_method_at_all_still_has_a_label(self) -> None:
        assert http_method_label(None) == OTHER_METHOD
