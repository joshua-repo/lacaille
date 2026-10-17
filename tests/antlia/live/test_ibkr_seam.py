"""The seam between the IBKR adapter and the SDK, held so the SDK can be swapped.

The user may replace `ib_async` with a client of their own on IBKR's `ibapi`.
These tests are what that client has to satisfy: the adapter needs nothing but
`IBKRClient`, and the raw column names -- which every recording is stored
under -- belong to the adapter, not to the SDK.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest

from antlia import auth, live
from antlia.live.sources import ibkr
from antlia.live.sources.ibasync import IbAsyncClient
from antlia.live.sources.ibkr import RAW, ChainParams, IBKRLive
from antlia.schema import OPTION_QUOTE
from tests.antlia.live.test_option_chain import FAR, NEAR, FakeIB, Option, Stock


class FakeClient:
    """An `IBKRClient` with no SDK behind it at all."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def stock(self, symbol):
        self.calls.append("stock")
        return ("STK", symbol)

    def chains(self, stock):
        self.calls.append("chains")
        return [ChainParams("SMART", (NEAR, FAR), (190.0, 200.0, 210.0), "100", "AAPL")]

    def options(self, symbol, chain, legs):
        self.calls.append("options")
        return [("OPT", *leg) for leg in legs]

    def delayed_price(self, stock):
        self.calls.append("delayed_price")
        return 200.0

    def snapshot(self, contracts):
        self.calls.append("snapshot")
        stamp = dt.datetime(2026, 10, 7, 19, 45, tzinfo=dt.UTC)
        rows = []
        for _, expiry, strike, right in contracts:
            row = dict.fromkeys(RAW)
            row.update(
                symbol="AAPL",
                lastTradeDateOrContractMonth=expiry,
                strike=strike,
                right=right,
                time=stamp,
                bid=3.0,
                ask=3.2,
            )
            rows.append(row)
        return rows


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient()

    @contextlib.contextmanager
    def session(*args, **kwargs):
        yield object()

    monkeypatch.setattr(auth, "session", session)
    monkeypatch.setattr(IBKRLive, "client", lambda self, session: client)
    return client


def test_the_adapter_needs_only_the_protocol(fake_client):
    snap = live.option_chain("AAPL", max_dte=20, rights="P")
    assert snap.table.column_names == [c.name for c in OPTION_QUOTE.columns]
    assert set(snap.table.column("strike").to_pylist()) == {190.0, 200.0, 210.0}
    assert fake_client.calls == ["stock", "chains", "delayed_price", "options", "snapshot"]


def test_the_adapter_module_imports_no_sdk():
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, antlia.live.sources.ibkr;"
            "print(sorted({'ib_async', 'ib_insync', 'ibapi'} & set(sys.modules)))",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.strip() == "[]"


def test_every_column_the_projection_reads_is_in_raw():
    read = set()
    for expression in IBKRLive().projection("option_quote").values():
        read |= set(re.findall(r'"([^"]+)"', expression))
    assert read - {"snapshot_at"} <= set(RAW)


def test_the_ib_async_client_fills_exactly_raw():
    ib = FakeIB()
    client = IbAsyncClient(ib, SimpleNamespace(Stock=Stock, Option=Option))  # type: ignore[arg-type]
    chain = next(c for c in client.chains(client.stock("AAPL")) if c.exchange == "SMART")
    listed = client.options("AAPL", chain, [(NEAR, 200.0, "C"), (NEAR, 260.0, "C")])
    assert len(listed) == 1  # 260 is listed but never trades
    [row] = client.snapshot(listed)
    assert tuple(row) == RAW


def test_raw_is_the_recorded_shape_and_must_not_drift():
    # Every recording in raw/ibkr/ is stored under these names. Changing one
    # orphans them; a replacement client maps onto these, not the reverse.
    assert ibkr.RAW[:3] == ("conId", "symbol", "lastTradeDateOrContractMonth")
    assert {"bid", "bidSize", "ask", "askSize", "time", "modelGreeks.delta"} <= set(ibkr.RAW)


def test_the_standard_class_wins_whatever_order_ibkr_lists_them_in():
    # Measured on SPY, 2026-10-17: two SMART entries, order varying per call.
    adjusted = ChainParams("SMART", ("20261120", "20261127"), (500.0, 600.0), "100", "2SPY")
    standard = ChainParams("SMART", ("20261019", "20261020"), tuple(range(400, 891)), "100", "SPY")
    other = ChainParams("CBOE", ("20261019",), (500.0,), "100", "SPY")
    for listing in ([adjusted, standard, other], [other, standard, adjusted]):
        assert ibkr.smart_chain(listing, "SPY") is standard


def test_without_a_class_named_for_the_symbol_the_fullest_listing_wins():
    thin = ChainParams("SMART", ("20261120",), (1.0,), "100", "XYZ1")
    full = ChainParams("SMART", ("20261120",), (1.0, 2.0, 3.0), "100", "XYZ2")
    assert ibkr.smart_chain([thin, full], "XYZ") is full
    assert ibkr.smart_chain([], "XYZ") is None
