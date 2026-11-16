"""Inclusive periods and presentation-only percentage changes."""
from datetime import date, timedelta
from decimal import Decimal


def previous_period(start: date, end: date) -> tuple[date, date]:
    if start > end or (end - start).days > 3660:
        raise ValueError('Use an ordered period of at most ten years')
    try:
        previous_end = start - timedelta(days=1)
        return previous_end - (end - start), previous_end
    except OverflowError as error:
        raise ValueError('Previous period is outside supported dates') from error


def percentage_change(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return float(round(Decimal(current - previous) / abs(Decimal(previous)) * 100, 2))
