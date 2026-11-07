"""FEFO allocation (Rev 3 II.6): expiry_date NULLS LAST, received_on, id."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class BatchView:
    id: str
    expiry_date: date | None
    received_on: date
    remaining_qty: Decimal
    unit_cost: Decimal


def fefo_key(b: BatchView):
    return (b.expiry_date is None, b.expiry_date or date.max, b.received_on, str(b.id))


def allocate(batches: list[BatchView], need: Decimal) -> tuple[list[tuple[BatchView, Decimal]], Decimal]:
    """Take `need` from batches in FEFO order. Mutates remaining_qty on the views so a caller can allocate
    several lines against the same locked batches. Returns (takes, short_qty)."""
    left, takes = need, []
    for b in sorted(batches, key=fefo_key):
        if left <= 0:
            break
        if b.remaining_qty <= 0:
            continue
        t = min(b.remaining_qty, left)
        b.remaining_qty -= t
        left -= t
        takes.append((b, t))
    return takes, left
