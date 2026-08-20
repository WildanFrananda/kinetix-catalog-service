from dataclasses import dataclass

@dataclass(frozen=True)
class Address:
    recipient_name: str
    phone_number: str
    street_address: str
    city: str
    postal_code: str
