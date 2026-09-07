import logging
from typing import Dict, Optional

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.infrastructure.observability import current_request_id

logger = logging.getLogger(__name__)


def api_exception_handler(exc: Exception, context: Dict[str, object]) -> Optional[Response]:
    response = drf_exception_handler(exc, context)
    trace_id = current_request_id() or "-"

    if response is not None:
        if isinstance(response.data, dict):
            response.data["traceId"] = trace_id
        else:
            response.data = {"detail": response.data, "traceId": trace_id}
        return response

    logger.exception("unhandled exception serving %s", context.get("request"))

    return Response(
        {
            "error": "INTERNAL_ERROR",
            "message": (
                "something went wrong handling this request. No product or stock was changed "
                "unless a previous response said so."
            ),
            "traceId": trace_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
