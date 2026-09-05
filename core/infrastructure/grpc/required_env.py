import os


def required_env(name: str) -> str:
    """Read a required environment variable, or fail loudly.

    Used for the gRPC targets. A default here is worse than useless: `BinStockGrpcClient`
    defaulted to ``localhost:50051`` while reading an environment variable nothing sets, so it
    dialled its own container for the life of the service and every call failed at the TLS
    handshake with ``WRONG_VERSION_NUMBER``. `PricingGrpcClient` had the same wrong name and
    survived only because its default happened to be the right address.

    A missing target is a deployment fault and should read as one.
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required and has no default.")
    return value
