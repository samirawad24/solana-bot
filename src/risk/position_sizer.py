def calculate_position_size(
    portfolio_value: float,
    entry_price: float,
    stop_price: float,
    risk_pct: float = 0.02,
    available_cash: float | None = None,
) -> float:
    """Return the number of SOL units to buy/sell for the given risk parameters.

    Formula: units = (portfolio_value × risk_pct) / |entry - stop|

    The result is capped so the notional cost (units × entry_price) never
    exceeds available_cash. If available_cash is not provided, portfolio_value
    is used as the cap (conservative — assumes no open positions tie up cash).

    Args:
        portfolio_value: Total portfolio value used to calculate dollar risk.
        entry_price:     Anticipated fill price per unit.
        stop_price:      Stop-loss price; determines risk per unit.
        risk_pct:        Fraction of portfolio to risk on this trade (0–1).
        available_cash:  Cash free to deploy; caps position notional.

    Raises:
        ValueError: If entry_price == stop_price (zero risk per unit would
                    produce infinite position size).
    """
    if entry_price <= 0:
        raise ValueError(f"entry_price must be positive, got {entry_price}")

    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0:
        raise ValueError(
            "entry_price and stop_price cannot be equal — "
            "risk per unit would be zero (infinite position size)."
        )

    dollar_risk = portfolio_value * risk_pct
    units = dollar_risk / risk_per_unit

    cash_cap  = available_cash if available_cash is not None else portfolio_value
    max_units = cash_cap / entry_price
    return min(units, max_units)
