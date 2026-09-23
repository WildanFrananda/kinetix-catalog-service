from __future__ import annotations

from typing import List, cast

import grpc
import pytest

from core.infrastructure.grpc import database_connection_interceptor as module
from core.infrastructure.grpc.database_connection_interceptor import (
    DatabaseConnectionInterceptor,
)


class FakeCallDetails:
    def __init__(self, method: str) -> None:
        self.method = method
        self.invocation_metadata: List[object] = []


def details(method: str) -> grpc.HandlerCallDetails:
    return cast(grpc.HandlerCallDetails, FakeCallDetails(method))


def handler_for(events: List[str]) -> grpc.RpcMethodHandler[object, object]:
    def behaviour(request: object, context: grpc.ServicerContext) -> str:
        events.append("served")
        return "answered"

    return grpc.unary_unary_rpc_method_handler(behaviour)


def failing_handler(events: List[str]) -> grpc.RpcMethodHandler[object, object]:
    def behaviour(request: object, context: grpc.ServicerContext) -> str:
        events.append("served")
        raise RuntimeError("the database went away mid-call")

    return grpc.unary_unary_rpc_method_handler(behaviour)


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    recorded: List[str] = []

    def spy() -> None:
        recorded.append("closed old connections")

    monkeypatch.setattr(module, "close_old_connections", spy)

    return recorded


def served_by(handler: grpc.RpcMethodHandler[object, object]) -> None:
    behaviour = handler.unary_unary
    assert behaviour is not None
    behaviour(object(), cast(grpc.ServicerContext, object()))


class TestDatabaseConnectionInterceptor:
    def test_a_call_starts_and_ends_on_a_fresh_connection(self, events: List[str]) -> None:
        handler = DatabaseConnectionInterceptor().intercept_service(
            lambda _: handler_for(events),
            details("/catalog.v1.CatalogService/ChangedSince"),
        )

        assert handler is not None
        served_by(handler)

        assert events == ["closed old connections", "served", "closed old connections"]

    def test_a_failing_call_still_releases_its_connection(self, events: List[str]) -> None:
        handler = DatabaseConnectionInterceptor().intercept_service(
            lambda _: failing_handler(events),
            details("/catalog.v1.CatalogService/ChangedSince"),
        )

        assert handler is not None
        with pytest.raises(RuntimeError):
            served_by(handler)

        assert events[-1] == "closed old connections", (
            "a call that raised must not leave a connection behind to go stale"
        )

    def test_the_health_probe_opens_no_connection(self, events: List[str]) -> None:
        handler = DatabaseConnectionInterceptor().intercept_service(
            lambda _: handler_for(events),
            details("/grpc.health.v1.Health/Check"),
        )

        assert handler is not None
        served_by(handler)

        assert events == ["served"], "the container's own probe touches no database"
