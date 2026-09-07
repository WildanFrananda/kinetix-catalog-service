class CircuitOpenError(Exception):
    def __init__(self, breaker_name: str) -> None:
        super().__init__(f"circuit '{breaker_name}' is open; the call was not sent")
        self.breaker_name: str = breaker_name
