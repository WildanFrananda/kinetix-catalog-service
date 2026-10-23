import json
import logging
from logging.handlers import BufferingHandler
from typing import Callable, Iterator, List, Optional, Sequence, Tuple, cast

import grpc
import pytest
from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from grpc_health.v1 import health

from core.infrastructure.grpc.catalog_grpc_server import catalog_grpc_server
from core.infrastructure.observability import REQUEST_ID_HEADER, JsonLogFormatter, RequestIdLogFilter
from core.infrastructure.security.peer_authorization_interceptor import PeerAuthorizationInterceptor

ALLOWED_CALLER = "search"
REFUSED_CALLER = "review"
COUNT_PRODUCTS = "/catalog.v1.CatalogService/CountProducts"
TIMEOUT_SECONDS = 15


def _peer_named(name: str) -> Callable[[PeerAuthorizationInterceptor, grpc.ServicerContext], Optional[str]]:
    def peer_of(_interceptor: PeerAuthorizationInterceptor, _context: grpc.ServicerContext) -> Optional[str]:
        return name

    return peer_of


@pytest.fixture
def catalog(monkeypatch: pytest.MonkeyPatch) -> Iterator[catalog_pb2_grpc.CatalogServiceStub]:
    monkeypatch.setattr(PeerAuthorizationInterceptor, "peer_of", _peer_named(REFUSED_CALLER))

    server = catalog_grpc_server(frozenset({ALLOWED_CALLER}), 1, health.HealthServicer())
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    try:
        yield catalog_pb2_grpc.CatalogServiceStub(channel)
    finally:
        channel.close()
        server.stop(grace=None).wait()


@pytest.fixture
def logged() -> Iterator[List[logging.LogRecord]]:
    handler = BufferingHandler(capacity=10_000)
    handler.addFilter(RequestIdLogFilter())
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield handler.buffer
    finally:
        root.removeHandler(handler)


def _refused(catalog: catalog_pb2_grpc.CatalogServiceStub, metadata: Sequence[Tuple[str, str]]) -> None:
    with pytest.raises(grpc.RpcError) as raised:
        catalog.CountProducts(catalog_pb2.CountProductsRequest(), metadata=metadata, timeout=TIMEOUT_SECONDS)

    assert cast(grpc.Call, raised.value).code() == grpc.StatusCode.PERMISSION_DENIED


def _request_id_in(record: logging.LogRecord) -> str:
    line = json.loads(JsonLogFormatter().format(record))
    assert isinstance(line, dict)
    request_id = line["request_id"]
    assert isinstance(request_id, str)

    return request_id


def _refusals_logged(records: List[logging.LogRecord]) -> List[str]:
    refusal = f"refused a gRPC call to {COUNT_PRODUCTS} "

    return [_request_id_in(record) for record in records if record.getMessage().startswith(refusal)]


class TestTheCallersRequestIdIsAdopted:
    def test_a_refused_call_is_logged_under_the_callers_request_id(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        logged: List[logging.LogRecord],
    ) -> None:
        _refused(catalog, [(REQUEST_ID_HEADER, "kinetix-trace-1757000000-42")])

        assert _refusals_logged(logged) == ["kinetix-trace-1757000000-42"]

    def test_a_call_without_one_is_logged_without_one(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        logged: List[logging.LogRecord],
    ) -> None:
        _refused(catalog, [])

        assert _refusals_logged(logged) == ["-"]

    def test_the_id_does_not_outlive_its_call_on_the_worker_thread(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        logged: List[logging.LogRecord],
    ) -> None:
        _refused(catalog, [(REQUEST_ID_HEADER, "req-first")])
        _refused(catalog, [])

        assert _refusals_logged(logged) == ["req-first", "-"]

    @pytest.mark.parametrize(
        "request_id",
        [
            pytest.param("9b2f6a4e-6c1d-4e0a-9d35-3f1c2b7a8e10", id="kong-uuid"),
            pytest.param("9b2f6a4e-6c1d-4e0a-9d35-3f1c2b7a8e10#7", id="kong-uuid-counter"),
            pytest.param("0HN1GJ6F0QPL4:00000002", id="aspnet-trace-identifier"),
            pytest.param("a" * 128, id="longest"),
        ],
    )
    def test_an_id_in_a_shape_callers_mint_is_adopted(
        self,
        request_id: str,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        logged: List[logging.LogRecord],
    ) -> None:
        _refused(catalog, [(REQUEST_ID_HEADER, request_id)])

        assert _refusals_logged(logged) == [request_id]

    @pytest.mark.parametrize(
        "request_id",
        [
            pytest.param("a" * 129, id="too-long"),
            pytest.param("req id", id="space"),
            pytest.param("req;id", id="semicolon"),
            pytest.param("<script>", id="markup"),
            pytest.param('req"id', id="quote"),
        ],
    )
    def test_an_id_that_is_not_sane_is_ignored(
        self,
        request_id: str,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        logged: List[logging.LogRecord],
    ) -> None:
        _refused(catalog, [(REQUEST_ID_HEADER, request_id)])

        assert _refusals_logged(logged) == ["-"]
