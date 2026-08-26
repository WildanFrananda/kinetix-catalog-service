from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class PricingServicePort(ABC):
    @abstractmethod
    def calculate_price(
        self,
        items: List[Dict[str, Any]],
        voucher_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delegates pricing, discount, flash sale, and voucher calculations
        to kinetix-pricing-service.
        """
        pass
