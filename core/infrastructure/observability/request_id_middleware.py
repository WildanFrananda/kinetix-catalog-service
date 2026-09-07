from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse

from core.infrastructure.observability.request_id_context import (
    reset_request_id,
    set_request_id,
)

HEADER = "X-Request-Id"
_META_KEY = "HTTP_X_REQUEST_ID"


class RequestIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id: Optional[str] = request.META.get(_META_KEY) or None
        token = set_request_id(request_id)

        try:
            response = self._get_response(request)
        finally:
            reset_request_id(token)

        if request_id is not None:
            response[HEADER] = request_id

        return response
