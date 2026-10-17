"""Paper only: the check that matters, because nothing else stops an order.

The gateway runs with its Read-Only API off so that puppis can trade, and a
client's `readonly=True` blocks nothing. So the one guarantee that puppis never
trades a live account is this check, on puppis's own socket, before it does
anything with the session. IBKR's paper accounts are the ones starting `DU`.
"""

from __future__ import annotations

from collections.abc import Sequence

PAPER_PREFIX = "DU"


class NotPaper(RuntimeError):
    """A session manages an account that is not a paper account."""


def require_paper(accounts: Sequence[str]) -> list[str]:
    """The accounts, if every one is paper. Raises `NotPaper` otherwise.

    An empty list is refused too: a gateway still logging in manages no
    accounts, and "nothing to check" must not read as "checked".
    """
    if not accounts:
        raise NotPaper("the session manages no accounts (is the gateway still logging in?)")
    live = [a for a in accounts if not a.startswith(PAPER_PREFIX)]
    if live:
        raise NotPaper(
            f"refusing to run: {', '.join(live)} is not a paper account "
            f"(paper accounts start {PAPER_PREFIX}). Check the port: paper is 4002."
        )
    return list(accounts)
