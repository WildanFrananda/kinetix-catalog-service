from typing import List, Optional, Tuple

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from core.infrastructure.observability import RequestIdMiddleware, current_request_id


def _served(header: Optional[str]) -> Tuple[List[Optional[str]], HttpResponse]:
    seen: List[Optional[str]] = []

    def respond(request: HttpRequest) -> HttpResponse:
        seen.append(current_request_id())
        return HttpResponse()

    factory = RequestFactory()
    request = factory.get("/health") if header is None else factory.get("/health", HTTP_X_REQUEST_ID=header)
    response = RequestIdMiddleware(respond)(request)

    return seen, response


class TestTheHttpRequestId:
    def test_a_sane_id_is_adopted_and_echoed(self) -> None:
        seen, response = _served("kinetix-trace-1757000000-42")

        assert seen == ["kinetix-trace-1757000000-42"]
        assert response["X-Request-Id"] == "kinetix-trace-1757000000-42"
        assert current_request_id() is None

    def test_a_request_without_one_runs_without_one(self) -> None:
        seen, response = _served(None)

        assert seen == [None]
        assert "X-Request-Id" not in response

    @pytest.mark.parametrize(
        "header",
        [
            pytest.param("a" * 129, id="too-long"),
            pytest.param("req id", id="space"),
            pytest.param("<script>", id="markup"),
            pytest.param("réq", id="non-ascii"),
        ],
    )
    def test_an_id_that_is_not_sane_is_neither_adopted_nor_echoed(self, header: str) -> None:
        seen, response = _served(header)

        assert seen == [None]
        assert "X-Request-Id" not in response
