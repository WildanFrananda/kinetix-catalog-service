from typing import Optional

import pytest

from core.infrastructure.observability import REQUEST_ID_MAX_LENGTH, accepted_request_id


class TestASaneRequestId:
    @pytest.mark.parametrize(
        "request_id",
        [
            pytest.param("9b2f6a4e-6c1d-4e0a-9d35-3f1c2b7a8e10", id="kong-uuid"),
            pytest.param("9b2f6a4e-6c1d-4e0a-9d35-3f1c2b7a8e10#7", id="kong-uuid-counter"),
            pytest.param("0HN1GJ6F0QPL4:00000002", id="aspnet-trace-identifier"),
            pytest.param("kinetix-trace-1757000000-42", id="estate-trace"),
            pytest.param("dGVzdA+/w==", id="base64"),
            pytest.param("a" * REQUEST_ID_MAX_LENGTH, id="longest"),
        ],
    )
    def test_is_accepted_as_it_came(self, request_id: str) -> None:
        assert accepted_request_id(request_id) == request_id

    @pytest.mark.parametrize(
        "request_id",
        [
            pytest.param(None, id="absent"),
            pytest.param("", id="empty"),
            pytest.param("a" * (REQUEST_ID_MAX_LENGTH + 1), id="too-long"),
            pytest.param("req id", id="space"),
            pytest.param("req\nid", id="newline"),
            pytest.param("req-id\n", id="trailing-newline"),
            pytest.param("req\x00id", id="nul"),
            pytest.param("réq", id="non-ascii"),
            pytest.param("٣٤", id="non-ascii-digits"),
            pytest.param('req"id', id="quote"),
            pytest.param("<script>", id="markup"),
            pytest.param("req;id", id="semicolon"),
        ],
    )
    def test_anything_else_is_not(self, request_id: Optional[str]) -> None:
        assert accepted_request_id(request_id) is None
