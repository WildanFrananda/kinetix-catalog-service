from pathlib import Path

import pytest

from core.infrastructure.metrics import (
    MULTIPROCESS_DIR_ENV,
    SERVICE_NAME,
    MetricsUnavailable,
    render_metrics,
)


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
