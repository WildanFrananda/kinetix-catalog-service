from types import SimpleNamespace
from typing import Iterator, List, Optional, Tuple, cast

import grpc
import pytest

from core.infrastructure.grpc.request_id_interceptor import RequestIdInterceptor
from core.infrastructure.observability import REQUEST_ID_HEADER, current_request_id

WATCH = "/grpc.health.v1.Health/Watch"
CONTEXT = cast(grpc.ServicerContext, object())


def _details(metadata: Tuple[Tuple[str, str], ...]) -> grpc.HandlerCallDetails:
    return cast(grpc.HandlerCallDetails, SimpleNamespace(method=WATCH, invocation_metadata=metadata))


def _intercepted(
    handler: grpc.RpcMethodHandler[object, object],
    metadata: Tuple[Tuple[str, str], ...],
) -> grpc.RpcMethodHandler[object, object]:
    intercepted = RequestIdInterceptor().intercept_service(lambda _: handler, _details(metadata))
    assert intercepted is not None

    return intercepted


class TestAStream:
    def test_each_step_runs_under_the_id_and_the_caller_never_sees_it(self) -> None:
        inside: List[Optional[str]] = []
        between: List[Optional[str]] = []

        def behaviour(request: object, context: grpc.ServicerContext) -> Iterator[object]:
            inside.append(current_request_id())
            yield "first"
            inside.append(current_request_id())
            yield "second"
            inside.append(current_request_id())

        handler = _intercepted(grpc.unary_stream_rpc_method_handler(behaviour), ((REQUEST_ID_HEADER, "req-stream"),))
        assert handler.unary_stream is not None

        for _ in handler.unary_stream(object(), CONTEXT):
            between.append(current_request_id())

        assert inside == ["req-stream", "req-stream", "req-stream"]
        assert between == [None, None]
        assert current_request_id() is None

    def test_a_stream_that_fails_midway_leaves_no_id_behind(self) -> None:
        def behaviour(request: object, context: grpc.ServicerContext) -> Iterator[object]:
            yield "first"
            raise RuntimeError("the stream broke")

        handler = _intercepted(grpc.unary_stream_rpc_method_handler(behaviour), ((REQUEST_ID_HEADER, "req-broken"),))
        assert handler.unary_stream is not None

        with pytest.raises(RuntimeError):
            list(handler.unary_stream(object(), CONTEXT))

        assert current_request_id() is None


class TestAUnaryCall:
    def test_a_call_that_raises_leaves_no_id_behind(self) -> None:
        def behaviour(request: object, context: grpc.ServicerContext) -> object:
            assert current_request_id() == "req-raised"
            raise RuntimeError("the call broke")

        handler = _intercepted(grpc.unary_unary_rpc_method_handler(behaviour), ((REQUEST_ID_HEADER, "req-raised"),))
        assert handler.unary_unary is not None

        with pytest.raises(RuntimeError):
            handler.unary_unary(object(), CONTEXT)

        assert current_request_id() is None

    def test_only_the_request_id_key_is_read(self) -> None:
        seen: List[Optional[str]] = []

        def behaviour(request: object, context: grpc.ServicerContext) -> object:
            seen.append(current_request_id())
            return "answered"

        metadata = (("x-correlation-id", "not-ours"), ("user-agent", "grpc-go/1.75"))
        handler = _intercepted(grpc.unary_unary_rpc_method_handler(behaviour), metadata)
        assert handler.unary_unary is not None

        assert handler.unary_unary(object(), CONTEXT) == "answered"
        assert seen == [None]

    def test_an_unknown_method_is_left_unknown(self) -> None:
        assert RequestIdInterceptor().intercept_service(lambda _: None, _details(())) is None
