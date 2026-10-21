from typing import Mapping

from rest_framework.request import Request

from core.domain.errors import InvalidInputError


def json_object(request: Request) -> Mapping[str, object]:
    body = request.data
    if not isinstance(body, dict):
        raise InvalidInputError("body", "must be a JSON object")

    return body
