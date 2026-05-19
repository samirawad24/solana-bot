import pytest

from risk.daily_limit import DailyLimitBreached, DailyLimitGuard


def test_daily_limit_not_breached():
    guard = DailyLimitGuard(opening_value=10000, limit_pct=0.05)
    assert guard.floor == pytest.approx(9500.0)
    assert guard.opening_value == 10000.0
    assert guard.limit_pct == 0.05

    # Values above the floor must not raise
    guard.check(9501.0)
    guard.check(10000.0)
    guard.check(10500.0)


def test_daily_limit_breached():
    guard = DailyLimitGuard(opening_value=10000, limit_pct=0.05)

    # Exactly at floor (≤) → breach
    with pytest.raises(DailyLimitBreached) as exc_info:
        guard.check(9500.0)
    exc = exc_info.value
    assert exc.opening_value == 10000.0
    assert exc.current_value == 9500.0
    assert exc.loss_pct == pytest.approx(0.05)
    assert exc.limit_pct == 0.05

    # Below floor → also raises
    with pytest.raises(DailyLimitBreached):
        guard.check(9000.0)


def test_daily_limit_reset():
    guard = DailyLimitGuard(opening_value=10000, limit_pct=0.05)
    guard.reset(9800.0)

    assert guard.opening_value == 9800.0
    assert guard.floor == pytest.approx(9310.0)  # 9800 * 0.95

    guard.check(9311.0)   # above new floor → no raise

    with pytest.raises(DailyLimitBreached):
        guard.check(9310.0)  # exactly at new floor → raises

    # Invalid inputs
    with pytest.raises(ValueError):
        DailyLimitGuard(opening_value=0, limit_pct=0.05)
    with pytest.raises(ValueError):
        DailyLimitGuard(opening_value=10000, limit_pct=1.5)
    with pytest.raises(ValueError):
        guard.reset(0)
