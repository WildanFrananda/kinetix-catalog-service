"""Wiring for the API layer.

The clients here are process-wide singletons, built once and lazily.

They used to be constructed inside `get_product_service()`, which every handler calls on every
request. `BinStockGrpcClient.__init__` opens a gRPC channel — a TCP connection, a TLS handshake and
the service certificate read from disk — so the service paid all of that per request and left the
previous channel to the garbage collector. It also made a circuit breaker impossible: a breaker's
state lives on the client, and a client discarded each request is a breaker that resets each
request and can never open.

Lazy rather than at import: the clients call `required_env` in their constructors, and a module
imported before the environment is populated would fail at import time rather than at first use,
which is much harder to read. The lock makes first use safe under gunicorn's threaded workers;
after that the fast path is a plain attribute read.
"""

import threading
from typing import Optional

from core.application.services import ProductService
from core.application.services.category_service import CategoryService
from core.domain.repositories import BinStockServicePort, IdentityServicePort
from core.infrastructure.grpc.bin_stock_client import BinStockGrpcClient
from core.infrastructure.grpc.identity_client import IdentityGrpcClient
from core.infrastructure.repositories import DjangoProductRepository

_lock = threading.Lock()
_bin_stock_client: Optional[BinStockServicePort] = None
_identity_client: Optional[IdentityServicePort] = None


def get_bin_stock_client() -> BinStockServicePort:
    global _bin_stock_client
    if _bin_stock_client is None:
        with _lock:
            if _bin_stock_client is None:
                _bin_stock_client = BinStockGrpcClient()
    return _bin_stock_client


def get_identity_client() -> IdentityServicePort:
    global _identity_client
    if _identity_client is None:
        with _lock:
            if _identity_client is None:
                _identity_client = IdentityGrpcClient()
    return _identity_client


def get_product_service() -> ProductService:
    # The repository is cheap and stateless; only the network clients are shared.
    return ProductService(
        product_repo=DjangoProductRepository(),
        bin_stock_port=get_bin_stock_client(),
        identity_port=get_identity_client(),
    )


def get_category_service() -> CategoryService:
    return CategoryService(product_repo=DjangoProductRepository())
