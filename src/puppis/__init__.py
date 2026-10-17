"""Puppis -- the forward test: vela's strategies, run live against a paper account.

Puppis never reads market data itself (antlia does) and never re-implements a
strategy (vela's are imported). What it owns is the broker socket for orders,
the paper-only guard, and -- from M2 -- the journal.

Importing this package needs no SDK; `puppis.ibkr` loads ib_async when a
session is opened.
"""

from puppis.broker import Broker, Execution, Instrument, Position
from puppis.guard import NotPaper, require_paper

__all__ = ["Broker", "Execution", "Instrument", "NotPaper", "Position", "require_paper"]
