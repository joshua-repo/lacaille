"""Live position pulls via antlia's account layer (read-only by
construction). antlia owns connections, credentials, pooling, client-id
allocation and rate limiting; this module only maps antlia's canonical
`Position`/`Instrument` onto pictor's `OptionLeg`/`EquityPosition`.

Two brokers are reachable, and they hold different things:

- **`ibkr`** -- the option book, via TWS / IB Gateway. Profiles are "live"
  (default) and "paper". This is the only source that feeds the spread
  charts, since it is the only one with options in it.
- **`trading212`** -- a cash equity account, via the T212 REST API. Profiles
  are "live" and "demo" (different hosts, different key pairs). It holds
  shares only, so it produces `EquityPosition`s and never reaches
  `pair_spreads`. The API key deliberately lacks the trading scope, so
  working orders come back empty; that is the intended posture, not a fault.

antlia is a core dependency, pinned to its `develop` branch -- pictor's CLI
has no other position source, so it isn't optional the way a single vendor
extra would be. The import is still deferred inside the functions so a caller
that only wants `pictor.pairing`/`pictor.charts` and feeds its own
`OptionLeg`s (IBKR MCP, a backtest, ...) never pays for it. Hosts, ports and
credentials are antlia's concern -- resolved from environment variables or
`~/.antlia/credentials.toml`, not from this module. See
https://github.com/joshua-repo/antlia (develop branch) `auth`/`account` docs.
"""

from __future__ import annotations

from pictor.models import EquityPosition, OptionLeg


def fetch_option_legs(source: str = "ibkr", profile: str = "live") -> list[OptionLeg]:
    """Pull open option positions for one account via antlia.

    `profile` picks which antlia-configured connection to use -- for `ibkr`,
    "live" (default; the only gateway actually running as of 2026-08-29 -- a
    dockerized IB Gateway, host port 4001) or "paper", if/when a paper
    gateway is running too. Legs missing an expiry, strike, or right (a
    malformed/partial contract) are dropped rather than passed through to
    fail pairing downstream.
    """
    from antlia import account
    from antlia.account.types import OPTION

    snapshot = account.snapshot(source, profile=profile)
    legs = []
    for p in snapshot.by_kind(OPTION):
        inst = p.instrument
        if inst.expiry is None or inst.strike is None or inst.right is None:
            continue
        legs.append(
            OptionLeg(
                underlying=inst.symbol,
                strike=inst.strike,
                right=inst.right,
                expiry=inst.expiry,
                position=p.quantity,
                unrealized_pnl=p.unrealized_pnl or 0.0,
            )
        )
    return legs


def fetch_equity_positions(
    source: str = "trading212", profile: str = "live"
) -> list[EquityPosition]:
    """Pull share holdings for one account via antlia.

    Works for any source antlia can snapshot -- Trading212 holds nothing but
    shares, and an IBKR account typically holds some alongside its options.
    `market_value` stays `None` where antlia could not pin down the scale
    between the instrument's quote currency and the account's; that is
    deliberate there, and passing the `None` through is better than inventing
    a number that may be 100x wrong.
    """
    from antlia import account
    from antlia.account.types import STOCK

    snapshot = account.snapshot(source, profile=profile)
    return [
        EquityPosition(
            symbol=p.instrument.symbol,
            quantity=p.quantity,
            price=p.market_price,
            market_value=p.market_value,
            unrealized_pnl=p.unrealized_pnl,
            currency=p.currency or snapshot.base_currency,
            source=snapshot.source,
        )
        for p in snapshot.by_kind(STOCK)
    ]


def fetch_positions_live(profile: str = "live") -> list[OptionLeg]:
    """IBKR option legs. Kept as the name the charts and skill docs use."""
    return fetch_option_legs("ibkr", profile)
