import pytest

from risk.position_sizer import calculate_position_size


def test_position_size_basic():
    # dollar_risk = 10000 * 0.02 = 200; risk_per_unit = |100 - 90| = 10
    # units = 200 / 10 = 20; max_units = 10000 / 100 = 100 (not binding)
    units = calculate_position_size(
        portfolio_value=10000, entry_price=100, stop_price=90,
        risk_pct=0.02, available_cash=10000,
    )
    assert units == pytest.approx(20.0)


def test_position_size_capped_by_cash():
    # dollar_risk = 10000 * 0.02 = 200; risk_per_unit = |100 - 99| = 1
    # uncapped units = 200; max_units = 5000 / 100 = 50 → capped at 50
    units = calculate_position_size(
        portfolio_value=10000, entry_price=100, stop_price=99,
        risk_pct=0.02, available_cash=5000,
    )
    assert units == pytest.approx(50.0)

    # entry == stop → zero risk per unit → ValueError
    with pytest.raises(ValueError, match="equal"):
        calculate_position_size(10000, 100, 100, 0.02)

    # entry <= 0 → ValueError
    with pytest.raises(ValueError):
        calculate_position_size(10000, 0, 90, 0.02)
