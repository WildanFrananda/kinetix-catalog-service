from pathlib import Path

import pytest

from core.infrastructure.metrics import contract_metrics

DECLARED = (
    Path(contract_metrics.__file__).resolve().parents[3] / "VERSION"
).read_text(encoding="utf-8").strip()


class TestServiceVersionResolution:
    def test_the_environment_wins_when_a_build_stamped_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KINETIX_SERVICE_VERSION", "ci-9f21c0b")

        assert contract_metrics._resolve_service_version() == "ci-9f21c0b"

    def test_the_declared_version_is_used_when_nothing_stamped_the_build(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KINETIX_SERVICE_VERSION", raising=False)

        resolved = contract_metrics._resolve_service_version()

        assert resolved == DECLARED
        assert resolved != "unknown"

    def test_an_empty_environment_variable_does_not_shadow_the_declared_version(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KINETIX_SERVICE_VERSION", "")

        assert contract_metrics._resolve_service_version() == DECLARED

    def test_a_missing_version_file_reports_unknown_rather_than_guessing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            contract_metrics, "_VERSION_FILE", Path("/nonexistent/VERSION")
        )

        assert contract_metrics._read_declared_version() == "unknown"

    def test_the_module_level_value_is_not_a_placeholder(self) -> None:
        assert contract_metrics.SERVICE_VERSION not in {"", "unknown", "0.0.0"}
