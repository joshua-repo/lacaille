"""Data model for option legs and paired vertical spreads."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass
class OptionLeg:
    underlying: str
    strike: float
    right: str        # "C" or "P"
    expiry: dt.date
    position: float   # +N long, -N short
    unrealized_pnl: float


@dataclass
class Spread:
    underlying: str
    right: str
    expiry: dt.date
    long_strike: float
    short_strike: float
    unrealized_pnl: float

    @property
    def label(self) -> str:
        return f"{self.underlying} {self.long_strike:g}/{self.short_strike:g}"
