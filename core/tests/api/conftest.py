from typing import Iterator, cast

import pytest
from jwt import PyJWKClient

from core.api import di
from core.infrastructure.security import SigningKeySet, TokenVerifier
from core.tests.api.api_fixtures import KEYS, VERIFIER_ENV
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort


@pytest.fixture(autouse=True)
def mesh_clients_are_stubbed() -> Iterator[None]:
    bin_stock, identity = di._bin_stock_client, di._identity_client
    di._bin_stock_client = FakeBinStockServicePort()
    di._identity_client = FakeIdentityServicePort()
    yield
    di._bin_stock_client, di._identity_client = bin_stock, identity


@pytest.fixture(autouse=True)
def identity_signs_tokens(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name, value in VERIFIER_ENV.items():
        monkeypatch.setenv(name, value)
    verifier = TokenVerifier()
    monkeypatch.setattr(verifier, "_keys", SigningKeySet(cast(PyJWKClient, KEYS)))
    monkeypatch.setattr(TokenVerifier, "_instance", verifier)
    yield
