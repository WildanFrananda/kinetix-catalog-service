class SkuTakenError(Exception):
    def __init__(self, sku: str) -> None:
        super().__init__(f"another product already uses the SKU {sku}")
        self.sku: str = sku
