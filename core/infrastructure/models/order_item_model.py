from django.db import models
from core.infrastructure.models.order_model import OrderModel

class OrderItemModel(models.Model):
    id: int
    objects: models.Manager["OrderItemModel"]

    order = models.ForeignKey(OrderModel, related_name="items", on_delete=models.CASCADE)
    sku = models.CharField(max_length=64)
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    bin_location = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        db_table = "order_items"

    def __str__(self) -> str:
        return f"{self.quantity}x {self.sku} @ {self.price}"
