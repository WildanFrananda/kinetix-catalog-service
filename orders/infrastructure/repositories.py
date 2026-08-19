from typing import Optional, List
from decimal import Decimal
from django.db import transaction
from orders.domain.entities import Order, OrderItem, Money, Address
from orders.domain.repositories import OrderRepository
from orders.infrastructure.models import OrderModel, OrderItemModel

class DjangoOrderRepository(OrderRepository):
    def save(self, order: Order) -> Order:
        with transaction.atomic():
            if order.id:
                orm_order = OrderModel.objects.get(id=order.id)
                orm_order.status = order.status
                orm_order.save()
            else:
                orm_order = OrderModel.objects.create(
                    order_number=order.order_number,
                    buyer_name=order.buyer_name,
                    buyer_phone=order.buyer_phone,
                    recipient_name=order.shipping_address.recipient_name,
                    street_address=order.shipping_address.street_address,
                    city=order.shipping_address.city,
                    postal_code=order.shipping_address.postal_code,
                    total_amount=order.total_amount.amount,
                    currency=order.total_amount.currency,
                    status=order.status
                )

                for item in order.items:
                    OrderItemModel.objects.create(
                        order=orm_order,
                        sku=item.sku,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        price=item.price.amount,
                        bin_location=item.bin_location
                    )

            return self._to_domain_entity(orm_order)

    def find_by_id(self, order_id: int) -> Optional[Order]:
        try:
            orm_order = OrderModel.objects.prefetch_related("items").get(id=order_id)
            return self._to_domain_entity(orm_order)
        except OrderModel.DoesNotExist:
            return None

    def find_by_order_number(self, order_number: str) -> Optional[Order]:
        try:
            orm_order = OrderModel.objects.prefetch_related("items").get(order_number=order_number)
            return self._to_domain_entity(orm_order)
        except OrderModel.DoesNotExist:
            return None

    def list_all(self) -> List[Order]:
        orm_orders = OrderModel.objects.prefetch_related("items").all()
        return [self._to_domain_entity(o) for o in orm_orders]

    def _to_domain_entity(self, orm_order: OrderModel) -> Order:
        items: List[OrderItem] = [
            OrderItem(
                sku=it.sku,
                product_name=it.product_name,
                quantity=it.quantity,
                price=Money(currency=orm_order.currency, amount=Decimal(str(it.price))),
                bin_location=it.bin_location
            )
            for it in orm_order.items.all()
        ]

        shipping_addr = Address(
            recipient_name=orm_order.recipient_name,
            phone_number=orm_order.buyer_phone,
            street_address=orm_order.street_address,
            city=orm_order.city,
            postal_code=orm_order.postal_code
        )

        return Order(
            id=orm_order.id,
            order_number=orm_order.order_number,
            buyer_name=orm_order.buyer_name,
            buyer_phone=orm_order.buyer_phone,
            shipping_address=shipping_addr,
            total_amount=Money(currency=orm_order.currency, amount=Decimal(str(orm_order.total_amount))),
            items=items,
            status=orm_order.status,
            created_at=orm_order.created_at
        )
