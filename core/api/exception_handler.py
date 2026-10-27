import logging
from http import HTTPStatus
from typing import Dict, Optional

from django.conf import settings
from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent
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
from core.infrastructure.resilience import is_database_unavailable

logger = logging.getLogger(__name__)

_IDENTITY_UNAVAILABLE_MESSAGE = (
    "we could not check this merchant account right now, so the request was not "
    "applied. Nothing was created, changed or deleted."
)
_IDENTITY_RETRY_AFTER_SECONDS = "15"
_DATABASE_UNAVAILABLE_MESSAGE = (
    "the catalogue could not reach its database, so this request could not be answered. "
    "Try again shortly."
)
_DATABASE_RETRY_AFTER_SECONDS = "15"
_BODY_TOO_LARGE_MESSAGE = (
    f"the request body is larger than {settings.DATA_UPLOAD_MAX_MEMORY_SIZE} bytes, so it was not read"
)
_TOO_MANY_FIELDS_MESSAGE = (
    f"this request carries more than {settings.DATA_UPLOAD_MAX_NUMBER_FIELDS} query or form "
    "fields, so it was not read"
)
_FILES_NOT_ACCEPTED_MESSAGE = (
    "a multipart/form-data body may carry text fields only, and this one carries a file, so it was not read"
)


def api_exception_handler(exc: Exception, context: Dict[str, object]) -> Response:
    for answer_to in (_domain_refusal, _unreadable_request, _database_unavailable):
        refusal = answer_to(exc)
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


def _unreadable_request(exc: Exception) -> Optional[Response]:
    if isinstance(exc, RequestDataTooBig):
        return Response(
            error_body("BODY_TOO_LARGE", _BODY_TOO_LARGE_MESSAGE),
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    if isinstance(exc, TooManyFieldsSent):
        return Response(error_body("TOO_MANY_FIELDS", _TOO_MANY_FIELDS_MESSAGE), status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, TooManyFilesSent):
        return Response(
            error_body("FILES_NOT_ACCEPTED", _FILES_NOT_ACCEPTED_MESSAGE),
            status=status.HTTP_400_BAD_REQUEST,
        )

    return None


def _database_unavailable(exc: Exception) -> Optional[Response]:
    if not is_database_unavailable(exc):
        return None

    logger.error("the database could not be reached: %s", exc)

    return Response(
        error_body("DATABASE_UNAVAILABLE", _DATABASE_UNAVAILABLE_MESSAGE),
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": _DATABASE_RETRY_AFTER_SECONDS},
    )


def _framework_refusal(exc: Exception, response: Response) -> Dict[str, object]:
    detail = exc.detail if isinstance(exc, APIException) else None
    if isinstance(detail, ErrorDetail) and detail.code:
        return error_body(detail.code.upper(), str(detail))

    answer = HTTPStatus(response.status_code)

    return error_body(answer.name, answer.phrase)
