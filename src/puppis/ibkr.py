"""`Broker` on IBKR through `ib_async` -- the only puppis module with the SDK.

**puppis's own socket, and a writable one.** antlia's sessions are for market
data; this one is for orders and their reports, so it connects with
`readonly=False` and a fixed client id of its own (default 100, below the
range antlia allocates from 900). It holds no credential: host and port come
from `antlia.auth.credential("ibkr", profile)`, and the gateway is already
logged in.

**The guard runs first.** The connect asks ib_async to sync nothing
(`StartupFetchNONE`) -- it still requests positions, a read it always makes --
so no order or account state is pulled before `require_paper` has looked at
the managed accounts. A non-paper account disconnects and raises.

**Nothing above this file sees an SDK object.** Positions and executions are
converted to `broker.Position` / `broker.Execution` here, which is what a
replacement client on IBKR's `ibapi` has to produce too.
"""

from __future__ import annotations

import datetime as dt
import importlib
from types import ModuleType
from typing import Any

from antlia import auth
from puppis.broker import Execution, Instrument, Position
from puppis.guard import require_paper

#: Below antlia's auto-allocated range (900+). Two puppis processes on one
#: gateway would evict each other; give a second one its own id.
CLIENT_ID = 100


def load_sdk() -> ModuleType:
    try:
        return importlib.import_module("ib_async")
    except ImportError as exc:
        raise RuntimeError("puppis needs the IBKR SDK: uv sync --extra ibkr") from exc


class IbkrBroker:
    def __init__(
        self,
        profile: str = "paper",
        *,
        client_id: int = CLIENT_ID,
        timeout: float = 10.0,
        sdk: ModuleType | None = None,
    ) -> None:
        self.profile = profile
        self.client_id = client_id
        self.timeout = timeout
        self.sdk = sdk
        self.ib: Any = None

    def connect(self) -> None:
        cred = auth.credential("ibkr", self.profile)
        host = str(cred.get("host") or "127.0.0.1")
        port = cred.get("port")
        if not port:
            raise RuntimeError(
                f"no port for ibkr:{self.profile}; set [ibkr.{self.profile}] port in "
                "~/.antlia/credentials.toml (the gateway's paper API is 4002)"
            )
        sdk = self.sdk or load_sdk()
        ib = sdk.IB()
        ib.connect(
            host,
            int(port),
            clientId=self.client_id,
            readonly=False,
            timeout=self.timeout,
            fetchFields=sdk.StartupFetchNONE,
        )
        try:
            require_paper(list(ib.managedAccounts()))
        except Exception:
            ib.disconnect()
            raise
        self.ib = ib

    def close(self) -> None:
        if self.ib is not None:
            self.ib.disconnect()
            self.ib = None

    def __enter__(self) -> IbkrBroker:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def accounts(self) -> list[str]:
        return list(self.session().managedAccounts())

    def positions(self) -> list[Position]:
        return [
            Position(
                account=p.account,
                instrument=instrument(p.contract),
                quantity=float(p.position),
                avg_cost=float(p.avgCost),
            )
            for p in self.session().reqPositions()
        ]

    def executions(self) -> list[Execution]:
        return [execution(f) for f in self.session().reqExecutions()]

    def session(self) -> Any:
        if self.ib is None:
            raise RuntimeError("not connected; call connect() first")
        return self.ib


def instrument(contract: Any) -> Instrument:
    """IBKR's contract as puppis's `Instrument`. Empty fields become None."""
    expiry = str(getattr(contract, "lastTradeDateOrContractMonth", "") or "")
    strike = float(getattr(contract, "strike", 0.0) or 0.0)
    right = str(getattr(contract, "right", "") or "")[:1].upper()
    multiplier = str(getattr(contract, "multiplier", "") or "")
    return Instrument(
        con_id=int(contract.conId),
        symbol=str(contract.symbol),
        sec_type=str(contract.secType),
        expiration=dt.datetime.strptime(expiry[:8], "%Y%m%d").date() if len(expiry) >= 8 else None,
        strike=strike or None,
        right=right or None,
        multiplier=float(multiplier) if multiplier else 1.0,
    )


def execution(fill: Any) -> Execution:
    """One ib_async `Fill` as an `Execution`. The commission rides along if known.

    ib_async gives every fill a commission report, empty (no `execId`) until
    IBKR's report for that execution arrives -- so emptiness, not zero, means
    unknown.
    """
    ex = fill.execution
    report: Any = getattr(fill, "commissionReport", None)
    known = report is not None and getattr(report, "execId", "") == ex.execId
    time = ex.time if ex.time.tzinfo else ex.time.replace(tzinfo=dt.UTC)
    return Execution(
        exec_id=ex.execId,
        perm_id=int(ex.permId),
        order_ref=str(ex.orderRef or ""),
        account=ex.acctNumber,
        instrument=instrument(fill.contract),
        side=ex.side,
        quantity=float(ex.shares),
        price=float(ex.price),
        time=time.astimezone(dt.UTC),
        commission=float(report.commission) if known else None,
    )
