from typing import Dict, Mapping, Optional

from core.infrastructure.observability import current_request_id

INTERNAL_ERROR_MESSAGE = (
    "something went wrong handling this request. No product or stock was changed "
    "unless a previous response said so."
)


def error_body(code: str, message: str, details: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    body: Dict[str, object] = {"error": code, "message": message}
    if details is not None:
        body.update(details)
    body["traceId"] = current_request_id() or "-"

    return body
