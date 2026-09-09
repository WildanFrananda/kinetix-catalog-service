import os

from prometheus_client import CollectorRegistry, generate_latest, multiprocess
from prometheus_client.registry import REGISTRY

from core.infrastructure.metrics.metrics_unavailable import MetricsUnavailable

MULTIPROCESS_DIR_ENV = "PROMETHEUS_MULTIPROC_DIR"


def render_metrics() -> bytes:
    multiprocess_dir = os.environ.get(MULTIPROCESS_DIR_ENV)

    if multiprocess_dir is None:
        _refuse_a_single_worker_view()
        return generate_latest(REGISTRY)

    registry = CollectorRegistry()
    try:
        multiprocess.MultiProcessCollector(  # type: ignore[no-untyped-call]
            registry, path=multiprocess_dir
        )
        return generate_latest(registry)
    except (OSError, ValueError) as failure:
        raise MetricsUnavailable(
            f"the per-worker metric files under {multiprocess_dir} could not be read: {failure}"
        ) from failure


def _refuse_a_single_worker_view() -> None:
    if os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn"):
        raise MetricsUnavailable(
            f"{MULTIPROCESS_DIR_ENV} is unset under gunicorn, so this worker can see only its "
            "own counters; gunicorn.conf.py is what sets it"
        )
