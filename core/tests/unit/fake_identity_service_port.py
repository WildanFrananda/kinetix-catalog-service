from typing import Any, Dict, Optional

from core.domain.errors import IdentityUnavailableError
from core.domain.repositories import IdentityServicePort

class FakeIdentityServicePort(IdentityServicePort):
    def __init__(
        self,
        status: Optional[str] = "verified",
        unavailable: bool = False,
        may_sell: bool = True,
        merchant_principal_id: Optional[str] = None,
    ) -> None:
        self._status = status
        self._unavailable = unavailable
        self._may_sell = may_sell
        self._merchant_principal_id = merchant_principal_id

    def get_merchant_info(self, merchant_principal_id: str) -> Optional[Dict[str, Any]]:
        if self._unavailable:
            raise IdentityUnavailableError(
                merchant_principal_id, "circuit 'identity-merchant' is open"
            )

        if self._status is None:
            return None

        return {
            "merchant_principal_id": self._merchant_principal_id or merchant_principal_id,
            "store_name": "Fake Store",
            "status": self._status,
            "may_sell": self._may_sell,
        }
