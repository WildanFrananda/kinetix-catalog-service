import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.infrastructure.metrics import (
    MULTIPROCESS_DIR_ENV,
    SERVICE_NAME,
    MetricsUnavailable,
    render_metrics,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_A_WORKER_SERVING_ONE_REQUEST = (
    "from core.infrastructure.metrics.contract_metrics import HTTP_REQUESTS_TOTAL\n"
    'HTTP_REQUESTS_TOTAL.labels(method="GET", route="/health", status="200").inc()\n'
)


def _run_a_worker_against(multiprocess_dir: Path) -> None:
    finished = subprocess.run(
        [sys.executable, "-c", _A_WORKER_SERVING_ONE_REQUEST],
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "PROMETHEUS_MULTIPROC_DIR": str(multiprocess_dir),
            "PYTHONPATH": str(REPO_ROOT),
        },
        capture_output=True,
        text=True,
    )

    assert finished.returncode == 0, finished.stderr


class TestRenderMetrics:
    def test_the_body_is_prometheus_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(MULTIPROCESS_DIR_ENV, raising=False)
        monkeypatch.delenv("SERVER_SOFTWARE", raising=False)

        body = render_metrics().decode()

        assert "# HELP " in body

    def test_the_build_names_itself(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(MULTIPROCESS_DIR_ENV, raising=False)
        monkeypatch.delenv("SERVER_SOFTWARE", raising=False)

        body = render_metrics().decode()

        assert f'kinetix_build_info{{service="{SERVICE_NAME}",version="' in body

    def test_a_gunicorn_worker_with_no_shared_directory_says_it_cannot_tell(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(MULTIPROCESS_DIR_ENV, raising=False)
        monkeypatch.setenv("SERVER_SOFTWARE", "gunicorn/23.0.0")

        with pytest.raises(MetricsUnavailable):
            render_metrics()

    def test_a_directory_that_is_not_there_is_a_failed_scrape_not_an_empty_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(tmp_path / "never-created"))

        with pytest.raises(MetricsUnavailable):
            render_metrics()

    def test_outside_gunicorn_the_process_registry_is_the_whole_answer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(MULTIPROCESS_DIR_ENV, raising=False)
        monkeypatch.delenv("SERVER_SOFTWARE", raising=False)

        assert b"kinetix_build_info" in render_metrics()

    def test_an_empty_directory_is_a_failed_scrape_not_zero_requests(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(tmp_path))

        with pytest.raises(MetricsUnavailable):
            render_metrics()

    def test_a_directory_this_process_cannot_read_is_a_failed_scrape(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0o000)
        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(locked))

        try:
            with pytest.raises(MetricsUnavailable):
                render_metrics()
        finally:
            locked.chmod(0o700)

    def test_a_partial_read_is_a_failed_scrape_not_a_smaller_answer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _run_a_worker_against(tmp_path)
        for gauge_file in tmp_path.glob("gauge_*.db"):
            gauge_file.unlink()
        assert list(tmp_path.glob("counter_*.db")), "the counter file should still be readable"

        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(tmp_path))

        with pytest.raises(MetricsUnavailable):
            render_metrics()

    def test_the_merge_serves_what_every_worker_wrote(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _run_a_worker_against(tmp_path)
        _run_a_worker_against(tmp_path)
        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(tmp_path))

        body = render_metrics().decode()

        assert f'kinetix_build_info{{service="{SERVICE_NAME}",version="' in body
        assert (
            'kinetix_http_requests_total{method="GET",route="/health",status="200"} 2.0' in body
        ), body
