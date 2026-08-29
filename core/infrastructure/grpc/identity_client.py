import os
from typing import Optional, Dict, Any
from core.domain.repositories.identity_service_port import IdentityServicePort

class IdentityGrpcClient(IdentityServicePort):
    def __init__(self, endpoint_url: Optional[str] = None) -> None:
        self.endpoint_url = endpoint_url or os.getenv("IDENTITY_GRPC_URL", "localhost:50052")

    def get_merchant_info(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        if merchant_id > 0:
            return {
                "user_id": merchant_id,
                "store_name": f"Merchant Store #{merchant_id}",
                "status": "active"
            }
        return None
