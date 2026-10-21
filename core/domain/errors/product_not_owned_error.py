class ProductNotOwnedError(Exception):
    def __init__(self, product_id: int) -> None:
        super().__init__("Product does not belong to this merchant")
        self.product_id: int = product_id
