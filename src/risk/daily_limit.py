class DailyLimitBreached(Exception):
    """Raised by DailyLimitGuard.check() when the daily loss floor is breached.

    Attributes:
        opening_value:  Portfolio value at the start of the day.
        current_value:  Portfolio value that triggered the breach.
        loss_pct:       Realised loss as a fraction (e.g. 0.053 = 5.3%).
        limit_pct:      Configured limit that was exceeded.
    """

    def __init__(
        self,
        opening_value: float,
        current_value: float,
        loss_pct: float,
        limit_pct: float,
    ) -> None:
        self.opening_value = opening_value
        self.current_value = current_value
        self.loss_pct      = loss_pct
        self.limit_pct     = limit_pct
        super().__init__(
            f"Daily loss limit breached: portfolio fell {loss_pct:.2%} "
            f"(${opening_value:,.2f} -> ${current_value:,.2f}; "
            f"limit={limit_pct:.2%}). Trading halted for today."
        )


class DailyLimitGuard:
    """Tracks intraday portfolio value and raises DailyLimitBreached when the
    portfolio drops more than limit_pct from the day's opening value.

    Usage:
        guard = DailyLimitGuard(opening_value=10_000, limit_pct=0.05)
        guard.check(current_value)   # raises DailyLimitBreached if floor hit
        guard.reset(new_opening)     # call at midnight / start of new day
    """

    def __init__(self, opening_value: float, limit_pct: float = 0.05) -> None:
        if opening_value <= 0:
            raise ValueError(f"opening_value must be positive, got {opening_value}")
        if not (0 < limit_pct < 1):
            raise ValueError(f"limit_pct must be in (0, 1), got {limit_pct}")
        self._opening   = opening_value
        self._limit_pct = limit_pct
        self._floor     = opening_value * (1.0 - limit_pct)

    @property
    def opening_value(self) -> float:
        return self._opening

    @property
    def floor(self) -> float:
        """Minimum portfolio value before trading is halted."""
        return self._floor

    @property
    def limit_pct(self) -> float:
        return self._limit_pct

    def check(self, current_value: float) -> None:
        """Raise DailyLimitBreached if current_value has fallen to or below the floor."""
        if current_value <= self._floor:
            loss_pct = (self._opening - current_value) / self._opening
            raise DailyLimitBreached(
                opening_value=self._opening,
                current_value=current_value,
                loss_pct=loss_pct,
                limit_pct=self._limit_pct,
            )

    def reset(self, new_opening_value: float) -> None:
        """Reset for a new trading day with a fresh opening value."""
        if new_opening_value <= 0:
            raise ValueError(f"new_opening_value must be positive, got {new_opening_value}")
        self._opening = new_opening_value
        self._floor   = new_opening_value * (1.0 - self._limit_pct)
