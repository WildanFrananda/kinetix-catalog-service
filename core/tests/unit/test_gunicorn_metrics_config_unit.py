import os
import runpy
import sys
from pathlib import Path
from typing import Iterator

import pytest

CONF = Path(__file__).resolve().parents[3] / "gunicorn.conf.py"


@pytest.fixture
def clean_prometheus_import() -> Iterator[None]:
    saved_env = os.environ.pop("PROMETHEUS_MULTIPROC_DIR", None)
    saved_modules = {k: v for k, v in sys.modules.items() if k.startswith("prometheus_client")}
    for name in saved_modules:
        del sys.modules[name]
    try:
        yield
    finally:
        os.environ.pop("PROMETHEUS_MULTIPROC_DIR", None)
        if saved_env is not None:
            os.environ["PROMETHEUS_MULTIPROC_DIR"] = saved_env
        for name in [k for k in sys.modules if k.startswith("prometheus_client")]:
            del sys.modules[name]
        sys.modules.update(saved_modules)


def test_loading_the_config_selects_the_multiprocess_value_class(
    clean_prometheus_import: None,
) -> None:
    runpy.run_path(str(CONF))

    from prometheus_client import values

    assert values.ValueClass.__name__ == "MmapedValue", (
        "prometheus_client chose the single-process ValueClass, which means "
        "PROMETHEUS_MULTIPROC_DIR was still unset when it was imported. Each gunicorn worker will "
        "keep its own counts and a scrape will report one of them."
    )


def test_the_environment_assignment_precedes_the_prometheus_import(
    clean_prometheus_import: None,
) -> None:
    source = CONF.read_text()
    assignment = source.index("PROMETHEUS_MULTIPROC_DIR")
    prometheus_import = source.index("from prometheus_client")

    assert assignment < prometheus_import, (
        "the PROMETHEUS_MULTIPROC_DIR assignment moved below the prometheus_client import; "
        "prometheus_client reads that variable at import time and never re-reads it"
    )
