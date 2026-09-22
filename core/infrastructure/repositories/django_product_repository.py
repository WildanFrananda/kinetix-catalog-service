from datetime import datetime
from typing import Optional, List, Tuple
from decimal import Decimal
from django.db.models import Q
from core.domain.entities import Product, Category, ProductChangePage
from core.domain.repositories import ProductRepository
from core.infrastructure.models import ProductModel, CategoryModel

class DjangoProductRepository(ProductRepository):
    def find_page(
        self,
        category_slug: Optional[str] = None,
        search_query: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Product], int]:
        qs = ProductModel.objects.select_related("category").filter(is_active=True)
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if search_query:
            qs = qs.filter(title__icontains=search_query)

        total = qs.count()

        page = [self._to_domain_entity(orm_p) for orm_p in qs[offset : offset + limit]]

        return page, total

    def find_changed_since(
        self,
        updated_through: Optional[datetime] = None,
        last_sku: str = "",
        limit: int = 100,
    ) -> ProductChangePage:
        qs = ProductModel.objects.select_related("category")

        if updated_through is not None:
            qs = qs.filter(
                Q(updated_at__gt=updated_through)
                | (Q(updated_at=updated_through) & Q(sku__gt=last_sku))
            )

        qs = qs.order_by("updated_at", "sku")

        rows = list(qs[: limit + 1])
        has_more = len(rows) > limit
        rows = rows[:limit]

        upserted: List[Product] = []
        removed_skus: List[str] = []
        for row in rows:
            if row.is_active:
                upserted.append(self._to_domain_entity(row))
            else:
                removed_skus.append(row.sku)

        if rows:
            last = rows[-1]
            next_updated_through: Optional[datetime] = last.updated_at
            next_last_sku = last.sku
        else:
            next_updated_through = updated_through
            next_last_sku = last_sku

        return ProductChangePage(
            upserted=upserted,
            removed_skus=removed_skus,
            next_updated_through=next_updated_through,
            next_last_sku=next_last_sku,
            has_more=has_more,
        )

    def count_active_products(self) -> int:
        return ProductModel.objects.filter(is_active=True).count()

    def find_by_sku(self, sku: str) -> Optional[Product]:
        try:
            orm_p = ProductModel.objects.select_related("category").get(sku=sku, is_active=True)
            return self._to_domain_entity(orm_p)
        except ProductModel.DoesNotExist:
            return None

    def find_by_id(self, product_id: int) -> Optional[Product]:
        try:
            orm_p = ProductModel.objects.select_related("category").get(id=product_id)
            return self._to_domain_entity(orm_p)
        except ProductModel.DoesNotExist:
            return None

    def save(self, product: Product) -> Product:
        category_orm = CategoryModel.objects.get(id=product.category.id)
        orm_p, _ = ProductModel.objects.update_or_create(
            sku=product.sku,
            defaults={
                "title": product.title,
                "description": product.description,
                "price": product.price,
                "currency": product.currency,
                "image_url": product.image_url,
                "category": category_orm,
                "merchant_principal_id": product.merchant_principal_id,
                "is_active": product.is_active,
            }
        )
        return self._to_domain_entity(orm_p)

    def delete(self, product_id: int) -> bool:
        updated = ProductModel.objects.filter(id=product_id).update(is_active=False)
        return updated > 0

    def find_all_categories(self) -> List[Category]:
        qs = CategoryModel.objects.all()
        return [Category(id=c.id, name=c.name, slug=c.slug) for c in qs]

    def find_category_by_id(self, category_id: int) -> Optional[Category]:
        try:
            c = CategoryModel.objects.get(id=category_id)
            return Category(id=c.id, name=c.name, slug=c.slug)
        except CategoryModel.DoesNotExist:
            return None

    def save_category(self, category: Category) -> Category:
        orm_c, _ = CategoryModel.objects.update_or_create(
            slug=category.slug,
            defaults={"name": category.name}
        )
        return Category(id=orm_c.id, name=orm_c.name, slug=orm_c.slug)

    def delete_category(self, category_id: int) -> bool:
        count, _ = CategoryModel.objects.filter(id=category_id).delete()
        return count > 0

    def _to_domain_entity(self, orm_p: ProductModel) -> Product:
        category = Category(
            id=orm_p.category.id,
            name=orm_p.category.name,
            slug=orm_p.category.slug
        )
        return Product(
            id=orm_p.id,
            sku=orm_p.sku,
            title=orm_p.title,
            description=orm_p.description,
            price=Decimal(str(orm_p.price)),
            currency=orm_p.currency,
            image_url=orm_p.image_url,
            category=category,
            merchant_principal_id=orm_p.merchant_principal_id,
            is_active=orm_p.is_active,
            created_at=orm_p.created_at,
            updated_at=orm_p.updated_at,
        )
