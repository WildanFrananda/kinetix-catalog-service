import logging
from typing import TYPE_CHECKING, Callable, TypeVar

import grpc

from core.infrastructure.metrics.contract_metrics import GRPC_CLIENT_CALLS_TOTAL

if TYPE_CHECKING:
    from grpc import _CallFuture

logger = logging.getLogger(__name__)

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class GrpcClientMetricsInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, peer: str) -> None:
        self._peer = peer

    def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.ClientCallDetails, RequestT], "_CallFuture[ResponseT]"],
        client_call_details: grpc.ClientCallDetails,
        request: RequestT,
    ) -> "_CallFuture[ResponseT]":
        call = continuation(client_call_details, request)
        self._record(client_call_details.method, call)
        return call

    def _record(self, method: str, call: grpc.Call) -> None:
        try:
            GRPC_CLIENT_CALLS_TOTAL.labels(
                peer=self._peer, grpc_method=method, grpc_code=call.code().name
            ).inc()
        except Exception as failure:
            logger.error(
                "could not record the outcome of %s to %s: %s", method, self._peer, failure
            )
