"""`IBKRClient` on `ib_async`: the only live module that touches the SDK.

`ib_async` is ib_insync's maintained successor (ib_insync stopped in 2024). It
is the current choice, not a permanent one: the user may replace it with a
client of their own on IBKR's `ibapi`, and that client implements the same
Protocol (`ibkr.IBKRClient`) instead of editing the adapter. The work done
here, and so the work a replacement owes, is:

- building SDK contract objects and asking the gateway to qualify them;
- switching market-data type -- 3 (delayed) for the band's centre, 1
  (realtime) for every snapshot, restored to 1 afterwards;
- flattening each ticker into a row under `ibkr.RAW`, values as sent:
  `-1.0` and `1.797e308` stay in, because the projection is where they
  become NULL.

The SDK module is passed in rather than imported, so the adapter's
`require()` produces a readable `MissingExtra` and a test can hand in fakes.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import ModuleType
from typing import Any

from antlia.live.ibkr import CONTRACT_FIELDS, GREEK_FIELDS, TICKER_FIELDS, ChainParams, Leg

#: IBKR's market-data types.
REALTIME, DELAYED = 1, 3


class IbAsyncClient:
    def __init__(self, ib: Any, sdk: ModuleType) -> None:
        self.ib = ib
        self.sdk = sdk

    def stock(self, symbol: str) -> Any:
        contract = self.sdk.Stock(symbol, "SMART", "USD")
        if not self.ib.qualifyContracts(contract):
            raise LookupError(f"ibkr does not recognise {symbol!r} as a US stock")
        return contract

    def chains(self, stock: Any) -> list[ChainParams]:
        params = self.ib.reqSecDefOptParams(stock.symbol, "", stock.secType, stock.conId)
        return [
            ChainParams(
                exchange=p.exchange,
                expirations=tuple(p.expirations),
                strikes=tuple(p.strikes),
                multiplier=getattr(p, "multiplier", ""),
                trading_class=getattr(p, "tradingClass", ""),
            )
            for p in params
        ]

    def options(self, symbol: str, chain: ChainParams, legs: Sequence[Leg]) -> list[Any]:
        contracts = [
            self.sdk.Option(
                symbol,
                expiry,
                strike,
                right,
                "SMART",
                multiplier=chain.multiplier,
                currency="USD",
                tradingClass=chain.trading_class,
            )
            for expiry, strike, right in legs
        ]
        return [c for c in self.ib.qualifyContracts(*contracts) if getattr(c, "conId", 0)]

    def delayed_price(self, stock: Any) -> float | None:
        self.ib.reqMarketDataType(DELAYED)
        try:
            [ticker] = self.ib.reqTickers(stock)
        finally:
            self.ib.reqMarketDataType(REALTIME)
        for price in (ticker.marketPrice(), ticker.close):
            if price == price and price > 0:  # not NaN, and set
                return float(price)
        return None

    def snapshot(self, contracts: Sequence[Any]) -> list[dict[str, Any]]:
        self.ib.reqMarketDataType(REALTIME)
        return [row(t) for t in self.ib.reqTickers(*contracts)]


def row(ticker: Any) -> dict[str, Any]:
    """One ticker as IBKR named its fields. Nothing renamed, nothing repaired."""
    contract = ticker.contract
    out: dict[str, Any] = {name: getattr(contract, name, None) for name in CONTRACT_FIELDS}
    out.update({name: getattr(ticker, name, None) for name in TICKER_FIELDS})
    greeks = getattr(ticker, "modelGreeks", None)
    for name in GREEK_FIELDS:
        value = getattr(greeks, name, None) if greeks is not None else None
        out[f"modelGreeks.{name}"] = None if value is None else float(value)
    return out
