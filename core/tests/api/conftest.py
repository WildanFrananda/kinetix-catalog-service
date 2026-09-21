from typing import Iterator

import pytest

from core.api import di
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort


@pytest.fixture(autouse=True)
def mesh_clients_are_stubbed() -> Iterator[None]:
    bin_stock, identity = di._bin_stock_client, di._identity_client
    di._bin_stock_client = FakeBinStockServicePort()
    di._identity_client = FakeIdentityServicePort()
    yield
    di._bin_stock_client, di._identity_client = bin_stock, identity
