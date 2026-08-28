"""Live option position pull via ib_insync (requires TWS or IB Gateway
running locally with the API enabled -- default port 7497 for paper, 7496
for live trading).

ib_insync is an optional dependency (`pip install pictor[ibkr]`); the import
is deferred so the rest of the package works without it installed.
"""

from __future__ import annotations

import datetime as dt

from pictor.models import OptionLeg


def fetch_positions_live(host: str = "127.0.0.1", port: int = 7497, client_id: int = 7) -> list[OptionLeg]:
    """Pull open option positions from IBKR via ib_insync.

    Note: ib_insync's `positions()` call doesn't return live unrealized P&L;
    pull that separately via `reqPnLSingle` per contract, or read it off
    `portfolio()` instead of `positions()`.
    """
    from ib_insync import IB

    ib = IB()
    ib.connect(host, port, clientId=client_id)
    legs = []
    for p in ib.positions():
        c = p.contract
        if c.secType != "OPT":
            continue
        legs.append(
            OptionLeg(
                underlying=c.symbol,
                strike=float(c.strike),
                right=c.right,
                expiry=dt.datetime.strptime(c.lastTradeDateOrContractMonth, "%Y%m%d").date(),
                position=p.position,
                unrealized_pnl=0.0,
            )
        )
    ib.disconnect()
    return legs
