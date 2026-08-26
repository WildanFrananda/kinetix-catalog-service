import uuid
from decimal import Decimal
from typing import Optional, List
from core.domain.entities import Order, OrderItem, Money, Address, ReservationResult
from core.domain.repositories import (
    OrderRepository,
    FulfillmentServicePort,
    BinStockServicePort,
    PricingServicePort,
)
from core.application.dto import CreateOrderInputDTO, CheckoutResultDTO, ReserveCartStockInputDTO


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        fulfillment_port: FulfillmentServicePort,
        bin_stock_port: Optional[BinStockServicePort] = None,
        pricing_port: Optional[PricingServicePort] = None,
    ) -> None:
        self._order_repo = order_repo
        self._fulfillment_port = fulfillment_port
        self._bin_stock_port = bin_stock_port
        self._pricing_port = pricing_port

    def checkout(self, dto: CreateOrderInputDTO) -> CheckoutResultDTO:
        if not dto.buyer_name.strip():
            raise ValueError("Buyer name cannot be blank")
        if not dto.street_address.strip():
            raise ValueError("Street address cannot be blank")
        if not dto.items:
            raise ValueError("Order must contain at least one item")

        if dto.idempotency_key:
            existing_order = self._order_repo.find_by_idempotency_key(dto.idempotency_key)
            if existing_order:
                return CheckoutResultDTO(
                    success=True,
                    order_id=existing_order.id,
                    order_number=existing_order.order_number,
                    status=existing_order.status,
                    total_amount=existing_order.total_amount.amount,
                    fulfillment_ref=str(existing_order.id or ""),
                    message="Duplicate request detected. Returning existing order details."
                )

        if self._bin_stock_port:
            for it in dto.items:
                res = self._bin_stock_port.reserve_stock(sku=it.sku, quantity=it.quantity)
                if not res.get("success", False) and not res.get("unavailable", False):
                    raise ValueError(f"Insufficient stock for SKU '{it.sku}'. Reservation failed.")

        shipping_addr = Address(
            recipient_name=dto.buyer_name,
            phone_number=dto.buyer_phone,
            street_address=dto.street_address,
            city=dto.city,
            postal_code=dto.postal_code
        )

        domain_items: List[OrderItem] = []
        total_amount = Decimal("0")

        # Delegate pricing calculation entirely to PricingServicePort (kinetix-pricing-service)
        if self._pricing_port:
            pricing_payload_items = [
                {
                    "product_id": it.sku,
                    "base_price": str(it.price),
                    "quantity": it.quantity,
                }
                for it in dto.items
            ]
            pricing_res = self._pricing_port.calculate_price(
                items=pricing_payload_items,
                voucher_code=dto.voucher_code
            )

            total_amount = Decimal(str(pricing_res.get("final_total", "0")))
            pricing_items_map = {
                str(item_res.get("product_id")): Decimal(str(item_res.get("final_unit_price", "0")))
                for item_res in pricing_res.get("items", [])
            }

            for it in dto.items:
                final_unit_price = pricing_items_map.get(it.sku, it.price)
                domain_items.append(
                    OrderItem(
                        sku=it.sku,
                        product_name=it.product_name,
                        quantity=it.quantity,
                        price=Money(currency="IDR", amount=final_unit_price)
                    )
                )
        else:
            for it in dto.items:
                item_price = Money(currency="IDR", amount=it.price)
                item_total = it.price * Decimal(it.quantity)
                total_amount += item_total

                domain_items.append(
                    OrderItem(
                        sku=it.sku,
                        product_name=it.product_name,
                        quantity=it.quantity,
                        price=item_price
                    )
                )

        order_num = f"ORD-STF-{uuid.uuid4().hex[:8].upper()}"

        new_order = Order(
            id=None,
            order_number=order_num,
            buyer_name=dto.buyer_name,
            buyer_phone=dto.buyer_phone,
            shipping_address=shipping_addr,
            total_amount=Money(currency="IDR", amount=total_amount),
            items=domain_items,
            status="pending",
            idempotency_key=dto.idempotency_key
        )

        saved_order = self._order_repo.save(new_order)

        try:
            grpc_res = self._fulfillment_port.submit_fulfillment_order(
                order=saved_order
            )

            is_offline = bool(grpc_res.get("offline", False))
            is_success = bool(grpc_res.get("success", True))

            if not is_success and not is_offline:
                raise RuntimeError(str(grpc_res.get("error", "Fulfillment service rejected order")))

            fulfillment_status = grpc_res.get("status", "received" if is_offline else "pending")
            fulfillment_ref = str(grpc_res.get("order_id", saved_order.id))

            return CheckoutResultDTO(
                success=True,
                order_id=saved_order.id,
                order_number=saved_order.order_number,
                status=fulfillment_status,
                total_amount=total_amount,
                fulfillment_ref=fulfillment_ref,
                message="Checkout completed and dispatched to Warehouse OMS" if not is_offline else "Order created and queued for offline fulfillment"
            )

        except Exception as exc:
            failed_order = Order(
                id=saved_order.id,
                order_number=saved_order.order_number,
                buyer_name=saved_order.buyer_name,
                buyer_phone=saved_order.buyer_phone,
                shipping_address=saved_order.shipping_address,
                total_amount=saved_order.total_amount,
                items=saved_order.items,
                status="failed",
                idempotency_key=saved_order.idempotency_key,
                created_at=saved_order.created_at
            )
            self._order_repo.save(failed_order)

            return CheckoutResultDTO(
                success=False,
                order_id=saved_order.id,
                order_number=saved_order.order_number,
                status="failed",
                total_amount=total_amount,
                fulfillment_ref="",
                message=f"Fulfillment submission failed: {exc}"
            )

    def reserve_cart_stock(self, dto: ReserveCartStockInputDTO) -> ReservationResult:
        if dto.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        if not self._bin_stock_port:
            raise ValueError("BinStockServicePort is not configured")

        res = self._bin_stock_port.reserve_stock(sku=dto.sku, quantity=dto.quantity)
        success = bool(res.get("success", False))

        return ReservationResult(
            sku=dto.sku,
            quantity=dto.quantity,
            success=success,
            bin_location=str(res.get("bin_location", "N/A")),
            message=str(res.get("message", "Stock reserved successfully"))
        )
