import uuid
from decimal import Decimal
from typing import Optional, List
from orders.domain.entities import Order, OrderItem, Money, Address
from orders.domain.repositories import OrderRepository, FulfillmentServicePort
from orders.application.dto import CreateOrderInputDTO, CheckoutResultDTO

class CheckoutOrderService:
    def __init__(self, order_repo: OrderRepository, fulfillment_port: FulfillmentServicePort):
        self._order_repo = order_repo
        self._fulfillment_port = fulfillment_port

    def execute(self, dto: CreateOrderInputDTO) -> CheckoutResultDTO:
        if not dto.buyer_name.strip():
            raise ValueError("Buyer name cannot be blank")
        if not dto.street_address.strip():
            raise ValueError("Street address cannot be blank")
        if not dto.items:
            raise ValueError("Order must contain at least one item")

        shipping_addr = Address(
            recipient_name=dto.buyer_name,
            phone_number=dto.buyer_phone,
            street_address=dto.street_address,
            city=dto.city,
            postal_code=dto.postal_code
        )

        domain_items: List[OrderItem] = []
        total_amount = Decimal("0")

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
            status="pending"
        )

        saved_order = self._order_repo.save(new_order)

        grpc_res = self._fulfillment_port.submit_fulfillment_order(
            order=saved_order,
            merchant_api_key=dto.merchant_api_key
        )

        fulfillment_status = grpc_res.get("status", "received")
        fulfillment_ref = str(grpc_res.get("order_id", saved_order.id))

        return CheckoutResultDTO(
            success=True,
            order_id=saved_order.id,
            order_number=saved_order.order_number,
            status=fulfillment_status,
            total_amount=total_amount,
            fulfillment_ref=fulfillment_ref,
            message="Checkout completed and dispatched to Warehouse OMS"
        )
