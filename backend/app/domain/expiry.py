"""Expiry classification and usable(batch). Source: Revision 6.3 sections 2, 3.7
and Revision 5 section 2.6 (as quoted in 6.3).

Pure functions: no DB, no framework. The warning window `w` (warning days) is a
placeholder parameter that is still OPEN (D9), so it has NO default here.
Dates are plain `date`; the business timezone is Asia/Ho_Chi_Minh (UTC+7, no DST).
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))
ERR_EXPIRED_ACTION = "ACTION_NOT_PERMITTED_FOR_EXPIRED_BATCH"


def today_vn(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(VN_TZ).date()


class ExpiryStatus(str, Enum):
    EXPIRED = "EXPIRED"
    EXPIRES_SOON = "EXPIRES_SOON"
    OK = "OK"
    NO_EXPIRY = "NO_EXPIRY"


def classify_expiry(expiry_date: date | None, today: date, warning_days: int) -> ExpiryStatus:
    """EXPIRED iff expiry_date < today; EXPIRES_SOON iff 0 <= days <= w; else OK."""
    if warning_days < 0:
        raise ValueError("warning_days must be >= 0")
    if expiry_date is None:
        return ExpiryStatus.NO_EXPIRY
    days = (expiry_date - today).days
    if days < 0:
        return ExpiryStatus.EXPIRED
    if days <= warning_days:
        return ExpiryStatus.EXPIRES_SOON
    return ExpiryStatus.OK


def usable(remaining_qty: Decimal, status: ExpiryStatus, expired_batches_consumable: bool) -> bool:
    """usable(batch) = remaining_qty > 0 and (status != EXPIRED or expired_batches_consumable)."""
    return remaining_qty > 0 and (status != ExpiryStatus.EXPIRED or expired_batches_consumable)


@dataclass(frozen=True)
class CookBatchDecision:
    permitted: bool
    error_code: str | None = None


def explicit_cook_batch_eligibility(status: ExpiryStatus, expired_batch_actions: frozenset[str]) -> CookBatchDecision:
    """Section 3.7: a non-expired explicit batch is always eligible; an expired one only
    if COOK is in expired_batch_actions, regardless of expired_batches_consumable."""
    if status == ExpiryStatus.EXPIRED and "COOK" not in expired_batch_actions:
        return CookBatchDecision(False, ERR_EXPIRED_ACTION)
    return CookBatchDecision(True)
