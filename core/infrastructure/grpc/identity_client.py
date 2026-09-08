import logging
from typing import Any, Dict, Optional

import grpc
from identity.v1 import identity_pb2, identity_pb2_grpc

from core.domain.errors import IdentityUnavailableError
from core.domain.repositories.identity_service_port import IdentityServicePort
from core.infrastructure.grpc.required_env import required_env
from core.infrastructure.resilience import CircuitBreaker, CircuitOpenError
from core.infrastructure.security import channel_credentials
from core.infrastructure.observability import request_id_metadata


logger = logging.getLogger(__name__)

_STATUS_NAMES: Dict[int, str] = {
    identity_pb2.MERCHANT_STATUS_UNSPECIFIED: "unspecified",
    identity_pb2.MERCHANT_STATUS_PENDING: "pending",
    identity_pb2.MERCHANT_STATUS_VERIFIED: "verified",
    identity_pb2.MERCHANT_STATUS_SUSPENDED: "suspended",
    identity_pb2.MERCHANT_STATUS_CLOSED: "closed",
}


class IdentityGrpcClient(IdentityServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host: str = target_host or required_env("IDENTITY_GRPC_URL")
        self._channel = grpc.secure_channel(self._target_host, channel_credentials())
        self._stub = identity_pb2_grpc.IdentityServiceStub(self._channel)
        self._breaker = CircuitBreaker("identity-merchant")

    def get_merchant_info(self, merchant_principal_id: str) -> Optional[Dict[str, Any]]:
        if not merchant_principal_id:
            return None

        request = identity_pb2.GetMerchantInfoRequest(principal_id=merchant_principal_id)
        metadata = request_id_metadata()

        try:
            response = self._breaker.call(
                lambda: self._stub.GetMerchantInfo(request, timeout=5, metadata=metadata)
            )
        except CircuitOpenError as circuit_open:
            logger.debug(
                "identity is not being called right now, so merchant %s is neither verified nor "
                "unverified as far as this service knows",
                merchant_principal_id,
            )
            raise IdentityUnavailableError(
                merchant_principal_id, str(circuit_open)
            ) from circuit_open
        except grpc.RpcError as rpc_error:
            logger.error(
                "identity did not answer about merchant %s; the request is refused as unknown, "
                "not as unverified",
                merchant_principal_id,
            )
            raise IdentityUnavailableError(
                merchant_principal_id, f"gRPC GetMerchantInfo failed: {rpc_error.details()}"
            ) from rpc_error

        if not response.found:
            return None

        return {
            "merchant_principal_id": response.merchant_principal_id,
            "store_name": response.store_name,
            "status": _STATUS_NAMES.get(response.status, "unspecified"),
        }
