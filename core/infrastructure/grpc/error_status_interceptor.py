from __future__ import annotations

import logging
from typing import Callable, Iterator, NoReturn, Optional, Tuple, TypeVar

import grpc

from core.domain.errors import InvalidInputError
from core.infrastructure.resilience import is_database_unavailable

logger = logging.getLogger(__name__)

DATABASE_UNAVAILABLE_DETAILS = (
    "catalog could not reach its database, so this call was not answered; try again shortly"
)
INTERNAL_ERROR_DETAILS = "catalog failed while answering this call"

_OPEN_METHODS: Tuple[str, ...] = (
    "/grpc.health.v1.Health/",
    "/grpc.reflection.",
)

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

Behavior = Callable[[RequestT, grpc.ServicerContext], ResponseT]
StreamBehavior = Callable[[RequestT, grpc.ServicerContext], Iterator[ResponseT]]
Handler = grpc.RpcMethodHandler


class ErrorStatusInterceptor(grpc.ServerInterceptor):
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
                self._answered(handler.unary_unary, method),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            return grpc.unary_stream_rpc_method_handler(
                self._answered_stream(handler.unary_stream, method),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler

    def _answered(
        self, behavior: Behavior[RequestT, ResponseT], method: str
    ) -> Behavior[RequestT, ResponseT]:
        def call(request: RequestT, context: grpc.ServicerContext) -> ResponseT:
            try:
                return behavior(request, context)
            except Exception as error:
                _abort_for(error, method, context)

        return call

    def _answered_stream(
        self, behavior: StreamBehavior[RequestT, ResponseT], method: str
    ) -> StreamBehavior[RequestT, ResponseT]:
        def call(request: RequestT, context: grpc.ServicerContext) -> Iterator[ResponseT]:
            try:
                yield from behavior(request, context)
            except Exception as error:
                _abort_for(error, method, context)

        return call


def _abort_for(error: Exception, method: str, context: grpc.ServicerContext) -> NoReturn:
    if isinstance(error, InvalidInputError):
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"{error.field} {error.reason}")

    if is_database_unavailable(error):
        logger.error("%s could not reach the database: %s", method, error)
        context.abort(grpc.StatusCode.UNAVAILABLE, DATABASE_UNAVAILABLE_DETAILS)

    logger.exception("unhandled exception serving %s", method)
    context.abort(grpc.StatusCode.INTERNAL, INTERNAL_ERROR_DETAILS)
