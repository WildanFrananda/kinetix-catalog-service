from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator, Optional, Tuple

import grpc
from django.db import close_old_connections

Behavior = Callable[[object, grpc.ServicerContext], object]
StreamBehavior = Callable[[object, grpc.ServicerContext], Iterator[object]]
Handler = grpc.RpcMethodHandler

_OPEN_METHODS: Tuple[str, ...] = (
    "/grpc.health.v1.Health/",
    "/grpc.reflection.",
)

if TYPE_CHECKING:
    _Intercepted = grpc.ServerInterceptor[object, object]
else:
    _Intercepted = grpc.ServerInterceptor


class DatabaseConnectionInterceptor(_Intercepted):
    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Optional[Handler[object, object]]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Optional[Handler[object, object]]:
        method: str = getattr(handler_call_details, "method", "") or ""

        if method.startswith(_OPEN_METHODS):
            return continuation(handler_call_details)

        handler = continuation(handler_call_details)

        if handler is None:
            return None

        if handler.unary_unary is not None:
            return grpc.unary_unary_rpc_method_handler(
                self._around(handler.unary_unary),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            return grpc.unary_stream_rpc_method_handler(
                self._around_stream(handler.unary_stream),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler

    def _around(self, behavior: Behavior) -> Behavior:
        def call(request: object, context: grpc.ServicerContext) -> object:
            close_old_connections()
            try:
                return behavior(request, context)
            finally:
                close_old_connections()

        return call

    def _around_stream(self, behavior: StreamBehavior) -> StreamBehavior:
        def call(request: object, context: grpc.ServicerContext) -> Iterator[object]:
            close_old_connections()
            try:
                yield from behavior(request, context)
            finally:
                close_old_connections()

        return call
