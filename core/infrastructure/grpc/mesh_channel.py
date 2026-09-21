from typing import Optional, Sequence, Tuple

import grpc

from core.infrastructure.security.mtls import channel_credentials

_MAX_RECONNECT_BACKOFF_MS = 5_000
_INITIAL_RECONNECT_BACKOFF_MS = 500

_DNS_MIN_TIME_BETWEEN_RESOLUTIONS_MS = 2_000

_KEEPALIVE_TIME_MS = 30_000
_KEEPALIVE_TIMEOUT_MS = 10_000


def mesh_channel_options() -> Sequence[Tuple[str, int]]:
    return (
        ("grpc.initial_reconnect_backoff_ms", _INITIAL_RECONNECT_BACKOFF_MS),
        ("grpc.max_reconnect_backoff_ms", _MAX_RECONNECT_BACKOFF_MS),
        ("grpc.dns_min_time_between_resolutions_ms", _DNS_MIN_TIME_BETWEEN_RESOLUTIONS_MS),
        ("grpc.keepalive_time_ms", _KEEPALIVE_TIME_MS),
        ("grpc.keepalive_timeout_ms", _KEEPALIVE_TIMEOUT_MS),
        ("grpc.keepalive_permit_without_calls", 1),
    )


def mesh_channel(target: str, directory: Optional[str] = None) -> grpc.Channel:
    """A secure channel to another service in this mesh."""
    return grpc.secure_channel(
        target,
        channel_credentials(directory),
        options=list(mesh_channel_options()),
    )
