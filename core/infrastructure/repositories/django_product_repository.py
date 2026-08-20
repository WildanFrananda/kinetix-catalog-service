from typing import Optional, List
from decimal import Decimal
from core.domain.entities import Product, Category
from core.domain.repositories import ProductRepository
from core.infrastructure.models import ProductModel, CategoryModel

class DjangoProductRepository(ProductRepository):
    def find_all(self, category_slug: Optional[str] = None, search_query: Optional[str] = None) -> List[Product]:
        qs = ProductModel.objects.select_related("category").all()
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if search_query:
            qs = qs.filter(title__icontains=search_query)

        return [self._to_domain_entity(orm_p) for orm_p in qs]

    def find_by_sku(self, sku: str) -> Optional[Product]:
        try:
            orm_p = ProductModel.objects.select_related("category").get(sku=sku)
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
                "category": category_orm
            }
        )
        return self._to_domain_entity(orm_p)

    def save_category(self, category: Category) -> Category:
        orm_c, _ = CategoryModel.objects.update_or_create(
            slug=category.slug,
            defaults={"name": category.name}
        )
        return Category(id=orm_c.id, name=orm_c.name, slug=orm_c.slug)

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
            created_at=orm_p.created_at
        )
