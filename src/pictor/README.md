# pictor

Visualization layer for option spread positions. Two views ship today:

- **calendar** -- a month-grid dashboard: a chip per spread on its expiry
  date, colored by P&L, ringed when inside its decision zone, badged for
  earnings-before-expiry and recent headlines, plus native Gantt and table
  views and an underlying filter, all in one page. Self-contained, no
  external assets.
- **gantt** -- a standalone expiry-sorted Gantt chart (Plotly) with the same
  decision zone / earnings / news enrichment, bar length showing
  days-to-expiry.

The calendar page also carries an **Accounts** tab: one card per broker
account -- net liquidation, cash, unrealized P&L, margin headroom with a
utilisation meter, top holdings ranked by value, and the per-currency
breakdown for a multi-currency account. Every figure rolls into place on a
digit wheel ported from [NumberTicker](https://github.com/joshua-repo/NumberTicker).

A **display-currency picker** (USD / GBP / JPY / HKD / Native) restates every
figure on that tab, and a combined **All accounts** card totals them -- which is
only offered because the rate and its timestamp are printed underneath it.
Switching currency rolls every digit on the page at once.

Rates come from **`antlia.fx`**, the same library the positions do -- yfinance
first, because it is a market rate that reconciles with the broker's own (Yahoo
USD/JPY 160.04 against IBKR's 160.08), falling back to the ECB via Frankfurter
when Yahoo misbehaves, which it does. Rates cache for 6 hours. `pictor.fx` is a
thin wrapper that makes exactly one decision antlia leaves to its callers: if
there is no rate at all, the page drops the picker and shows each account in
its own currency rather than failing. A *stale* rate is not a failure -- it is
shown, and labelled.

Two things the page is careful about, because getting them wrong is expensive:
converted P&L moves with the exchange rate as well as with the positions, so it
is **not** FX-adjusted performance; and holdings are converted per position
using each instrument's own currency, never per account, since an IBKR account
can hold JPY and USD lines side by side.

The pairing and charting logic doesn't care where positions came from --
feed it `OptionLeg` objects from [antlia](https://github.com/joshua-repo/antlia)
(the default, see below), IBKR MCP, a local JSON dump, or anything else.

## Usage

```bash
uv sync   # pulls in antlia[ibkr,trading212,yfinance] -- pictor's only position and FX source

uv run pictor calendar --open                         # live account, opens in browser
uv run pictor calendar --profile paper --open         # paper account, if one is running
uv run pictor gantt --output gantt.html

uv run pictor positions                               # what both brokers hold, right now
uv run pictor positions --source trading212           # one broker only

uv run pictor calendar --no-accounts                  # skip the Accounts tab, one less round-trip
uv run pictor calendar --t212-profile demo            # T212 demo host instead of live
uv run pictor calendar --no-fx                        # native currencies only, no combined total
```

A broker that cannot be reached does not cost you the page: `pictor calendar`
warns on stderr, renders the account you *can* read, and puts the connection
error verbatim on a card in place of the other one.

Positions come from [antlia](https://github.com/joshua-repo/antlia), which
owns every connection, credential and rate limit; pictor only picks a source
and a profile. Two are wired up:

| source | how | profiles | holds |
| --- | --- | --- | --- |
| `ibkr` | socket to TWS / IB Gateway, read-only by construction | `live`, `paper` | options **and** shares |
| `trading212` | REST, HTTP Basic key+secret | `live`, `demo` | shares only |

The charts are an option-spread view, so they run on IBKR alone -- Trading212
is a cash equity account with no options in it, and its holdings show up in
`pictor positions` rather than in the calendar. `--profile` defaults to `live`
(currently the only IBKR gateway actually running is a dockerized one on host
port 4001; `paper` works if/when a paper gateway is also up). See antlia's own
README for `~/.antlia/credentials.toml`, and `uv run python -m antlia.auth
--verify` to prove a credential actually round-trips before blaming pictor.

## Working on the front end

The dashboard's UI lives in `web/` as ES modules and CSS. Vite bundles it and
inlines everything into **one self-contained HTML file** committed at
`src/pictor/_web/index.html`, which is what `pictor calendar` fills in with a
JSON payload. Installing pictor needs no Node and no build step -- the built
file ships in the wheel.

```bash
./web/build.sh     # rebuild after editing web/src
```

That script runs Node in a throwaway `node:22-alpine` container and installs
nothing on your machine. If you edit `web/src` and forget to rebuild, rendering
warns you rather than quietly serving the previous build.

Or as a library:

```python
from pictor import pair_spreads
from pictor.charts import build_calendar_html, build_chart
from pictor.accounts import fetch_overview

legs = fetch_overview("ibkr", profile="live").option_legs
spreads = pair_spreads(legs)

open("calendar.html", "w").write(build_calendar_html(spreads))
build_chart(spreads).write_html("gantt.html")
```

`pair_spreads` and the chart builders take plain `OptionLeg`/`Spread`
objects, so a caller that already has positions from elsewhere (IBKR MCP,
Vela, a backtest) can skip `pictor.accounts` entirely -- see
[skills/pictor-gantt/SKILL.md](skills/pictor-gantt/SKILL.md) for that path.
