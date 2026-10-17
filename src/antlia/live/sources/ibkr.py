"""IBKR as a live source: a slice of an option chain, quoted now.

Read-only by what it asks, not by a broker block: the session comes from
`auth.session("ibkr")` (`readonly=True`, which skips the order sync and
enforces nothing), and the only requests made are contract lookups and
market-data snapshots.

The raw frame is one row per contract under **IBKR's own attribute names**
-- `lastTradeDateOrContractMonth`, `bidSize`, `modelGreeks.delta` -- with
IBKR's own sentinels left in. The projection is where `"20261016"` becomes a
date and `-1.0` becomes NULL.

## The seam: no SDK in this file

Everything that talks to the gateway goes through `IBKRClient`, a Protocol of
five calls, and contracts are opaque handles here. `ibasync.py` implements it
on `ib_async`; a client of the user's own, on IBKR's `ibapi`, would implement
the same five calls and change nothing in this file. What such a client must
keep is `RAW`: every recording in `raw/ibkr/` is in those column names and
the projection reads them, so they are a contract, not an SDK detail.

## Facts measured against the user's gateway (2026-08-29)

- **OPRA is on, so option quotes arrive.** Chain structure
  (`reqSecDefOptParams`) is free.
- **`modelGreeks` arrive as None.** Greeks need an underlying price and the
  account has no US equity realtime bundle; the error names the *stock's*
  feed, not OPRA. The columns are kept so they fill the day that changes.
- **The underlying is delayed.** The default strike band is centred on a
  delayed (`reqMarketDataType(3)`) price, which is plenty for choosing strikes
  and is never written into a quote row.
- **`bid`/`ask` of -1.0 is IBKR's "no quote"**, seen with the market closed;
  whether it appears in regular hours is unconfirmed. Either way it reads as
  NULL.

Not yet run against a live gateway: the request sequence follows the SDK's
documented API and is covered by a fake in the tests.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from antlia import auth
from antlia.live.base import LiveSource

NY = ZoneInfo("America/New_York")

#: Contracts per `reqTickers` call. Each snapshot holds a market-data line
#: until it answers, and the default allowance is 100 lines.
BATCH = 40

#: More than this is a scan, not a slice, and should be narrowed.
MAX_CONTRACTS = 400

#: The default strike band around the underlying: +/- 15%.
BAND = 0.15

#: The raw columns, in three parts: the contract's fields, the quote's, and the
#: model greeks' (flattened as `modelGreeks.<name>`). A client fills each row
#: under exactly these names, None where it has nothing.
CONTRACT_FIELDS = (
    "conId",
    "symbol",
    "lastTradeDateOrContractMonth",
    "strike",
    "right",
    "multiplier",
    "exchange",
    "currency",
    "localSymbol",
    "tradingClass",
)
TICKER_FIELDS = ("time", "bid", "bidSize", "ask", "askSize", "last", "lastSize", "volume", "close")
GREEK_FIELDS = (
    "impliedVol",
    "delta",
    "gamma",
    "vega",
    "theta",
    "undPrice",
    "optPrice",
    "pvDividend",
)

RAW = (*CONTRACT_FIELDS, *TICKER_FIELDS, *(f"modelGreeks.{name}" for name in GREEK_FIELDS))


@dataclass(frozen=True, slots=True)
class ChainParams:
    """One exchange's listing of a chain: what `reqSecDefOptParams` answers."""

    exchange: str
    expirations: tuple[str, ...]
    strikes: tuple[float, ...]
    multiplier: str
    trading_class: str


#: One option to look up: (expiration as IBKR's YYYYMMDD, strike, right).
Leg = tuple[str, float, str]


class IBKRClient(Protocol):
    """Everything this source asks of a gateway. Contracts are opaque here."""

    def stock(self, symbol: str) -> Any:
        """The qualified US stock. Raises LookupError if IBKR does not know it."""

    def chains(self, stock: Any) -> list[ChainParams]:
        """Every exchange's listing of the stock's option chain."""

    def options(self, symbol: str, chain: ChainParams, legs: Sequence[Leg]) -> list[Any]:
        """The legs that really exist, qualified. Combinations that do not are dropped."""

    def delayed_price(self, stock: Any) -> float | None:
        """A delayed price, enough to centre a strike band on. None if there is none."""

    def snapshot(self, contracts: Sequence[Any]) -> list[dict[str, Any]]:
        """One realtime snapshot per contract, as rows under `RAW`."""


def _double(column: str) -> str:
    return f'TRY_CAST("{column}" AS DOUBLE)'


def _price(column: str) -> str:
    """Non-negative and finite, else NULL: drops -1, 1.797e308 and NaN alike."""
    x = _double(column)
    return f"CASE WHEN {x} >= 0 AND {x} < 1e300 THEN {x} END"


def _signed(column: str) -> str:
    """Finite, else NULL. A delta or theta may be negative."""
    x = _double(column)
    return f"CASE WHEN isfinite({x}) AND abs({x}) < 1e300 THEN {x} END"


def smart_chain(chains: Sequence[ChainParams], symbol: str) -> ChainParams | None:
    """The SMART listing to trade, out of every exchange-and-class IBKR returns.

    IBKR lists a chain per exchange **and per trading class**, in no fixed
    order. SPY has two SMART entries: class `SPY` (the chain) and `2SPY`
    (adjusted contracts, two expirations). Taking the first one returned 0
    rows on some calls and not others. The standard class is the one named
    for the symbol; failing that, the fullest listing.
    """
    smart = [c for c in chains if c.exchange == "SMART"]
    for chain in smart:
        if chain.trading_class == symbol:
            return chain
    return max(smart, key=lambda c: len(c.strikes), default=None)


def choose_expirations(
    listed: Sequence[str],
    today: dt.date,
    wanted: Sequence[str | dt.date] | None,
    min_dte: int | None,
    max_dte: int | None,
) -> list[str]:
    """IBKR's `YYYYMMDD` strings, filtered by an explicit list or a DTE band."""
    chosen = []
    asked: set[dt.date] = set()
    if wanted is not None:
        asked = {(w if isinstance(w, dt.date) else dt.date.fromisoformat(str(w))) for w in wanted}
    for raw in sorted(listed):
        expiry = dt.datetime.strptime(raw, "%Y%m%d").date()
        if wanted is not None and expiry not in asked:
            continue
        dte = (expiry - today).days
        if dte < 0:
            continue
        if min_dte is not None and dte < min_dte:
            continue
        if max_dte is not None and dte > max_dte:
            continue
        chosen.append(raw)
    return chosen


class IBKRLive(LiveSource):
    name = "ibkr"
    auth_source = "ibkr"
    extra = "ibkr"
    package = "ib_async"
    datasets = frozenset({"option_quote"})

    def client(self, session: Any) -> IBKRClient:
        """The one place a session becomes an `IBKRClient`. Swap the SDK here."""
        from antlia.live.sources.ibasync import IbAsyncClient

        return IbAsyncClient(session, self.require("ib_async"))

    def fetch(self, dataset: str, symbol: str, **options: Any) -> Any:
        if dataset != "option_quote":
            raise ValueError(f"{self.name} cannot serve {dataset!r}")
        from antlia.live.engine import pa

        asked = dt.datetime.now(dt.UTC)
        today = asked.astimezone(NY).date()

        with auth.session(self.auth_source, options.get("profile")) as session:
            client = self.client(session)
            underlying = client.stock(symbol)
            chain = smart_chain(client.chains(underlying), symbol)
            if chain is None:
                raise LookupError(f"ibkr lists no SMART option chain for {symbol!r}")

            expirations = choose_expirations(
                chain.expirations,
                today,
                options.get("expirations"),
                options.get("min_dte"),
                options.get("max_dte"),
            )
            band = options.get("strikes") or self._band(client, underlying, symbol)
            strikes = [k for k in sorted(chain.strikes) if band[0] <= k <= band[1]]
            rights = [r for r in "CP" if r in options.get("rights", "CP").upper()]

            legs = [(e, k, r) for e in expirations for k in strikes for r in rights]
            if len(legs) > MAX_CONTRACTS:
                raise ValueError(
                    f"{len(legs)} contracts is a scan, not a slice (limit {MAX_CONTRACTS}); "
                    "narrow expirations, the DTE band or strikes=(lo, hi)"
                )
            if not legs:
                return None

            # The union of strikes is wider than any one expiration's: a
            # combination that does not exist comes back unqualified.
            listed = client.options(symbol, chain, legs)
            rows: list[dict[str, Any]] = []
            for i in range(0, len(listed), BATCH):
                rows.extend(client.snapshot(listed[i : i + BATCH]))

        if not rows:
            return None
        frame = pa.Table.from_pylist(rows)
        stamp = pa.array([asked] * frame.num_rows, type=pa.timestamp("us", tz="UTC"))
        return frame.append_column("snapshot_at", stamp)

    def _band(self, client: IBKRClient, underlying: Any, symbol: str) -> tuple[float, float]:
        """+/- BAND around a delayed underlying price. Delayed is enough to pick strikes."""
        price = client.delayed_price(underlying)
        if price is None:
            raise LookupError(
                f"no price for {symbol} to centre a strike band on; pass strikes=(lo, hi)"
            )
        return price * (1 - BAND), price * (1 + BAND)

    def projection(self, dataset: str) -> dict[str, str]:
        return {
            "date": "(\"snapshot_at\" AT TIME ZONE 'America/New_York')::DATE",
            "snapshot_at": '"snapshot_at"',
            "stamp": 'TRY_CAST("time" AS TIMESTAMPTZ)',
            "symbol": '"symbol"',
            "expiration": "strptime(\"lastTradeDateOrContractMonth\", '%Y%m%d')::DATE",
            "strike": _double("strike"),
            "right": 'upper(left("right", 1))',
            "bid": _price("bid"),
            "bid_size": _price("bidSize"),
            "ask": _price("ask"),
            "ask_size": _price("askSize"),
            "last": _price("last"),
            "volume": _price("volume"),
            "iv": _price("modelGreeks.impliedVol"),
            "delta": _signed("modelGreeks.delta"),
            "gamma": _signed("modelGreeks.gamma"),
            "vega": _signed("modelGreeks.vega"),
            "theta": _signed("modelGreeks.theta"),
            "underlying_price": _price("modelGreeks.undPrice"),
        }
