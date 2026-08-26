from decimal import Decimal
from typing import List, Optional, Dict, Any
from core.domain.repositories import PricingServicePort


class FakePricingServicePort(PricingServicePort):
    def __init__(self, discount_rate: Decimal = Decimal("0.0")) -> None:
        self.discount_rate = discount_rate

    def calculate_price(
        self,
        items: List[Dict[str, Any]],
        voucher_code: Optional[str] = None
    ) -> Dict[str, Any]:
        subtotal = Decimal("0")
        item_responses = []

        for it in items:
            base_p = Decimal(str(it.get("base_price", "0")))
            qty = int(it.get("quantity", 1))
            unit_p = base_p * (Decimal("1.0") - self.discount_rate)
            line_t = unit_p * Decimal(qty)
            subtotal += line_t

            item_responses.append({
                "product_id": str(it.get("product_id", "")),
                "base_price": base_p,
                "final_unit_price": unit_p,
                "quantity": qty,
                "line_total": line_t,
                "applied_flash_sale": None,
                "applied_discount": "20% OFF" if self.discount_rate > 0 else None,
            })

        voucher_discount = Decimal("50000.00") if voucher_code == "SUPER50K" else Decimal("0.00")
        final_total = max(Decimal("0.00"), subtotal - voucher_discount)

        return {
            "success": True,
            "subtotal": subtotal,
            "total_discount": (subtotal * self.discount_rate) + voucher_discount,
            "voucher_discount": voucher_discount,
            "final_total": final_total,
            "applied_voucher": voucher_code if voucher_code == "SUPER50K" else None,
            "items": item_responses,
        }
