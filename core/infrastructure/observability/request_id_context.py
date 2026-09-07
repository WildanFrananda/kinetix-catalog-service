from contextvars import ContextVar, Token
from typing import Optional

REQUEST_ID_HEADER = "x-request-id"

_request_id: ContextVar[Optional[str]] = ContextVar("kinetix_request_id", default=None)


def current_request_id() -> Optional[str]:
    """The correlation id of the request this code is serving, or None outside one."""
    return _request_id.get()


def set_request_id(request_id: Optional[str]) -> Token[Optional[str]]:
    """Sets the id for this context and returns the token that restores what was there before."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[Optional[str]]) -> None:
    """
    Restores the previous id.

    A context variable outlives the request on a reused worker thread, so a missed reset would
    log one customer's work under another customer's id.
    """
    _request_id.reset(token)
