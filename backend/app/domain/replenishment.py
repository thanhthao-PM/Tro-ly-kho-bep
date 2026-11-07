"""Replenishment classification, Rev 5 section 2.4 (formula D25 unchanged), with 6.3 s3.5 date basis.
Inputs are plain numbers so this stays testable; all parameters are PLACEHOLDERS from kitchen_settings."""
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from app.domain.ledger_rules import ObservationWindow

DEFAULT_STEP = Decimal("0.001")


@dataclass(frozen=True)
class ReplenishmentInput:
    ingredient_id: str
    name: str
    unit: str
    usable_qty: Decimal
    min_stock_qty: Decimal
    order_step: Decimal | None
    consumption_total: Decimal           # positive, net of reversals, inside the window
    window: ObservationWindow
    target_coverage_days: int
    min_history_days: int


@dataclass(frozen=True)
class Suggestion:
    kind: str                            # item | insufficient_data | no_recent_consumption | none
    rule: str | None = None
    reason: str | None = None
    avg_daily: Decimal | None = None
    days_of_cover: Decimal | None = None
    raw_order_qty: Decimal | None = None
    suggested_order_qty: Decimal | None = None


def _ceil_to_step(raw: Decimal, step: Decimal) -> Decimal:
    return (raw / step).to_integral_value(rounding=ROUND_CEILING) * step


def classify(i: ReplenishmentInput) -> list[Suggestion]:
    """May return two entries: an item AND an insufficient_data caveat (Rev 5 2.4)."""
    step = i.order_step or DEFAULT_STEP
    out: list[Suggestion] = []
    min_trig = i.min_stock_qty > 0 and i.usable_qty < i.min_stock_qty
    min_raw = max(Decimal(0), i.min_stock_qty - i.usable_qty)
    obs = i.window.observed_days
    evaluable = obs >= max(1, i.min_history_days)

    if not evaluable:
        reason = i.window.reason or ("HISTORY_TOO_SHORT" if obs >= 1 else "NO_COMPLETE_DAYS")
        if reason is None:
            reason = "HISTORY_TOO_SHORT"
        out.append(Suggestion("insufficient_data", reason=reason))
        if min_trig:
            out.append(Suggestion("item", rule="MIN_STOCK_ONLY", raw_order_qty=min_raw,
                                  suggested_order_qty=_ceil_to_step(min_raw, step)))
        return out

    avg = i.consumption_total / Decimal(obs)
    cover = None if avg == 0 else i.usable_qty / avg
    cov_trig = avg > 0 and cover is not None and cover < i.target_coverage_days
    if not (cov_trig or min_trig):
        return [Suggestion("no_recent_consumption")] if avg == 0 else [Suggestion("none", avg_daily=avg, days_of_cover=cover)]
    raws = []
    if cov_trig:
        raws.append(max(Decimal(0), i.target_coverage_days * avg - i.usable_qty))
    if min_trig:
        raws.append(min_raw)
    raw = max(raws)
    rule = "BOTH" if (cov_trig and min_trig) else ("COVERAGE" if cov_trig else "MIN_STOCK_ONLY")
    return [Suggestion("item", rule=rule, avg_daily=avg, days_of_cover=cover, raw_order_qty=raw,
                       suggested_order_qty=_ceil_to_step(raw, step))]
