from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from common.v1 import common_pb2

CURRENCY = "IDR"
MINOR_PER_MAJOR = Decimal("100")


def to_money(amount: Decimal) -> common_pb2.Money:
    minor = (amount * MINOR_PER_MAJOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return common_pb2.Money(amount_minor=int(minor), currency=CURRENCY)


def from_money(money: Optional[common_pb2.Money]) -> Decimal:
    if money is None:
        return Decimal("0")

    return Decimal(money.amount_minor) / MINOR_PER_MAJOR
