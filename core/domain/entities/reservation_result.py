from dataclasses import dataclass

@dataclass(frozen=True)
class ReservationResult:
    sku: str
    quantity: int
    success: bool
    bin_location: str
    message: str
    expires_in_seconds: int = 900
