from typing import TYPE_CHECKING, Callable, Dict, Optional, cast

import grpc
from google.protobuf.message import Message
from prometheus_client import REGISTRY

from core.infrastructure.metrics import GrpcClientMetricsInterceptor

if TYPE_CHECKING:
    from grpc import _CallFuture

METHOD = "/fulfillment.v1.BinStockService/CheckBinStock"
PEER = "kinetix-warehouse-service"


class _CallDetails(grpc.ClientCallDetails):
    def __init__(self, method: str) -> None:
        self.method = method
        self.timeout = None
        self.metadata = None
        self.credentials = None
        self.wait_for_ready = None
        self.compression = None


class _FinishedCall:
    def __init__(self, code: grpc.StatusCode) -> None:
        self._code = code

    def code(self) -> grpc.StatusCode:
        return self._code


def _continuation_finishing_with(
    code: grpc.StatusCode,
) -> Callable[[grpc.ClientCallDetails, Message], "_CallFuture[Message]"]:
    def continuation(
        client_call_details: grpc.ClientCallDetails, request: Message
    ) -> "_CallFuture[Message]":
        return cast("_CallFuture[Message]", _FinishedCall(code))

    return continuation


def _calls_counted(code: str) -> float:
    labels: Dict[str, str] = {"peer": PEER, "grpc_method": METHOD, "grpc_code": code}
    counted: Optional[float] = REGISTRY.get_sample_value(
        "kinetix_grpc_client_calls_total", labels
    )
    return counted or 0.0


class TestGrpcClientMetricsInterceptor:
    def test_a_call_that_succeeded_is_counted_as_OK(self) -> None:
        interceptor = GrpcClientMetricsInterceptor(PEER)
        before = _calls_counted("OK")

        interceptor.intercept_unary_unary(
            _continuation_finishing_with(grpc.StatusCode.OK),
            _CallDetails(METHOD),
            cast(Message, object()),
        )

        assert _calls_counted("OK") == before + 1

    def test_a_call_the_peer_refused_is_counted_under_its_own_code(self) -> None:
        interceptor = GrpcClientMetricsInterceptor(PEER)
        before = _calls_counted("UNAVAILABLE")

        interceptor.intercept_unary_unary(
            _continuation_finishing_with(grpc.StatusCode.UNAVAILABLE),
            _CallDetails(METHOD),
            cast(Message, object()),
        )

        assert _calls_counted("UNAVAILABLE") == before + 1

    def test_the_call_object_is_handed_back_untouched(self) -> None:
        interceptor = GrpcClientMetricsInterceptor(PEER)
        continuation = _continuation_finishing_with(grpc.StatusCode.OK)
        details = _CallDetails(METHOD)
        request = cast(Message, object())

        returned = interceptor.intercept_unary_unary(continuation, details, request)

        assert returned.code() is grpc.StatusCode.OK

    def test_the_method_label_comes_from_grpc_rather_than_from_this_service(self) -> None:
        interceptor = GrpcClientMetricsInterceptor(PEER)
        renamed = "/fulfillment.v1.BinStockService/CheckBinStockV2"

        interceptor.intercept_unary_unary(
            _continuation_finishing_with(grpc.StatusCode.OK),
            _CallDetails(renamed),
            cast(Message, object()),
        )

        counted = REGISTRY.get_sample_value(
            "kinetix_grpc_client_calls_total",
            {"peer": PEER, "grpc_method": renamed, "grpc_code": "OK"},
        )
        assert counted == 1
