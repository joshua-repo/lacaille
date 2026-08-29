"""Per-account overviews -- the data behind the dashboard's Accounts view.

One `AccountOverview` per broker account, built from a single antlia snapshot
each, so the page can show what an account is worth, what it holds, and how
much margin headroom is left, next to the spread views of the same positions.

Three things this module refuses to do, all for the same reason -- a number
that is quietly wrong is worse than one that is absent:

- **No cross-account totals.** The IBKR account is USD and the Trading212 one
  is GBP. Summing them needs an FX rate at a stated time, which is a market
  data question this layer has no business answering. Each account is
  reported in its own currency and they are never added up.
- **No invented fields.** Trading212 is a cash account with no margin at all,
  so its margin fields stay `None` and the view omits that panel rather than
  rendering zeros that look like "no headroom used".
- **A failure is a value, not an exception.** One unreachable broker (gateway
  down, key expired) must not cost you the view of the other, so the error
  text rides along on the overview and gets rendered as a card.

The snapshot is taken once per account and both the option legs and the
equity holdings come out of it -- the charts and this view share a pull rather
than each opening their own connection.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from pictor.models import EquityPosition, OptionLeg

#: The accounts the CLI reads when it is not told otherwise: (source, profile).
#: IBKR is where the options live; Trading212 is cash equity only.
DEFAULT_ACCOUNTS: tuple[tuple[str, str], ...] = (("ibkr", "live"), ("trading212", "live"))

@dataclass
class CurrencyRow:
    """One currency inside a multi-currency account.

    IBKR reports a `BASE` rollup alongside the real currencies; that one is
    filtered out here, because it is a consolidated view rather than a
    currency and including it double-counts everything.
    """

    currency: str
    cash: float | None
    net_liquidation: float | None
    unrealized_pnl: float | None
    exchange_rate: float | None


@dataclass
class AccountOverview:
    """Everything the dashboard says about one account at one instant."""

    source: str
    profile: str
    account: str = ""
    currency: str = ""
    as_of: dt.datetime | None = None

    net_liquidation: float | None = None
    cash: float | None = None
    unrealized_pnl: float | None = None
    realized_pnl: float | None = None

    # Margin: present for IBKR, absent for a cash account like Trading212.
    maintenance_margin: float | None = None
    excess_liquidity: float | None = None
    buying_power: float | None = None
    cushion: float | None = None
    utilisation: float | None = None

    option_count: int = 0
    equity_count: int = 0
    currencies: list[CurrencyRow] = field(default_factory=list)
    holdings: list[EquityPosition] = field(default_factory=list)
    option_legs: list[OptionLeg] = field(default_factory=list)

    #: Endpoints the credential is not scoped for -- T212 reports its missing
    #: trading scope this way. Worth showing: it explains an empty orders list.
    unavailable: list[str] = field(default_factory=list)
    #: Set when the account could not be read at all; every other field is then
    #: at its default and the view renders an error card instead of numbers.
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def has_margin(self) -> bool:
        return self.maintenance_margin is not None or self.excess_liquidity is not None


def _first(*values: float | None) -> float | None:
    """The first value that is actually present.

    Not `a or b` -- a real 0.0 cash balance is a fact, and `or` would step
    over it and report the fallback instead.
    """
    for value in values:
        if value is not None:
            return value
    return None


def _holding(position, snap, rates: dict[str, float]) -> EquityPosition:
    """One share line, with its value also restated in the account's currency."""
    currency = position.currency or snap.base_currency
    rate = 1.0 if currency == snap.base_currency else rates.get(currency)
    value = position.market_value
    return EquityPosition(
        symbol=position.instrument.symbol,
        quantity=position.quantity,
        price=position.market_price,
        market_value=value,
        unrealized_pnl=position.unrealized_pnl,
        currency=currency,
        source=snap.source,
        base_value=value * rate if value is not None and rate is not None else None,
        base_currency=snap.base_currency,
    )


def fetch_overview(source: str, profile: str = "live") -> AccountOverview:
    """One account, or an overview carrying the reason it could not be read."""
    from antlia import account
    from antlia.account.types import BASE, OPTION, STOCK

    try:
        snap = account.snapshot(source, profile=profile)
    except Exception as exc:  # antlia raises per-vendor auth/connection errors
        return AccountOverview(
            source=source, profile=profile, error=f"{type(exc).__name__}: {exc}"
        )

    margin = snap.margin
    # The broker's own consolidated view where it publishes one (IBKR's BASE
    # row), else the balance in the account's base currency.
    rollup = snap.balance(BASE) or snap.balance(snap.base_currency)

    options = snap.by_kind(OPTION)
    legs = [
        OptionLeg(
            underlying=p.instrument.symbol,
            strike=p.instrument.strike,
            right=p.instrument.right,
            expiry=p.instrument.expiry,
            position=p.quantity,
            unrealized_pnl=p.unrealized_pnl or 0.0,
        )
        for p in options
        if p.instrument.expiry and p.instrument.strike is not None and p.instrument.right
    ]

    # The broker's own rate per currency, as of this snapshot. Nothing here
    # invents an FX rate: a currency the broker did not price simply gets no
    # base value, and drops to the bottom of the ranking instead of being
    # compared on a raw number that means something else.
    rates = {b.currency: b.exchange_rate for b in snap.balances if b.exchange_rate is not None}

    stocks = snap.by_kind(STOCK)
    holdings = sorted(
        (_holding(p, snap, rates) for p in stocks),
        key=lambda h: abs(h.base_value if h.base_value is not None else 0.0),
        reverse=True,
    )

    return AccountOverview(
        source=snap.source,
        profile=profile,
        account=snap.account,
        currency=snap.base_currency,
        as_of=snap.as_of,
        net_liquidation=_first(
            margin.net_liquidation if margin else None,
            rollup.net_liquidation if rollup else None,
        ),
        cash=_first(
            margin.total_cash if margin else None,
            rollup.cash if rollup else None,
        ),
        unrealized_pnl=rollup.unrealized_pnl if rollup else None,
        realized_pnl=rollup.realized_pnl if rollup else None,
        maintenance_margin=margin.maintenance_margin if margin else None,
        excess_liquidity=margin.excess_liquidity if margin else None,
        buying_power=margin.buying_power if margin else None,
        cushion=margin.cushion if margin else None,
        utilisation=margin.utilisation if margin else None,
        option_count=len(options),
        equity_count=len(stocks),
        currencies=[
            CurrencyRow(
                currency=b.currency,
                cash=b.cash,
                net_liquidation=b.net_liquidation,
                unrealized_pnl=b.unrealized_pnl,
                exchange_rate=b.exchange_rate,
            )
            for b in snap.balances
            if b.currency != BASE
        ],
        # Every holding, ranked. How many of them a view shows is that view's
        # decision, not this layer's -- capping here silently shortened
        # `pictor positions` to 12 of 16 lines.
        holdings=holdings,
        option_legs=legs,
        unavailable=list(snap.vendor.get("unavailable") or ()),
    )


def fetch_overviews(
    accounts: tuple[tuple[str, str], ...] | None = None,
) -> list[AccountOverview]:
    """Every configured account, read one after another.

    Sequential on purpose: `ib_insync` drives an asyncio event loop and is not
    a library to call from an arbitrary worker thread, and two accounts is not
    a latency problem worth taking that risk for. `enrich_tickers` parallelises
    because yfinance over HTTP genuinely is one.
    """
    return [fetch_overview(source, profile) for source, profile in (accounts or DEFAULT_ACCOUNTS)]
