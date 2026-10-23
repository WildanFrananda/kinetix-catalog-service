import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.infrastructure.metrics import MULTIPROCESS_DIR_ENV, render_metrics

REPO_ROOT = Path(__file__).resolve().parents[3]

_A_WORKER_THAT_LOADED_THE_ROUTES = "import core.api.admin_actions\n"

_A_WORKER_THAT_AUDITED_ONE_DELETE = (
    "import core.api.admin_actions\n"
    "from core.infrastructure.observability import record_admin_action\n"
    'record_admin_action("admin-1", "catalog.category_delete", "7", "done")\n'
)


def _run_a_worker(source: str, multiprocess_dir: Path) -> None:
    finished = subprocess.run(
        [sys.executable, "-c", source],
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


class TestTheAdminActionCounterAcrossWorkers:
    def test_every_action_and_outcome_is_published_at_zero_before_anything_happened(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _run_a_worker(_A_WORKER_THAT_LOADED_THE_ROUTES, tmp_path)
        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(tmp_path))

        body = render_metrics().decode()

        for action in ("catalog.category_create", "catalog.category_update", "catalog.category_delete"):
            for outcome in ("done", "refused", "failed"):
                assert f'kinetix_admin_actions_total{{action="{action}",outcome="{outcome}"}} 0.0' in body, body

    def test_the_merge_adds_what_every_worker_counted(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _run_a_worker(_A_WORKER_THAT_AUDITED_ONE_DELETE, tmp_path)
        _run_a_worker(_A_WORKER_THAT_AUDITED_ONE_DELETE, tmp_path)
        _run_a_worker(_A_WORKER_THAT_LOADED_THE_ROUTES, tmp_path)
        monkeypatch.setenv(MULTIPROCESS_DIR_ENV, str(tmp_path))

        body = render_metrics().decode()

        assert 'kinetix_admin_actions_total{action="catalog.category_delete",outcome="done"} 2.0' in body, body
        assert 'kinetix_admin_actions_total{action="catalog.category_delete",outcome="refused"} 0.0' in body, body
