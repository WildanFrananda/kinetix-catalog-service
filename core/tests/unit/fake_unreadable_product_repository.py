from typing import Optional

from core.domain.entities import Product
from core.tests.unit.fake_product_repository import FakeProductRepository


class FakeUnreadableProductRepository(FakeProductRepository):
    def find_by_sku(self, sku: str) -> Optional[Product]:
        raise RuntimeError("the database did not answer")
