import runpy
from pathlib import Path

import pytest

CONF = Path(__file__).resolve().parents[3] / "gunicorn.conf.py"


class TestGunicornAccessLogConfig:
    def test_the_access_line_carries_the_path_without_the_query_string(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))

        namespace = runpy.run_path(str(CONF))

        assert "access_log_format" in namespace, (
            "gunicorn falls back to its default access line, whose %(r)s is the whole request "
            "line: a shopper's query string lands in the log stream"
        )
        access_log_format = namespace["access_log_format"]
        assert "%(U)s" in access_log_format
        assert "%(r)s" not in access_log_format, (
            "%(r)s is the full request line including the query string; %(U)s is the path alone"
        )
        assert "%(q)s" not in access_log_format
