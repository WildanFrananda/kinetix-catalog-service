from typing import TYPE_CHECKING
from django.db import models

if TYPE_CHECKING:
    from core.infrastructure.models.order_item_model import OrderItemModel

class OrderModel(models.Model):
    id: int
    objects: models.Manager["OrderModel"]
    items: models.Manager["OrderItemModel"]

    order_number = models.CharField(max_length=64, unique=True, db_index=True)
    buyer_name = models.CharField(max_length=128)
    buyer_phone = models.CharField(max_length=32)
    recipient_name = models.CharField(max_length=128)
    street_address = models.TextField()
    city = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=16)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="IDR")
    status = models.CharField(max_length=32, default="pending", db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.order_number} ({self.status})"
