from typing import FrozenSet, Optional

import psycopg
from django.db import InterfaceError, OperationalError

_CONNECTION_EXCEPTION_CLASS = "08"
_SERVER_NOT_SERVING: FrozenSet[str] = frozenset(
    {
        "57P01",
        "57P02",
        "57P03",
        "53300",
    }
)


def is_database_unavailable(error: BaseException) -> bool:
    if isinstance(error, InterfaceError):
        return True

    if not isinstance(error, OperationalError):
        return False

    cause = error.__cause__
    if not isinstance(cause, psycopg.Error):
        return False

    sqlstate: Optional[str] = cause.sqlstate
    if sqlstate is None:
        return True

    return sqlstate.startswith(_CONNECTION_EXCEPTION_CLASS) or sqlstate in _SERVER_NOT_SERVING
