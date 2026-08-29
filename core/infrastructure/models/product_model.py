from django.db import models
from core.infrastructure.models.category_model import CategoryModel

class ProductModel(models.Model):
    id: int
    objects: models.Manager["ProductModel"]

    merchant_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="IDR")
    image_url = models.URLField(blank=True)
    category = models.ForeignKey(CategoryModel, related_name="products", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.sku})"
