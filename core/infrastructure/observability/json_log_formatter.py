import json
import logging
from datetime import datetime, timezone
from typing import Dict, FrozenSet, Union

JsonScalar = Union[str, int, float, bool, None]

REQUEST_ID_FIELD = "request_id"
NO_REQUEST_ID = "-"

_RECORD_OWN_FIELDS: FrozenSet[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, JsonScalar] = {
            "timestamp": _timestamp_of(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            REQUEST_ID_FIELD: _request_id_of(record),
        }

        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info is not None:
            payload["stack"] = self.formatStack(record.stack_info)

        for key, value in _context_of(record).items():
            payload.setdefault(key, value)

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _timestamp_of(record: logging.LogRecord) -> str:
    when = datetime.fromtimestamp(record.created, tz=timezone.utc)
    return when.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _request_id_of(record: logging.LogRecord) -> str:
    request_id = getattr(record, REQUEST_ID_FIELD, None)
    if isinstance(request_id, str):
        return request_id

    return NO_REQUEST_ID


def _context_of(record: logging.LogRecord) -> Dict[str, JsonScalar]:
    context: Dict[str, JsonScalar] = {}

    for key, value in record.__dict__.items():
        if key in _RECORD_OWN_FIELDS or key == REQUEST_ID_FIELD or key.startswith("_"):
            continue
        if value is None or isinstance(value, (str, int, float, bool)):
            context[key] = value

    return context
