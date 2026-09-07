import grpc

_PEER_FAULT_CODES: frozenset[object] = frozenset(
    {
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        grpc.StatusCode.RESOURCE_EXHAUSTED,
        grpc.StatusCode.INTERNAL,
        grpc.StatusCode.UNKNOWN,
        grpc.StatusCode.DATA_LOSS,
    }
)


def is_peer_fault(error: BaseException) -> bool:
    if not isinstance(error, grpc.RpcError):
        return False

    read_code = getattr(error, "code", None)
    if not callable(read_code):
        return True

    return read_code() in _PEER_FAULT_CODES
