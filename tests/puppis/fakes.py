"""Stand-ins for the gateway: an `ib` object for the adapter, a `Broker` for the CLI."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from types import SimpleNamespace

from puppis.broker import Execution, Instrument, Position

STARTUP_NONE = object()


def option(con_id=11, symbol="SPY", expiry="20261120", strike=550.0, right="P"):
    return SimpleNamespace(
        conId=con_id,
        symbol=symbol,
        secType="OPT",
        lastTradeDateOrContractMonth=expiry,
        strike=strike,
        right=right,
        multiplier="100",
    )


def stock(con_id=756733, symbol="SPY"):
    return SimpleNamespace(
        conId=con_id,
        symbol=symbol,
        secType="STK",
        lastTradeDateOrContractMonth="",
        strike=0.0,
        right="",
        multiplier="",
    )


@dataclass
class FakeIB:
    """The few `ib_async.IB` calls the adapter makes, recording every one."""

    accounts: list[str] = field(default_factory=lambda: ["DU1234567"])
    calls: list[str] = field(default_factory=list)
    connected_with: dict[str, object] = field(default_factory=dict)

    def connect(self, host, port, **kwargs):
        self.calls.append("connect")
        self.connected_with = {"host": host, "port": port, **kwargs}

    def managedAccounts(self):
        self.calls.append("managedAccounts")
        return list(self.accounts)

    def disconnect(self):
        self.calls.append("disconnect")

    def reqPositions(self):
        self.calls.append("reqPositions")
        return [
            SimpleNamespace(
                account=self.accounts[0], contract=option(), position=-2.0, avgCost=310.5
            ),
            SimpleNamespace(
                account=self.accounts[0], contract=stock(), position=100.0, avgCost=548.2
            ),
        ]

    def reqExecutions(self):
        self.calls.append("reqExecutions")
        stamp = dt.datetime(2026, 10, 17, 19, 45, 3, tzinfo=dt.UTC)
        reported = SimpleNamespace(
            contract=option(),
            execution=SimpleNamespace(
                execId="0001.01",
                permId=77,
                orderRef="p-1",
                acctNumber=self.accounts[0],
                side="SLD",
                shares=2.0,
                price=3.1,
                time=stamp,
            ),
            commissionReport=SimpleNamespace(execId="0001.01", commission=1.3),
        )
        pending = SimpleNamespace(
            contract=option(con_id=12, strike=545.0),
            execution=SimpleNamespace(
                execId="0001.02",
                permId=77,
                orderRef="p-1",
                acctNumber=self.accounts[0],
                side="BOT",
                shares=2.0,
                price=2.4,
                time=stamp,
            ),
            # ib_async's placeholder until IBKR's report arrives.
            commissionReport=SimpleNamespace(execId="", commission=0.0),
        )
        return [reported, pending]


def fake_sdk(ib: FakeIB) -> SimpleNamespace:
    return SimpleNamespace(IB=lambda: ib, StartupFetchNONE=STARTUP_NONE)


@dataclass
class FakeBroker:
    """A `Broker` with no SDK at all, for the CLI."""

    accounts_: list[str] = field(default_factory=lambda: ["DU1234567"])
    refuse: Exception | None = None
    closed: bool = False

    def connect(self):
        if self.refuse is not None:
            raise self.refuse

    def close(self):
        self.closed = True

    def accounts(self):
        return list(self.accounts_)

    def positions(self):
        spy = Instrument(11, "SPY", "OPT", dt.date(2026, 11, 20), 550.0, "P", 100.0)
        return [Position("DU1234567", spy, -2.0, 310.5)]

    def executions(self):
        spy = Instrument(11, "SPY", "OPT", dt.date(2026, 11, 20), 550.0, "P", 100.0)
        stamp = dt.datetime(2026, 10, 17, 19, 45, 3, tzinfo=dt.UTC)
        return [Execution("0001.01", 77, "p-1", "DU1234567", spy, "SLD", 2.0, 3.1, stamp, 1.3)]
