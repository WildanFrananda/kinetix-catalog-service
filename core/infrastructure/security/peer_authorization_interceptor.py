from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Callable, FrozenSet, Iterator, Optional, Sequence, Tuple

import grpc

logger = logging.getLogger(__name__)

_SPIFFE_PREFIX = "spiffe://"
_DEFAULT_TRUST_DOMAIN = "kinetix.local"
_SERVICE_SEGMENT = "/service/"
_SAN_KEY = "x509_subject_alternative_name"
_OPEN_METHODS: Tuple[str, ...] = (
    "/grpc.health.v1.Health/",
    "/grpc.reflection.",
)

Behavior = Callable[[object, grpc.ServicerContext], object]
StreamBehavior = Callable[[object, grpc.ServicerContext], Iterator[object]]
Handler = grpc.RpcMethodHandler


def trust_domains() -> Tuple[str, ...]:
    configured = tuple(
        value.strip()
        for value in os.environ.get("KINETIX_TRUST_DOMAIN", "").split(",")
        if value.strip()
    )

    return configured or (_DEFAULT_TRUST_DOMAIN,)


def service_of(
    sans: Sequence[object], domains: Optional[Sequence[str]] = None
) -> Optional[str]:
    accepted = tuple(domains) if domains is not None else trust_domains()
    prefixes = tuple(
        f"{_SPIFFE_PREFIX}{domain}{_SERVICE_SEGMENT}" for domain in accepted
    )

    for san in sans:
        text = san.decode() if isinstance(san, bytes) else str(san)

        for prefix in prefixes:
            if not text.startswith(prefix):
                continue

            name = text[len(prefix) :]

            if name and "/" not in name:
                return name

    return None


if TYPE_CHECKING:
    _Intercepted = grpc.ServerInterceptor[object, object]
else:
    _Intercepted = grpc.ServerInterceptor


class PeerAuthorizationInterceptor(_Intercepted):
    def __init__(self, allowed: FrozenSet[str]) -> None:
        self._allowed = allowed

    def intercept_service(
        self,
        continuation: Callable[
            [grpc.HandlerCallDetails], Optional[Handler[object, object]]
        ],
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
                self._guarded(handler.unary_unary, method),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            return grpc.unary_stream_rpc_method_handler(
                self._guarded_stream(handler.unary_stream, method),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler

    def peer_of(self, context: grpc.ServicerContext) -> Optional[str]:
        auth = context.auth_context()
        return service_of(auth.get(_SAN_KEY, []))

    def _guarded_stream(self, behavior: StreamBehavior, method: str) -> StreamBehavior:
        def guard(request: object, context: grpc.ServicerContext) -> Iterator[object]:
            self._refuse_unless_allowed(context, method)

            return behavior(request, context)

        return guard

    def _guarded(self, behavior: Behavior, method: str) -> Behavior:
        def guard(request: object, context: grpc.ServicerContext) -> object:
            self._refuse_unless_allowed(context, method)

            return behavior(request, context)

        return guard

    def _refuse_unless_allowed(self, context: grpc.ServicerContext, method: str) -> None:
        peer = self.peer_of(context)

        if peer is not None and peer in self._allowed:
            return

        logger.warning(
            "refused a gRPC call to %s from peer %s; allowed: %s",
            method,
            peer or "<unnamed>",
            ",".join(sorted(self._allowed)),
        )
        context.abort(
            grpc.StatusCode.PERMISSION_DENIED,
            "this caller is not on catalog's gRPC allow list",
        )
