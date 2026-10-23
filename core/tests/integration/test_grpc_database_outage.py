from decimal import Decimal
from typing import Callable, Iterator, Optional, Tuple, cast

import grpc
import pytest
from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from django.db import connection
from grpc_health.v1 import health, health_pb2

from core.domain.entities import Category, Product
from core.infrastructure.grpc.catalog_grpc_server import catalog_grpc_server
from core.infrastructure.grpc.error_status_interceptor import DATABASE_UNAVAILABLE_DETAILS, INTERNAL_ERROR_DETAILS
from core.infrastructure.observability import REQUEST_ID_HEADER, RequestIdLogFilter
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.security.peer_authorization_interceptor import PeerAuthorizationInterceptor

CALLER = "search"
TIMEOUT_SECONDS = 15


def _peer_named(name: str) -> Callable[[PeerAuthorizationInterceptor, grpc.ServicerContext], Optional[str]]:
    def peer_of(_interceptor: PeerAuthorizationInterceptor, _context: grpc.ServicerContext) -> Optional[str]:
        return name

    return peer_of


def _status_of(call: Callable[[], object]) -> Tuple[grpc.StatusCode, str]:
    with pytest.raises(grpc.RpcError) as raised:
        call()

    error = cast(grpc.Call, raised.value)

    return error.code(), error.details() or ""


def _listed(sku: str) -> Product:
    repo = DjangoProductRepository()
    category = repo.save_category(Category(id=None, name="Footwear", slug="footwear"))

    return repo.save(
        Product(
            id=None,
            sku=sku,
            title=f"Shoe {sku}",
            description="",
            price=Decimal("150000.00"),
            currency="IDR",
            image_url="",
            category=category,
            merchant_principal_id="seller-1",
            weight_grams=500,
        )
    )


def _transaction_cursor() -> catalog_pb2.ChangedSinceRequest:
    request = catalog_pb2.ChangedSinceRequest(limit=10)
    request.cursor.transaction_id = 0

    return request


def _get_product(catalog: catalog_pb2_grpc.CatalogServiceStub) -> object:
    return catalog.GetProduct(catalog_pb2.GetProductRequest(sku="SHOE-1"), timeout=TIMEOUT_SECONDS)


def _changed_since_a_transaction(catalog: catalog_pb2_grpc.CatalogServiceStub) -> object:
    return catalog.ChangedSince(_transaction_cursor(), timeout=TIMEOUT_SECONDS)


def _changed_since_a_time(catalog: catalog_pb2_grpc.CatalogServiceStub) -> object:
    return catalog.ChangedSince(catalog_pb2.ChangedSinceRequest(limit=10), timeout=TIMEOUT_SECONDS)


def _count_products(catalog: catalog_pb2_grpc.CatalogServiceStub) -> object:
    return catalog.CountProducts(catalog_pb2.CountProductsRequest(), timeout=TIMEOUT_SECONDS)


@pytest.fixture
def channel(monkeypatch: pytest.MonkeyPatch) -> Iterator[grpc.Channel]:
    monkeypatch.setattr(PeerAuthorizationInterceptor, "peer_of", _peer_named(CALLER))
    monkeypatch.setitem(connection.settings_dict, "CONN_MAX_AGE", 0)

    health_servicer = health.HealthServicer()
    server = catalog_grpc_server(frozenset({CALLER}), 2, health_servicer)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    opened = grpc.insecure_channel(f"127.0.0.1:{port}")
    try:
        yield opened
    finally:
        opened.close()
        server.stop(grace=None).wait()


@pytest.fixture
def catalog(channel: grpc.Channel) -> catalog_pb2_grpc.CatalogServiceStub:
    return catalog_pb2_grpc.CatalogServiceStub(channel)


@pytest.fixture
def database_unreachable() -> Iterator[None]:
    settings = connection.settings_dict
    host, port = settings["HOST"], settings["PORT"]
    connection.close()
    settings["HOST"], settings["PORT"] = "127.0.0.1", "1"
    try:
        yield
    finally:
        connection.close()
        settings["HOST"], settings["PORT"] = host, port


@pytest.mark.django_db(transaction=True)
class TestTheDatabaseCannotBeReached:
    @pytest.mark.parametrize(
        "rpc",
        [
            pytest.param(_get_product, id="GetProduct"),
            pytest.param(_changed_since_a_transaction, id="ChangedSince-transaction-cursor"),
            pytest.param(_changed_since_a_time, id="ChangedSince-time-cursor"),
            pytest.param(_count_products, id="CountProducts"),
        ],
    )
    def test_every_rpc_is_unavailable_not_unknown(
        self,
        rpc: Callable[[catalog_pb2_grpc.CatalogServiceStub], object],
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        database_unreachable: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        code, details = _status_of(lambda: rpc(catalog))

        assert code == grpc.StatusCode.UNAVAILABLE
        assert details == DATABASE_UNAVAILABLE_DETAILS
        assert "127.0.0.1" in caplog.text, "the cause is logged where an operator can read it"

    def test_the_outage_is_logged_under_the_callers_request_id(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        database_unreachable: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.handler.addFilter(RequestIdLogFilter())

        code, _ = _status_of(
            lambda: catalog.CountProducts(
                catalog_pb2.CountProductsRequest(),
                metadata=[(REQUEST_ID_HEADER, "kinetix-trace-outage-1")],
                timeout=TIMEOUT_SECONDS,
            )
        )

        assert code == grpc.StatusCode.UNAVAILABLE
        outages = [record for record in caplog.records if "could not reach the database" in record.getMessage()]
        assert [getattr(record, "request_id", None) for record in outages] == ["kinetix-trace-outage-1"]

    def test_an_empty_sku_is_still_refused_as_a_bad_argument(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        database_unreachable: None,
    ) -> None:
        code, details = _status_of(
            lambda: catalog.GetProduct(catalog_pb2.GetProductRequest(sku=""), timeout=TIMEOUT_SECONDS)
        )

        assert code == grpc.StatusCode.INVALID_ARGUMENT
        assert details == "sku is required"

    def test_a_caller_off_the_allow_list_is_still_refused_as_one(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        database_unreachable: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(PeerAuthorizationInterceptor, "peer_of", _peer_named("review"))

        code, _ = _status_of(lambda: _count_products(catalog))

        assert code == grpc.StatusCode.PERMISSION_DENIED

    def test_the_health_probe_still_answers(self, channel: grpc.Channel, database_unreachable: None) -> None:
        check = channel.unary_unary(
            "/grpc.health.v1.Health/Check",
            request_serializer=health_pb2.HealthCheckRequest.SerializeToString,
            response_deserializer=health_pb2.HealthCheckResponse.FromString,
        )

        response = check(health_pb2.HealthCheckRequest(), timeout=TIMEOUT_SECONDS)

        assert response.status == health_pb2.HealthCheckResponse.SERVING


@pytest.mark.django_db(transaction=True)
class TestAnErrorTheDatabaseAnswered:
    def test_is_internal_and_its_text_stays_in_the_log(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _listed("SHOE-1")
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE products RENAME COLUMN title TO title_drifted")

        try:
            code, details = _status_of(lambda: _get_product(catalog))
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE products RENAME COLUMN title_drifted TO title")

        assert code == grpc.StatusCode.INTERNAL
        assert details == INTERNAL_ERROR_DETAILS
        assert "products.title does not exist" in caplog.text, "the cause is logged where an operator can read it"

    def test_a_cursor_postgres_cannot_hold_is_a_bad_argument(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
    ) -> None:
        request = _transaction_cursor()
        request.cursor.last_sku = "SHOE\x00-1"

        code, details = _status_of(lambda: catalog.ChangedSince(request, timeout=TIMEOUT_SECONDS))

        assert code == grpc.StatusCode.INVALID_ARGUMENT
        assert details == "cursor.last_sku must not contain a NUL character"


@pytest.mark.django_db(transaction=True)
class TestTheDatabaseIsBack:
    def test_a_listed_product_is_found(self, catalog: catalog_pb2_grpc.CatalogServiceStub) -> None:
        _listed("SHOE-1")

        response = _get_product(catalog)

        assert isinstance(response, catalog_pb2.GetProductResponse)
        assert response.found is True
        assert response.product.sku == "SHOE-1"

    def test_an_unknown_product_is_found_false_not_an_error(
        self,
        catalog: catalog_pb2_grpc.CatalogServiceStub,
    ) -> None:
        response = catalog.GetProduct(catalog_pb2.GetProductRequest(sku="NOPE"), timeout=TIMEOUT_SECONDS)

        assert response.found is False

    def test_a_sku_postgres_cannot_hold_is_found_false(self, catalog: catalog_pb2_grpc.CatalogServiceStub) -> None:
        response = catalog.GetProduct(catalog_pb2.GetProductRequest(sku="SHOE\x00-1"), timeout=TIMEOUT_SECONDS)

        assert response.found is False

    def test_the_count_is_read(self, catalog: catalog_pb2_grpc.CatalogServiceStub) -> None:
        _listed("SHOE-1")

        response = catalog.CountProducts(catalog_pb2.CountProductsRequest(), timeout=TIMEOUT_SECONDS)

        assert response.total == 1
