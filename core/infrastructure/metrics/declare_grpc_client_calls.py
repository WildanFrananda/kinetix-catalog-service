from typing import Sequence

import grpc
from google.protobuf.descriptor import ServiceDescriptor

from core.infrastructure.metrics.contract_metrics import GRPC_CLIENT_CALLS_TOTAL

OK_CODE = grpc.StatusCode.OK.name


def declare_grpc_client_calls(
    peer: str, service: ServiceDescriptor, method_names: Sequence[str]
) -> None:
    for method_name in method_names:
        method = service.methods_by_name[method_name]
        GRPC_CLIENT_CALLS_TOTAL.labels(
            peer=peer,
            grpc_method=f"/{service.full_name}/{method.name}",
            grpc_code=OK_CODE,
        )
