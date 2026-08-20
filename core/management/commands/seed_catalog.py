from typing import Any
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.domain.entities import Category, Product
from core.infrastructure.repositories import DjangoProductRepository

class Command(BaseCommand):
    help = "Seeds initial product catalog and category data"

    def handle(self, *args: Any, **options: Any) -> None:
        repo = DjangoProductRepository()

        apparel = repo.save_category(Category(id=None, name="Apparel", slug="apparel"))
        footwear = repo.save_category(Category(id=None, name="Footwear", slug="footwear"))
        accessories = repo.save_category(Category(id=None, name="Accessories", slug="accessories"))

        products_data = [
            Product(
                id=None,
                sku="TSHIRT-BLK-M",
                title="Oversized Heavyweight Black Tee - M",
                description="240 GSM Premium Cotton Oversized T-Shirt with relaxed silhouette.",
                price=Decimal("189000.00"),
                currency="IDR",
                image_url="https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800",
                category=apparel
            ),
            Product(
                id=None,
                sku="HOODIE-GRY-L",
                title="Minimalist Charcoal Fleece Hoodie - L",
                description="Heavyweight fleece hoodie with kangaroo pocket and double-lined hood.",
                price=Decimal("450000.00"),
                currency="IDR",
                image_url="https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800",
                category=apparel
            ),
            Product(
                id=None,
                sku="JEANS-BLU-32",
                title="Raw Denim Straight Fit Jeans - 32",
                description="14oz Japanese selvage raw denim with classic straight leg cut.",
                price=Decimal("620000.00"),
                currency="IDR",
                image_url="https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=800",
                category=apparel
            ),
            Product(
                id=None,
                sku="SNEAKER-WHT-42",
                title="Retro Low Top Leather Sneaker - 42",
                description="Full-grain leather sneaker with cushioned memory foam insole.",
                price=Decimal("890000.00"),
                currency="IDR",
                image_url="https://images.unsplash.com/photo-1549298916-b41d501d3772?w=800",
                category=footwear
            ),
            Product(
                id=None,
                sku="CAP-BLK-OS",
                title="Embroidered Cotton Canvas Cap",
                description="6-panel unstructured canvas cap with adjustable brass strapback.",
                price=Decimal("149000.00"),
                currency="IDR",
                image_url="https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=800",
                category=accessories
            )
        ]

        for p in products_data:
            repo.save(p)

        self.stdout.write(self.style.SUCCESS("Successfully seeded 3 categories and 5 products!"))
