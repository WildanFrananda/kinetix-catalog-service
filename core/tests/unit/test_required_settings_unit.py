import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest

ROOT = Path(__file__).resolve().parents[3]
GUNICORN_CONF = ROOT / "gunicorn.conf.py"
COMPLETE: Dict[str, str] = {
    "DEBUG": "False",
    "SECRET_KEY": "settings-test-only-not-a-deployed-key-0000",
    "ALLOWED_HOSTS": "kinetix-catalog-service",
    "DB_NAME": "kinetix_catalog_test",
    "DB_USER": "kinetix_catalog_test",
    "DB_PASSWORD": "settings-test-only",
    "DB_HOST": "kinetix-catalog-db",
    "DB_PORT": "5432",
    "DB_CONN_MAX_AGE": "60",
    "LOG_LEVEL": "INFO",
}
PROBE = (
    "from django.conf import settings; "
    "database = settings.DATABASES['default']; "
    "print(settings.DEBUG, settings.ALLOWED_HOSTS, database['NAME'], database['USER'], database['HOST'], "
    "database['PORT'], database['CONN_MAX_AGE'], settings.LOGGING['root']['level'], "
    "hasattr(settings, 'WAREHOUSE_GRPC_HOST'), hasattr(settings, 'WAREHOUSE_GRPC_PORT'))"
)


def _settings_imported_with(overrides: Dict[str, str]) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SETTINGS_MODULE": "config.settings",
        **COMPLETE,
        **overrides,
    }

    return subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )


class TestEverySettingComesFromTheEnvironment:
    def test_the_values_given_are_the_values_used(self) -> None:
        imported = _settings_imported_with({})

        assert imported.returncode == 0, imported.stderr
        assert imported.stdout.split() == [
            "False",
            "['kinetix-catalog-service']",
            "kinetix_catalog_test",
            "kinetix_catalog_test",
            "kinetix-catalog-db",
            "5432",
            "60",
            "INFO",
            "False",
            "False",
        ]

    @pytest.mark.parametrize("name", sorted(COMPLETE))
    def test_a_missing_variable_stops_the_import_and_is_named(self, name: str) -> None:
        imported = _settings_imported_with({name: ""})

        assert imported.returncode != 0
        assert f"{name} is required and has no default" in imported.stderr

    @pytest.mark.parametrize("value", ["sixty", "-1", "6.0", "٦٠"])
    def test_a_connection_age_that_is_not_a_whole_number_is_refused(self, value: str) -> None:
        imported = _settings_imported_with({"DB_CONN_MAX_AGE": value})

        assert imported.returncode != 0
        assert "DB_CONN_MAX_AGE must be a whole number" in imported.stderr

    @pytest.mark.parametrize("value", ["maybe", "off", "Flase"])
    def test_a_debug_flag_that_is_neither_true_nor_false_is_refused(self, value: str) -> None:
        imported = _settings_imported_with({"DEBUG": value})

        assert imported.returncode != 0
        assert "DEBUG must be true or false" in imported.stderr

    def test_a_host_list_of_only_separators_is_refused(self) -> None:
        imported = _settings_imported_with({"ALLOWED_HOSTS": " , ,"})

        assert imported.returncode != 0
        assert "ALLOWED_HOSTS must name at least one hostname" in imported.stderr


class TestGunicornsLogLevel:
    def test_is_required_before_a_worker_is_forked(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        with pytest.raises(RuntimeError, match="LOG_LEVEL is required"):
            runpy.run_path(str(GUNICORN_CONF))

    def test_is_the_level_both_loggers_and_the_root_use(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
        monkeypatch.setenv("LOG_LEVEL", "warning")

        namespace = runpy.run_path(str(GUNICORN_CONF))

        logconfig = namespace["logconfig_dict"]
        assert logconfig["loggers"]["gunicorn.error"]["level"] == "WARNING"
        assert logconfig["root"]["level"] == "WARNING"
