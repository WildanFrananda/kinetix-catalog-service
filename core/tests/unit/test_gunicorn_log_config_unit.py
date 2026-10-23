import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

_GUNICORN_CONFIGURES_ITS_LOGGING = (
    "import logging.config\n"
    "import runpy\n"
    "namespace = runpy.run_path('gunicorn.conf.py')\n"
    "logging.config.dictConfig(namespace['logconfig_dict'])\n"
)

_THE_LOG_FORMATTER_IS_IMPORTED = (
    "import sys\n"
    "import core.infrastructure.observability.json_log_formatter\n"
    "loaded = sorted(name for name in sys.modules if name.startswith('prometheus_client'))\n"
    "assert not loaded, loaded\n"
)


def _run(source: str, multiprocess_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "PROMETHEUS_MULTIPROC_DIR": str(multiprocess_dir),
            "PYTHONPATH": str(REPO_ROOT),
            "LOG_LEVEL": "info",
        },
        capture_output=True,
        text=True,
    )


class TestGunicornConfiguresItsLoggingBeforeTheMetricsDirectoryExists:
    def test_the_logging_configuration_applies_while_the_metrics_directory_is_still_missing(
        self, tmp_path: Path
    ) -> None:
        not_made_yet = tmp_path / "made-by-on_starting"

        finished = _run(_GUNICORN_CONFIGURES_ITS_LOGGING, not_made_yet)

        assert finished.returncode == 0, (
            "gunicorn applies logconfig_dict before its on_starting hook makes the metrics directory, "
            "so anything the log formatter or filter imports must not create a metric; it did, and "
            "gunicorn died with \"Unable to configure formatter 'json'\":\n" + finished.stderr
        )

    def test_importing_the_log_formatter_loads_no_metrics_library(self, tmp_path: Path) -> None:
        finished = _run(_THE_LOG_FORMATTER_IS_IMPORTED, tmp_path / "unused")

        assert finished.returncode == 0, finished.stderr
