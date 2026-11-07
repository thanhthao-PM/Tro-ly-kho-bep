"""Pure rules quoted from Revision 6.3 (sections 3.3.1, 3.4, 3.5, 3.6, 3.8).
Only what 6.3 states completely. Anything defined in Revisions 3/4/5 that is not
reproduced in 6.3 (FEFO tie-breaks, replenishment formula, ...) is NOT implemented.
"""
from dataclasses import dataclass
from datetime import date, timedelta


# ---- 3.3.1 attribution_date -------------------------------------------------
@dataclass(frozen=True)
class MovementDates:
    occurred_on: date
    sale_business_date: date | None = None       # set when the movement has sale_line_id
    document_business_date: date | None = None   # USAGE_CONSUMPTION with document_line_id
    disposal_occurred_on: date | None = None     # disposal-linked


def attribution_date(m: MovementDates) -> date:
    if m.sale_business_date is not None:
        return m.sale_business_date
    if m.document_business_date is not None:
        return m.document_business_date
    if m.disposal_occurred_on is not None:
        return m.disposal_occurred_on
    return m.occurred_on


def reversal_attribution_date(original: MovementDates) -> date:
    """A REVERSAL is attributed to the same date as its original."""
    return attribution_date(original)


# ---- 3.4 / 3.6 shortages ----------------------------------------------------
OPEN = "OPEN"
WRITTEN_OFF_ESTIMATED = "WRITTEN_OFF_ESTIMATED"
WAIVED = "WAIVED"
CONSUMED_FROM_STOCK = "CONSUMED_FROM_STOCK"


@dataclass(frozen=True)
class Shortage:
    is_open: bool
    resolution: str | None = None  # one of the constants above when resolved


def consumption_status(shortages: list[Shortage]) -> str:
    """FULL if never short; PARTIAL if any shortage is OPEN; RESOLVED otherwise."""
    if not shortages:
        return "FULL"
    return "PARTIAL" if any(s.is_open for s in shortages) else "RESOLVED"


@dataclass(frozen=True)
class CostStatus:
    has_open_shortages: bool
    all_actual: bool
    open_count: int
    written_off_estimated_count: int
    waived_count: int


def cost_status(shortages: list[Shortage]) -> CostStatus:
    """all_actual: no OPEN, none WRITTEN_OFF_ESTIMATED, none WAIVED.
    CONSUMED_FROM_STOCK does not affect it. Based on records, never amounts."""
    o = sum(1 for s in shortages if s.is_open)
    w = sum(1 for s in shortages if not s.is_open and s.resolution == WRITTEN_OFF_ESTIMATED)
    v = sum(1 for s in shortages if not s.is_open and s.resolution == WAIVED)
    return CostStatus(o > 0, o == 0 and w == 0 and v == 0, o, w, v)


# ---- 3.5 replenishment observation window ----------------------------------
@dataclass(frozen=True)
class ObservationWindow:
    reason: str | None  # None | "NO_HISTORY" | "NO_COMPLETE_DAYS"
    window_start: date | None
    window_end: date | None
    observed_days: int


def observation_window(history_start: date | None, today: date, window_days: int) -> ObservationWindow:
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    if history_start is None:
        return ObservationWindow("NO_HISTORY", None, None, 0)
    yesterday = today - timedelta(days=1)
    if history_start > yesterday:
        return ObservationWindow("NO_COMPLETE_DAYS", None, yesterday, 0)
    start = max(yesterday - timedelta(days=window_days - 1), history_start)
    return ObservationWindow(None, start, yesterday, max(0, (yesterday - start).days + 1))


# ---- 3.8 base-unit lock predicate ------------------------------------------
@dataclass(frozen=True)
class OperationalDataCounts:
    batches: int = 0                      # including empty batches
    stock_movements: int = 0
    recipe_items: int = 0                 # including soft-deleted dishes
    non_cancelled_document_lines: int = 0
    stock_shortages: int = 0
    unit_conversions: int = 0


def has_operational_data(c: OperationalDataCounts) -> bool:
    """True if any of the six conditions holds; deleted_at flags are ignored."""
    return any((c.batches, c.stock_movements, c.recipe_items,
                c.non_cancelled_document_lines, c.stock_shortages, c.unit_conversions))
