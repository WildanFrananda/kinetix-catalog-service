import logging
from typing import Any, Dict, Optional

import grpc
from identity.v1 import identity_pb2, identity_pb2_grpc

from core.domain.repositories.identity_service_port import IdentityServicePort
from core.infrastructure.grpc.required_env import required_env
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
    """
    Asks identity about a merchant, over the mesh.

    This class used to answer by itself. It returned
    `{"user_id": n, "store_name": f"Merchant Store #{n}", "status": "active"}` for any positive
    integer and never opened a connection, so `create_product`'s check that a merchant is
    verified passed for every caller — including a suspended one, and including an account
    identity had never heard of. It read as a working authorization check in every log and test.
    """

    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host: str = target_host or required_env("IDENTITY_GRPC_URL")
        self._channel = grpc.secure_channel(self._target_host, channel_credentials())
        self._stub = identity_pb2_grpc.IdentityServiceStub(self._channel)

    def get_merchant_info(self, merchant_principal_id: str) -> Optional[Dict[str, Any]]:
        if not merchant_principal_id:
            return None

        try:
            response = self._stub.GetMerchantInfo(
                identity_pb2.GetMerchantInfoRequest(principal_id=merchant_principal_id),
                timeout=5,
                metadata=request_id_metadata(),
            )
        except grpc.RpcError as error:
            logger.error(
                "identity did not answer for merchant %s (%s); treating the merchant as unverified",
                merchant_principal_id,
                error.code(),
            )
            return None

        if not response.found:
            return None

        return {
            "merchant_principal_id": response.merchant_principal_id,
            "store_name": response.store_name,
            "status": _STATUS_NAMES.get(response.status, "unspecified"),
        }
