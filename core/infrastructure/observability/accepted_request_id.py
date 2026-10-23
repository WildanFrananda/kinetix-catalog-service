import re
from typing import Optional

REQUEST_ID_MAX_LENGTH = 128

_REQUEST_ID_SHAPE = re.compile(r"[A-Za-z0-9._:#/+=-]+")


def accepted_request_id(raw: Optional[str]) -> Optional[str]:
    if raw is None or len(raw) > REQUEST_ID_MAX_LENGTH:
        return None

    if _REQUEST_ID_SHAPE.fullmatch(raw) is None:
        return None

    return raw
