"""Unit conversion, Rev 4 section 2.A. MASS and VOLUME convert inside their own dimension; COUNT never converts
automatically; everything else needs an ingredient-specific conversion row."""
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import round_qty


class UnitNotConvertible(Exception):
    def __init__(self, from_unit: str, to_unit: str):
        super().__init__(f"UNIT_NOT_CONVERTIBLE {from_unit}->{to_unit}")
        self.from_unit, self.to_unit = from_unit, to_unit


@dataclass(frozen=True)
class UnitInfo:
    dimension: str                      # MASS | VOLUME | COUNT
    factor: Decimal | None              # factor_to_dimension_base (None for COUNT)


def factor_to_base(from_unit: str, base_unit: str, units: dict[str, UnitInfo],
                   conversions: dict[str, Decimal]) -> Decimal:
    """How many base units one `from_unit` is worth."""
    if from_unit == base_unit:
        return Decimal(1)
    f, b = units.get(from_unit), units.get(base_unit)
    if f is None or b is None:
        raise UnitNotConvertible(from_unit, base_unit)
    if f.dimension == b.dimension and f.dimension in ("MASS", "VOLUME"):
        return f.factor / b.factor
    if from_unit in conversions:
        return conversions[from_unit]
    raise UnitNotConvertible(from_unit, base_unit)


def convert_to_base(qty: Decimal, from_unit: str, base_unit: str, units: dict[str, UnitInfo],
                    conversions: dict[str, Decimal]) -> Decimal:
    return round_qty(qty * factor_to_base(from_unit, base_unit, units, conversions))
