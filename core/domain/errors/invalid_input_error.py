class InvalidInputError(ValueError):
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field: str = field
        self.reason: str = reason
