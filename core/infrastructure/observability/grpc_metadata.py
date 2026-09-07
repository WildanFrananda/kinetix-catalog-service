from typing import List, Optional, Tuple

from core.infrastructure.observability.request_id_context import (
    REQUEST_ID_HEADER,
    current_request_id,
)


def request_id_metadata() -> List[Tuple[str, str]]:
    request_id: Optional[str] = current_request_id()
    if request_id is None:
        return []
    return [(REQUEST_ID_HEADER, request_id)]
