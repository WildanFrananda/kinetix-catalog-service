from __future__ import annotations

from typing import Iterator, List, Optional, Tuple, cast

import grpc
import psycopg
import pytest
from django.db import InterfaceError, OperationalError
from psycopg import errors as pg_errors

from core.domain.errors import InvalidInputError
from core.infrastructure.grpc.error_status_interceptor import (
    DATABASE_UNAVAILABLE_DETAILS,
    INTERNAL_ERROR_DETAILS,
    ErrorStatusInterceptor,
)

METHOD = "/catalog.v1.CatalogService/GetProduct"
CAUSE = 'connection to server at "10.0.0.7", port 5432 failed: Connection refused'


class FakeContext:
    def __init__(self) -> None:
        self.status: Optional[Tuple[grpc.StatusCode, str]] = None

    def abort(self, code: grpc.StatusCode, details: str) -> None:
        self.status = (code, details)
        raise grpc.RpcError(details)


class FakeCallDetails:
    def __init__(self, method: str) -> None:
        self.method = method
        self.invocation_metadata: List[object] = []


def _caused_by(wrapper: Exception, cause: Exception) -> Exception:
    wrapper.__cause__ = cause

    return wrapper


def _raising(error: Exception) -> grpc.RpcMethodHandler[object, object]:
    def behaviour(request: object, context: grpc.ServicerContext) -> object:
        raise error

    return grpc.unary_unary_rpc_method_handler(behaviour)


def _intercepted(
    handler: grpc.RpcMethodHandler[object, object],
    method: str = METHOD,
) -> Optional[grpc.RpcMethodHandler[object, object]]:
    return ErrorStatusInterceptor().intercept_service(
        lambda _: handler,
        cast(grpc.HandlerCallDetails, FakeCallDetails(method)),
    )


def _status_after(error: Exception) -> Tuple[grpc.StatusCode, str]:
    handler = _intercepted(_raising(error))
    assert handler is not None and handler.unary_unary is not None
    context = FakeContext()

    with pytest.raises(grpc.RpcError):
        handler.unary_unary(object(), cast(grpc.ServicerContext, context))

    assert context.status is not None

    return context.status


class TestADatabaseThatCannotBeReached:
    def test_a_refused_connection_is_unavailable_and_its_text_is_not_sent(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        error = _caused_by(OperationalError(CAUSE), psycopg.OperationalError(CAUSE))

        assert _status_after(error) == (grpc.StatusCode.UNAVAILABLE, DATABASE_UNAVAILABLE_DETAILS)
        assert "10.0.0.7" in caplog.text, "the cause goes to the log"

    def test_a_closed_connection_is_unavailable(self) -> None:
        status = _status_after(InterfaceError("connection already closed"))

        assert status == (grpc.StatusCode.UNAVAILABLE, DATABASE_UNAVAILABLE_DETAILS)

    def test_a_stream_that_loses_the_database_midway_ends_unavailable(self) -> None:
        def behaviour(request: object, context: grpc.ServicerContext) -> Iterator[object]:
            yield "first"
            raise InterfaceError("connection already closed")

        handler = _intercepted(grpc.unary_stream_rpc_method_handler(behaviour))
        assert handler is not None and handler.unary_stream is not None
        context = FakeContext()
        sent: List[object] = []

        with pytest.raises(grpc.RpcError):
            for item in handler.unary_stream(object(), cast(grpc.ServicerContext, context)):
                sent.append(item)

        assert sent == ["first"]
        assert context.status == (grpc.StatusCode.UNAVAILABLE, DATABASE_UNAVAILABLE_DETAILS)


class TestEverythingElse:
    def test_an_error_the_database_answered_with_is_internal(self) -> None:
        timeout = pg_errors.QueryCanceled("canceling statement due to statement timeout")
        error = _caused_by(OperationalError(str(timeout)), timeout)

        assert _status_after(error) == (grpc.StatusCode.INTERNAL, INTERNAL_ERROR_DETAILS)

    def test_an_unexpected_exception_is_internal_and_its_text_stays_in_the_log(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        status = _status_after(KeyError("products.category_id"))

        assert status == (grpc.StatusCode.INTERNAL, INTERNAL_ERROR_DETAILS)
        assert "products.category_id" in caplog.text
        assert "Traceback" in caplog.text, "an unexpected failure is logged with its stack"

    def test_a_bad_argument_is_refused_as_one(self) -> None:
        status = _status_after(InvalidInputError("cursor.last_sku", "must not contain a NUL character"))

        assert status == (grpc.StatusCode.INVALID_ARGUMENT, "cursor.last_sku must not contain a NUL character")

    def test_an_answer_goes_through_untouched(self) -> None:
        def behaviour(request: object, context: grpc.ServicerContext) -> object:
            return "answered"

        handler = _intercepted(grpc.unary_unary_rpc_method_handler(behaviour))
        assert handler is not None and handler.unary_unary is not None

        assert handler.unary_unary(object(), cast(grpc.ServicerContext, FakeContext())) == "answered"

    @pytest.mark.parametrize(
        "method",
        [
            "/grpc.health.v1.Health/Check",
            "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
        ],
    )
    def test_the_probe_and_reflection_are_left_to_grpc(self, method: str) -> None:
        handler = _raising(RuntimeError("not catalog's code"))

        assert _intercepted(handler, method) is handler
