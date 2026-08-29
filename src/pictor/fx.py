"""Exchange rates, from antlia.

pictor no longer owns a provider chain. `antlia.fx` does -- the yfinance and
Frankfurter sources, the USD pivot, the disk cache and the staleness flag all
live there now, alongside the account layer that produced the figures being
converted. This module is what is left: the one policy decision that is
pictor's to make rather than antlia's.

**That decision is what to do when there are no rates at all.** antlia raises
`RatesUnavailable`, which is right for a library -- "I could not answer" is not
the same as "the answer is nothing", and a backtest silently pricing a
portfolio at no rate would be a serious bug. A dashboard's policy is the
opposite: a page without a currency picker is still a page, so the failure is
absorbed here and every caller downstream sees `None` and falls back to native
currencies.

Everything else is a re-export, deliberately, so the rest of pictor keeps
importing `pictor.fx` and never has to know which library answered.
"""

from __future__ import annotations

from antlia.fx import DEFAULT_CURRENCIES, PIVOT, RateTable

__all__ = ["DEFAULT_CURRENCIES", "PIVOT", "RateTable", "fetch_rates"]


def fetch_rates(currencies: tuple[str, ...] = DEFAULT_CURRENCIES) -> RateTable | None:
    """The best rate table antlia can produce, or `None` if it has none.

    A table that came back stale (every live source failed, this is the last
    one on disk) is *not* a failure and is passed through with its `stale` flag
    intact -- the dashboard says so on the page and lets the reader judge.
    Only "nothing at all, not even a stale table" becomes `None`.
    """
    from antlia import fx
    from antlia.auth.errors import AuthError

    try:
        return fx.rates(currencies)
    except AuthError:
        # `RatesUnavailable` subclasses `ConnectionFailed` subclasses
        # `AuthError`, which is the contract antlia documents. Deliberately not
        # a bare `except Exception`: an unexpected error out of antlia is a bug
        # worth seeing, not a missing feature to paper over.
        return None
