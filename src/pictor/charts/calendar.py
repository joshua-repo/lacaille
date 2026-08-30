"""Calendar-grid view of vertical spread expiries -- an alternative to the
Gantt view in `pictor.charts.gantt`, organized as a month calendar with a
chip per spread on its expiry date. Ships a native (non-Plotly) Gantt view,
a table view and an accounts view alongside it, the first three driven by the
same underlying-ticker filter, so this one page covers every way of looking at
the same book.

The Accounts view is the odd one out: it is per *account* rather than per
spread (so the ticker filter does not apply to it), and it is fed by
`pictor.accounts.AccountOverview` objects rather than by `Spread`s. Accounts
in different currencies are shown side by side and never summed -- see that
module for why.

Encoding:
- Chip/bar color: P&L sign (status good/critical -- a state, not identity).
- Amber ring/band: spread is inside its per-ticker decision zone right now.
- Diamond badge (categorical orange): earnings date falls before expiry.
- Star badge (categorical yellow): a headline in the last few days.

No external assets (fonts/JS libs) -- the page is fully self-contained and
works offline, unlike the Plotly-based Gantt view which pulls plotly.js from
a CDN.
"""

from __future__ import annotations

import datetime as dt
import json
import warnings
from pathlib import Path

from antlia.fx import RateTable

from pictor.accounts import AccountOverview
from pictor.charts.gantt import DECISION_ZONE_DAYS
from pictor.enrichment import enrich_tickers
from pictor.models import Spread

#: How many holdings the Accounts card lists before it stops. A presentation
#: limit, which is why it lives here and not on the overview itself.
TOP_HOLDINGS = 12

#: What to call each broker in the UI. A source key is a config name, not a
#: label to put in front of someone.
BROKER_LABELS = {"ibkr": "Interactive Brokers", "trading212": "Trading 212"}


def _build_chip_data(
    spreads: list[Spread],
    today: dt.date,
    decision_zone_days: dict[str, int],
) -> list[dict]:
    enrichment = enrich_tickers([s.underlying for s in spreads])

    chips = []
    for s in spreads:
        dte = (s.expiry - today).days
        zone_days = decision_zone_days.get(s.underlying, decision_zone_days["DEFAULT"])
        earnings = enrichment[s.underlying].earnings_date
        earnings_flag = earnings is not None and today <= earnings <= s.expiry
        chips.append(
            {
                "underlying": s.underlying,
                "label": s.label,
                "expiry": s.expiry.isoformat(),
                "dte": dte,
                "pnl": round(s.unrealized_pnl, 2),
                "gain": s.unrealized_pnl >= 0,
                "inDecisionZone": 0 <= dte <= zone_days,
                "zoneDays": zone_days,
                "earningsFlag": earnings_flag,
                "earningsDate": earnings.isoformat() if earnings_flag else None,
                "news": enrichment[s.underlying].news,
            }
        )
    return chips


def _account_data(overview: AccountOverview) -> dict:
    """One account, flattened for the page's JS.

    `null` is meaningful throughout and is preserved rather than coerced to 0:
    the view renders an em dash for a figure the broker did not report, which
    is a different statement from a figure that is zero.
    """
    return {
        "source": overview.source,
        "label": BROKER_LABELS.get(overview.source, overview.source),
        "profile": overview.profile,
        "account": overview.account,
        "currency": overview.currency,
        "asOf": overview.as_of.isoformat() if overview.as_of else None,
        "ok": overview.ok,
        "error": overview.error,
        "netLiquidation": overview.net_liquidation,
        "cash": overview.cash,
        "unrealizedPnl": overview.unrealized_pnl,
        "realizedPnl": overview.realized_pnl,
        "margin": (
            {
                "maintenance": overview.maintenance_margin,
                "excess": overview.excess_liquidity,
                "buyingPower": overview.buying_power,
                "cushion": overview.cushion,
                "utilisation": overview.utilisation,
            }
            if overview.has_margin
            else None
        ),
        "optionCount": overview.option_count,
        "equityCount": overview.equity_count,
        "currencies": [
            {
                "currency": row.currency,
                "cash": row.cash,
                "netLiquidation": row.net_liquidation,
                "unrealizedPnl": row.unrealized_pnl,
                "rate": row.exchange_rate,
            }
            for row in overview.currencies
        ],
        "holdings": [
            {
                "symbol": h.symbol,
                "quantity": h.quantity,
                "price": h.price,
                "marketValue": h.market_value,
                "currency": h.currency,
                "baseValue": h.base_value,
                "baseCurrency": h.base_currency or overview.currency,
                "unrealizedPnl": h.unrealized_pnl,
            }
            for h in overview.holdings[:TOP_HOLDINGS]
        ],
        "unavailable": overview.unavailable,
    }


def _fx_data(rates: RateTable, accounts: list[AccountOverview]) -> dict:
    """The rate table, plus the currencies the picker should offer.

    Offered = the standard list, then any account's own currency that is not
    already in it, filtered to what there is actually a rate for. An account
    denominated in something exotic still gets a picker entry; a currency with
    no rate never appears, so nothing on the page can be selected into a
    conversion that cannot be made.
    """
    # Everything the table can actually price, pivot first, then the accounts'
    # own currencies, then the rest. Derived from the table rather than from a
    # list here, so adding a currency is a change at the fetch and nowhere else.
    wanted = [
        rates.base,
        *(a.currency for a in accounts if a.ok and a.currency),
        *sorted(rates.rates),
    ]
    offered = [c for c in dict.fromkeys(wanted) if rates.has(c)]
    return {
        "base": rates.base,
        "rates": rates.rates,
        "asOf": rates.as_of.isoformat(),
        "source": rates.source,
        "stale": rates.stale,
        "currencies": offered,
    }


def build_calendar_html(
    spreads: list[Spread],
    today: dt.date | None = None,
    decision_zone_days: dict[str, int] | None = None,
    accounts: list[AccountOverview] | None = None,
    rates: RateTable | None = None,
) -> str:
    """Render the whole dashboard to one self-contained HTML string.

    `accounts` is optional -- with none passed the Accounts tab is simply not
    rendered, so a caller that has `Spread`s from somewhere other than a
    broker (a backtest, IBKR MCP) still gets the three spread views.

    `rates` is optional too, and independently: without it every account is
    shown in its own currency and no combined total is offered, which is the
    honest degradation when no exchange rate could be had.
    """
    today = today or dt.date.today()
    decision_zone_days = decision_zone_days or DECISION_ZONE_DAYS
    chips = _build_chip_data(spreads, today, decision_zone_days)
    accounts = accounts or []

    payload = json.dumps(
        {
            "today": today.isoformat(),
            "chips": chips,
            "accounts": [_account_data(a) for a in accounts],
            "fx": _fx_data(rates, accounts) if rates else None,
        }
    ).replace("</", "<\\/")

    return _template().replace("__PICTOR_DATA__", payload)


#: The built front end: one self-contained HTML file with a `__PICTOR_DATA__`
#: placeholder where the payload goes. It is a build artefact of `web/` (see
#: `web/build.sh`) that is committed and shipped inside the package, so a
#: plain `pip install pictor` needs no Node and no build step.
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "_web" / "index.html"


#: Front-end sources, present in a checkout and absent from an installed wheel.
_SOURCE_DIR = _TEMPLATE_PATH.parents[3] / "web" / "src"


def _warn_if_stale(built_at: float) -> None:
    """Say so when the front-end sources are newer than the built page.

    The one failure mode this split introduces: edit `web/src`, forget to run
    `web/build.sh`, and the CLI cheerfully renders the previous build while
    reporting success. Silence there costs an hour of "my change did nothing",
    so it is worth a handful of `stat` calls. Skipped entirely for an installed
    wheel, which has no sources to compare against.
    """
    if not _SOURCE_DIR.is_dir():
        return
    newest = max(
        (p.stat().st_mtime for p in _SOURCE_DIR.rglob("*") if p.is_file()), default=0.0
    )
    if newest > built_at:
        warnings.warn(
            f"{_SOURCE_DIR} is newer than the built front end -- this page is from the "
            "previous build. Run web/build.sh.",
            stacklevel=3,
        )


def _template() -> str:
    """The built page shell.

    Read on every call rather than cached at import: during front-end work the
    file is rebuilt underneath a running process, and a cached copy would
    quietly serve the previous build.
    """
    try:
        text = _TEMPLATE_PATH.read_text()
    except FileNotFoundError:  # pragma: no cover -- a broken install or checkout
        raise RuntimeError(
            f"the built front end is missing at {_TEMPLATE_PATH}. It is committed, so this "
            "is either an incomplete checkout or an edit that deleted it; rebuild with "
            "web/build.sh (needs Docker, installs nothing on the host)."
        ) from None
    _warn_if_stale(_TEMPLATE_PATH.stat().st_mtime)
    return text
