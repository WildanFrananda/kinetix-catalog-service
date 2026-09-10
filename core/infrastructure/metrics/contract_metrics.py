import os
from pathlib import Path

from prometheus_client import Counter, Gauge, Histogram

SERVICE_NAME = "kinetix-catalog-service"

_VERSION_FILE = Path(__file__).resolve().parents[3] / "VERSION"


def _read_declared_version() -> str:
    try:
        declared = _VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"

    return declared or "unknown"


def _resolve_service_version() -> str:
    return os.environ.get("KINETIX_SERVICE_VERSION") or _read_declared_version()


SERVICE_VERSION = _resolve_service_version()

BUILD_INFO_NAME = "kinetix_build_info"

HTTP_REQUESTS_TOTAL = Counter(
    "kinetix_http_requests_total",
    "HTTP requests served, by method, matched route template and response status.",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "kinetix_http_request_duration_seconds",
    "Seconds spent serving an HTTP request, measured around the middleware chain below this one.",
    ["method", "route"],
)

GRPC_CLIENT_CALLS_TOTAL = Counter(
    "kinetix_grpc_client_calls_total",
    "Outbound gRPC calls that reached a peer and finished, by peer, method and status code.",
    ["peer", "grpc_method", "grpc_code"],
)

BUILD_INFO = Gauge(
    BUILD_INFO_NAME,
    "Always 1. The labels say which service and which build answered the scrape.",
    ["service", "version"],
    multiprocess_mode="max",
)
BUILD_INFO.labels(service=SERVICE_NAME, version=SERVICE_VERSION).set(1)
