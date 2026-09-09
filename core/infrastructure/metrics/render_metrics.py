import os

from prometheus_client import CollectorRegistry, generate_latest, multiprocess
from prometheus_client.registry import REGISTRY

from core.infrastructure.metrics.contract_metrics import BUILD_INFO_NAME
from core.infrastructure.metrics.metrics_unavailable import MetricsUnavailable

MULTIPROCESS_DIR_ENV = "PROMETHEUS_MULTIPROC_DIR"

_BUILD_INFO_SAMPLE = f"{BUILD_INFO_NAME}{{".encode()


def render_metrics() -> bytes:
    multiprocess_dir = os.environ.get(MULTIPROCESS_DIR_ENV)

    if multiprocess_dir is None:
        _refuse_a_single_worker_view()
        body = generate_latest(REGISTRY)
        _refuse_a_body_that_names_no_build(body, "this process's own registry")
        return body

    _refuse_a_directory_this_process_cannot_read(multiprocess_dir)

    registry = CollectorRegistry()
    try:
        multiprocess.MultiProcessCollector(  # type: ignore[no-untyped-call]
            registry, path=multiprocess_dir
        )
        body = generate_latest(registry)
    except (OSError, ValueError) as failure:
        raise MetricsUnavailable(
            f"the per-worker metric files under {multiprocess_dir} could not be read: {failure}"
        ) from failure

    _refuse_a_body_that_names_no_build(
        body, f"the per-worker metric files under {multiprocess_dir}"
    )
    return body


def _refuse_a_single_worker_view() -> None:
    if os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn"):
        raise MetricsUnavailable(
            f"{MULTIPROCESS_DIR_ENV} is unset under gunicorn, so this worker can see only its "
            "own counters; gunicorn.conf.py is what sets it"
        )


def _refuse_a_directory_this_process_cannot_read(multiprocess_dir: str) -> None:
    if not os.path.isdir(multiprocess_dir):
        raise MetricsUnavailable(
            f"{MULTIPROCESS_DIR_ENV} points at {multiprocess_dir}, which is not a directory, "
            "so no worker's counters can be read"
        )

    if not os.access(multiprocess_dir, os.R_OK | os.X_OK):
        raise MetricsUnavailable(
            f"the per-worker metric files under {multiprocess_dir} could not be read: this "
            "process may not list that directory"
        )


def _refuse_a_body_that_names_no_build(body: bytes, source: str) -> None:
    # The invariant that makes this checkable rather than decorative: BUILD_INFO.labels(...).set(1)
    # runs at import in every process that serves this build, so a merge that read even one worker's
    # files carries it. A body without it read nothing, or read only part of what the workers wrote
    # -- an empty directory, a directory that was cleared underneath a running master, files a
    # cleaner removed. Serving that as 200 publishes "zero requests", which a dashboard cannot tell
    # apart from a quiet service. 503 says the scrape failed, and Prometheus stores up=0.
    if any(line.startswith(_BUILD_INFO_SAMPLE) for line in body.splitlines()):
        return

    raise MetricsUnavailable(
        f"{source} yielded {len(body)} bytes carrying no {BUILD_INFO_NAME} sample, so this scrape "
        "read nothing rather than measuring nothing"
    )
