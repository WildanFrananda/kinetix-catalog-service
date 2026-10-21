import logging
from http import HTTPStatus
from typing import Dict, Optional

from rest_framework import status
from rest_framework.exceptions import APIException, ErrorDetail
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.api.error_body import INTERNAL_ERROR_MESSAGE, error_body
from core.domain.errors import (
    CategoryInUseError,
    CategoryTakenError,
    IdentityUnavailableError,
    InvalidInputError,
    MerchantMayNotSellError,
    ProductNotOwnedError,
    SkuTakenError,
)

logger = logging.getLogger(__name__)

_IDENTITY_UNAVAILABLE_MESSAGE = (
    "we could not check this merchant account right now, so the request was not "
    "applied. Nothing was created, changed or deleted."
)
_IDENTITY_RETRY_AFTER_SECONDS = "15"


def api_exception_handler(exc: Exception, context: Dict[str, object]) -> Response:
    refusal = _domain_refusal(exc)
    if refusal is not None:
        return refusal

    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = _framework_refusal(exc, response)
        return response

    logger.exception("unhandled exception serving %s", context.get("request"))

    return Response(
        error_body("INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _domain_refusal(exc: Exception) -> Optional[Response]:
    if isinstance(exc, InvalidInputError):
        return Response(
            error_body("INVALID_INPUT", exc.reason, {"field": exc.field}),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, SkuTakenError):
        return Response(error_body("SKU_TAKEN", str(exc)), status=status.HTTP_409_CONFLICT)

    if isinstance(exc, CategoryTakenError):
        return Response(error_body("CATEGORY_TAKEN", str(exc)), status=status.HTTP_409_CONFLICT)

    if isinstance(exc, CategoryInUseError):
        return Response(
            error_body("CATEGORY_IN_USE", str(exc), {"product_count": exc.product_count}),
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, MerchantMayNotSellError):
        return Response(error_body("MERCHANT_MAY_NOT_SELL", exc.reason), status=status.HTTP_403_FORBIDDEN)

    if isinstance(exc, ProductNotOwnedError):
        return Response(error_body("NOT_PRODUCT_OWNER", str(exc)), status=status.HTTP_403_FORBIDDEN)

    if isinstance(exc, IdentityUnavailableError):
        return Response(
            error_body("IDENTITY_UNAVAILABLE", _IDENTITY_UNAVAILABLE_MESSAGE),
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": _IDENTITY_RETRY_AFTER_SECONDS},
        )

    return None


def _framework_refusal(exc: Exception, response: Response) -> Dict[str, object]:
    detail = exc.detail if isinstance(exc, APIException) else None
    if isinstance(detail, ErrorDetail) and detail.code:
        return error_body(detail.code.upper(), str(detail))

    answer = HTTPStatus(response.status_code)

    return error_body(answer.name, answer.phrase, {"details": response.data})
