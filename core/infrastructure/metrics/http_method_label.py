from typing import FrozenSet, Optional

_REGISTERED_METHODS: FrozenSet[str] = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "CONNECT", "OPTIONS", "TRACE"}
)

OTHER_METHOD = "other"


def http_method_label(method: Optional[str]) -> str:
    if method is not None and method in _REGISTERED_METHODS:
        return method

    return OTHER_METHOD
