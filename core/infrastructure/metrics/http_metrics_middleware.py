import logging
from time import perf_counter
from typing import Callable

from django.http import HttpRequest, HttpResponse

from core.infrastructure.metrics.contract_metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)
from core.infrastructure.metrics.http_method_label import http_method_label
from core.infrastructure.metrics.route_template import route_template

logger = logging.getLogger(__name__)


class HttpMetricsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started = perf_counter()

        try:
            response = self._get_response(request)
        except Exception:
            self._record(request, "500", perf_counter() - started)
            raise

        self._record(request, str(response.status_code), perf_counter() - started)
        return response

    def _record(self, request: HttpRequest, status: str, elapsed_seconds: float) -> None:
        method = http_method_label(request.method)
        route = route_template(request.resolver_match)

        try:
            HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status=status).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route).observe(
                elapsed_seconds
            )
        except Exception as failure:
            logger.error(
                "could not record HTTP metrics for %s %s: %s", method, route, failure
            )
