from __future__ import annotations

from typing import Callable, Iterator, Optional, Tuple, TypeVar

import grpc
from django.db import close_old_connections

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

Behavior = Callable[[RequestT, grpc.ServicerContext], ResponseT]
StreamBehavior = Callable[[RequestT, grpc.ServicerContext], Iterator[ResponseT]]
Handler = grpc.RpcMethodHandler

_OPEN_METHODS: Tuple[str, ...] = (
    "/grpc.health.v1.Health/",
    "/grpc.reflection.",
)


class DatabaseConnectionInterceptor(grpc.ServerInterceptor):
    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Optional[Handler[RequestT, ResponseT]]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Optional[Handler[RequestT, ResponseT]]:
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

    def _around(
        self, behavior: Behavior[RequestT, ResponseT]
    ) -> Behavior[RequestT, ResponseT]:
        def call(request: RequestT, context: grpc.ServicerContext) -> ResponseT:
            close_old_connections()
            try:
                return behavior(request, context)
            finally:
                close_old_connections()

        return call

    def _around_stream(
        self, behavior: StreamBehavior[RequestT, ResponseT]
    ) -> StreamBehavior[RequestT, ResponseT]:
        def call(request: RequestT, context: grpc.ServicerContext) -> Iterator[ResponseT]:
            close_old_connections()
            try:
                yield from behavior(request, context)
            finally:
                close_old_connections()

        return call
