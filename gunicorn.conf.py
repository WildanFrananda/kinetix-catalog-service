import os
import shutil
from typing import Protocol

from prometheus_client import multiprocess

METRICS_DIR = os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/kinetix-catalog-metrics")

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

graceful_timeout = 25

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "core.infrastructure.observability.request_id_log_filter.RequestIdLogFilter",
        },
    },
    "formatters": {
        "json": {
            "()": "core.infrastructure.observability.json_log_formatter.JsonLogFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "filters": ["request_id"],
            "formatter": "json",
        },
    },
    "loggers": {
        "gunicorn.error": {"handlers": ["console"], "level": _LOG_LEVEL, "propagate": False},
        "gunicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": _LOG_LEVEL},
}


class _Worker(Protocol):
    pid: int


def on_starting(server: object) -> None:
    shutil.rmtree(METRICS_DIR, ignore_errors=True)
    os.makedirs(METRICS_DIR, exist_ok=True)


def child_exit(server: object, worker: _Worker) -> None:
    multiprocess.mark_process_dead(worker.pid)
