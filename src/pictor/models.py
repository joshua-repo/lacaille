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


@dataclass
class EquityPosition:
    """One share/ETF holding.

    Trading212 is a cash equity account -- it has no options at all, so its
    positions cannot be `OptionLeg`s and never reach `pair_spreads`. Money
    fields are in the *account's* currency; `price` is in the instrument's,
    which is not always the same one (a London line quotes GBX against a GBP
    account). That split is antlia's finding, kept rather than flattened.
    """

    symbol: str
    quantity: float
    price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    currency: str
    source: str
    #: `market_value` restated in the account's base currency, using the rate
    #: the *broker itself* reported alongside that currency's balance. It
    #: exists because a multi-currency account cannot be ranked or summed
    #: without it -- 772,600 JPY outranks 10,893 USD on the raw number and is
    #: worth less than half as much. `None` when no rate was reported, in
    #: which case the position simply cannot take part in a comparison.
    base_value: float | None = None
    base_currency: str = ""
