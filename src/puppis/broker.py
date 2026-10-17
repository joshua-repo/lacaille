"""What puppis asks of a broker, in puppis's own types.

Everything above the adapter -- the loop, the journal, reconciliation --
depends on `Broker` and on the dataclasses here, never on an SDK object. That
is the seam that lets the user replace `ib_async` with a client of their own
on IBKR's `ibapi` and check the two against each other on the same paper
account.

The Protocol holds only what is implemented. M0 reads: who the accounts are,
what is held, what filled today. Placing, cancelling and the event stream
arrive at M3 as methods here, not as a second interface.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Instrument:
    """Which contract, as IBKR identifies it, plus the fields a person reads.

    `con_id` is the identity; the rest is description. Options carry
    `expiration`, `strike` and `right` ('C' or 'P'); a stock leaves them None.
    """

    con_id: int
    symbol: str
    sec_type: str
    expiration: dt.date | None = None
    strike: float | None = None
    right: str | None = None
    multiplier: float = 1.0


@dataclass(frozen=True, slots=True)
class Position:
    account: str
    instrument: Instrument
    #: Signed: negative is short.
    quantity: float
    #: IBKR's average cost, per unit *including* the multiplier, as it reports it.
    avg_cost: float


@dataclass(frozen=True, slots=True)
class Execution:
    """One fill of one leg, as the broker reported it."""

    exec_id: str
    perm_id: int
    #: puppis's own order id, sent as IBKR's `orderRef`. Empty for an order
    #: puppis did not place.
    order_ref: str
    account: str
    instrument: Instrument
    #: 'BOT' or 'SLD', IBKR's words.
    side: str
    quantity: float
    price: float
    time: dt.datetime
    #: None until the commission report for this `exec_id` has arrived.
    commission: float | None = None


class Broker(Protocol):
    def connect(self) -> None:
        """Open the session. The guard runs on `accounts()` before anything else."""

    def close(self) -> None: ...

    def accounts(self) -> list[str]:
        """Every account this session manages."""

    def positions(self) -> list[Position]: ...

    def executions(self) -> list[Execution]:
        """Today's fills, as the broker keeps them (it re-sends them on reconnect)."""
