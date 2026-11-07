from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.domain.expiry import (
    ERR_EXPIRED_ACTION, ExpiryStatus as E, classify_expiry, explicit_cook_batch_eligibility,
    today_vn, usable,
)

T = date(2026, 11, 6)


@pytest.mark.parametrize("exp,w,want", [
    (date(2026, 11, 5), 3, E.EXPIRED),        # yesterday
    (date(2026, 11, 6), 3, E.EXPIRES_SOON),   # today = 0 days
    (date(2026, 11, 9), 3, E.EXPIRES_SOON),   # exactly w
    (date(2026, 11, 10), 3, E.OK),            # w + 1
    (date(2026, 11, 6), 0, E.EXPIRES_SOON),   # w = 0 still flags today
    (date(2026, 11, 7), 0, E.OK),
    (None, 3, E.NO_EXPIRY),
])
def test_classify(exp, w, want):
    assert classify_expiry(exp, T, w) == want


def test_negative_window_rejected():
    with pytest.raises(ValueError):
        classify_expiry(T, T, -1)


@pytest.mark.parametrize("qty,st,cons,want", [
    ("1", E.OK, False, True), ("0", E.OK, False, False),
    ("1", E.EXPIRED, False, False), ("1", E.EXPIRED, True, True),
    ("1", E.NO_EXPIRY, False, True), ("1", E.EXPIRES_SOON, False, True),
])
def test_usable(qty, st, cons, want):
    assert usable(Decimal(qty), st, cons) is want


@pytest.mark.parametrize("st,actions,ok", [
    (E.OK, frozenset(), True), (E.EXPIRES_SOON, frozenset({"WASTE"}), True),
    (E.EXPIRED, frozenset({"WASTE"}), False), (E.EXPIRED, frozenset({"COOK"}), True),
    (E.EXPIRED, frozenset(), False),
])
def test_cook_eligibility(st, actions, ok):
    d = explicit_cook_batch_eligibility(st, actions)
    assert d.permitted is ok
    assert d.error_code == (None if ok else ERR_EXPIRED_ACTION)


def test_today_vn_crosses_midnight():
    # 20:00 UTC on 5 Nov is 03:00 on 6 Nov in Ho Chi Minh City
    assert today_vn(datetime(2026, 11, 5, 20, 0, tzinfo=timezone.utc)) == date(2026, 11, 6)
