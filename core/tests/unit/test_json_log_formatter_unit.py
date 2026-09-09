import json
import logging
from typing import Dict, Optional, Tuple

from core.infrastructure.observability import JsonLogFormatter, RequestIdLogFilter
from core.infrastructure.observability.request_id_context import reset_request_id, set_request_id


def _record(message: str, args: Optional[Tuple[object, ...]] = None) -> logging.LogRecord:
    return logging.LogRecord(
        name="core.api.views.product_view",
        level=logging.INFO,
        pathname="product_view.py",
        lineno=42,
        msg=message,
        args=args,
        exc_info=None,
    )


def _formatted(record: logging.LogRecord) -> Dict[str, object]:
    RequestIdLogFilter().filter(record)
    line = JsonLogFormatter().format(record)

    assert "\n" not in line, "one event is one line"
    parsed = json.loads(line)
    assert isinstance(parsed, dict)
    return parsed


class TestJsonLogFormatter:
    def test_the_line_carries_the_five_fields_the_estate_reads(self) -> None:
        token = set_request_id("kinetix-trace-1757000000-42")
        try:
            payload = _formatted(_record("GET /api/products/ -> 200"))
        finally:
            reset_request_id(token)

        assert payload["level"] == "INFO"
        assert payload["logger"] == "core.api.views.product_view"
        assert payload["message"] == "GET /api/products/ -> 200"
        assert payload["request_id"] == "kinetix-trace-1757000000-42"
        assert isinstance(payload["timestamp"], str)

    def test_a_plain_grep_for_the_correlation_id_still_matches_the_line(self) -> None:
        correlation_id = "kinetix-forward-1757000000-42"
        token = set_request_id(correlation_id)
        try:
            record = _record("asked warehouse about SKU-1")
            RequestIdLogFilter().filter(record)
            line = JsonLogFormatter().format(record)
        finally:
            reset_request_id(token)

        assert correlation_id in line

    def test_an_event_outside_a_request_says_so_rather_than_borrowing_an_id(self) -> None:
        payload = _formatted(_record("circuit 'identity-merchant' opened"))

        assert payload["request_id"] == "-"

    def test_the_message_is_the_interpolated_one(self) -> None:
        payload = _formatted(_record("stock for %s is unknown", ("SKU-1",)))

        assert payload["message"] == "stock for SKU-1 is unknown"

    def test_scalar_context_survives_and_objects_do_not(self) -> None:
        record = _record("readiness check failed")
        record.attempt = 2
        record.database = "unreachable"
        record.request = object()

        payload = _formatted(record)

        assert payload["attempt"] == 2
        assert payload["database"] == "unreachable"
        assert "request" not in payload

    def test_a_traceback_stays_on_the_line_of_the_event_that_raised_it(self) -> None:
        try:
            raise ValueError("pricing could not be reached")
        except ValueError:
            import sys

            record = _record("unhandled exception serving the request")
            record.exc_info = sys.exc_info()

        payload = _formatted(record)

        exception: Optional[object] = payload.get("exception")
        assert isinstance(exception, str)
        assert "ValueError: pricing could not be reached" in exception
