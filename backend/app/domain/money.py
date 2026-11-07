"""Rounding helpers. D7 (rounding rule) is OPEN: round-half-up is the documented PLACEHOLDER, kept in this one place."""
from decimal import ROUND_HALF_UP, Decimal

Q3 = Decimal("0.001")
Q6 = Decimal("0.000001")


def d(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def round_qty(v) -> Decimal:
    return d(v).quantize(Q3, rounding=ROUND_HALF_UP)


def round_cost(v) -> Decimal:
    return d(v).quantize(Q6, rounding=ROUND_HALF_UP)


def vnd(v) -> int:
    """Whole VND, half-up (placeholder rule)."""
    return int(d(v).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
