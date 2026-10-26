from __future__ import annotations

from typing import Callable, Iterator, Optional, TypeVar

import grpc

from core.infrastructure.observability import (
    REQUEST_ID_HEADER,
    accepted_request_id,
    reset_request_id,
    set_request_id,
)

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

Behavior = Callable[[RequestT, grpc.ServicerContext], ResponseT]
StreamBehavior = Callable[[RequestT, grpc.ServicerContext], Iterator[ResponseT]]
Handler = grpc.RpcMethodHandler


class RequestIdInterceptor(grpc.ServerInterceptor):
    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Optional[Handler[RequestT, ResponseT]]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Optional[Handler[RequestT, ResponseT]]:
        handler = continuation(handler_call_details)

        if handler is None:
            return None

        request_id = accepted_request_id(_request_id_of(handler_call_details))

        if handler.unary_unary is not None:
            return grpc.unary_unary_rpc_method_handler(
                self._adopted(handler.unary_unary, request_id),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            return grpc.unary_stream_rpc_method_handler(
                self._adopted_stream(handler.unary_stream, request_id),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler

    def _adopted(
        self, behavior: Behavior[RequestT, ResponseT], request_id: Optional[str]
    ) -> Behavior[RequestT, ResponseT]:
        def call(request: RequestT, context: grpc.ServicerContext) -> ResponseT:
            token = set_request_id(request_id)
            try:
                return behavior(request, context)
            finally:
                reset_request_id(token)

        return call

    def _adopted_stream(
        self, behavior: StreamBehavior[RequestT, ResponseT], request_id: Optional[str]
    ) -> StreamBehavior[RequestT, ResponseT]:
        def call(request: RequestT, context: grpc.ServicerContext) -> Iterator[ResponseT]:
            token = set_request_id(request_id)
            try:
                responses = iter(behavior(request, context))
            finally:
                reset_request_id(token)

            while True:
                token = set_request_id(request_id)
                try:
                    response = next(responses)
                except StopIteration:
                    return
                finally:
                    reset_request_id(token)

                yield response

        return call


def _request_id_of(handler_call_details: grpc.HandlerCallDetails) -> Optional[str]:
    for key, value in handler_call_details.invocation_metadata or ():
        if key == REQUEST_ID_HEADER:
            return value if isinstance(value, str) else None

    return None
