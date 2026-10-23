from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator, Optional

import grpc

from core.infrastructure.observability import (
    REQUEST_ID_HEADER,
    accepted_request_id,
    reset_request_id,
    set_request_id,
)

Behavior = Callable[[object, grpc.ServicerContext], object]
StreamBehavior = Callable[[object, grpc.ServicerContext], Iterator[object]]
Handler = grpc.RpcMethodHandler

_END = object()

if TYPE_CHECKING:
    _Intercepted = grpc.ServerInterceptor[object, object]
else:
    _Intercepted = grpc.ServerInterceptor


class RequestIdInterceptor(_Intercepted):
    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Optional[Handler[object, object]]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Optional[Handler[object, object]]:
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

    def _adopted(self, behavior: Behavior, request_id: Optional[str]) -> Behavior:
        def call(request: object, context: grpc.ServicerContext) -> object:
            token = set_request_id(request_id)
            try:
                return behavior(request, context)
            finally:
                reset_request_id(token)

        return call

    def _adopted_stream(self, behavior: StreamBehavior, request_id: Optional[str]) -> StreamBehavior:
        def call(request: object, context: grpc.ServicerContext) -> Iterator[object]:
            token = set_request_id(request_id)
            try:
                responses = iter(behavior(request, context))
            finally:
                reset_request_id(token)

            while True:
                token = set_request_id(request_id)
                try:
                    response = next(responses, _END)
                finally:
                    reset_request_id(token)

                if response is _END:
                    return

                yield response

        return call


def _request_id_of(handler_call_details: grpc.HandlerCallDetails) -> Optional[str]:
    for key, value in handler_call_details.invocation_metadata or ():
        if key == REQUEST_ID_HEADER:
            return value if isinstance(value, str) else None

    return None
