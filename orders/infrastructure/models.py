from django.db import models

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.order_number} ({self.status})"

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
