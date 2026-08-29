from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class IdentityServicePort(ABC):
    @abstractmethod
    def get_merchant_info(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        pass
