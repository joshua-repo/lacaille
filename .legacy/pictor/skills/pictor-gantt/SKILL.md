---
name: pictor-gantt
description: Render an interactive expiry Gantt chart or calendar dashboard for open vertical option spreads (e.g. bull put credit spreads), with per-ticker decision-zone windows and earnings/recent-news flags pulled from a live IBKR positions snapshot. Use when the user wants to visualize option spread expiries, check for earnings colliding with expiry, or decide which spreads need attention soon.
---

# Pictor Gantt

Renders an interactive HTML view of open vertical option spreads (e.g. bull
put credit spreads), with:

- Bars/chips colored by unrealized P&L (green/red).
- A per-ticker "decision zone" -- the days-to-expiry window in which the
  position should be reviewed for close/roll.
- A diamond marker if an earnings date falls before expiry.
- A star marker if there's been a headline in the last few days.
- Full detail on hover (ticker, strikes, expiry, P&L, flags) to keep the
  chart itself uncluttered.

Two forms ship:

- **calendar** (`pictor.charts.build_calendar_html` / `pictor calendar`) --
  the flagship view. A month-grid dashboard with a chip per spread on its
  expiry date, plus native Gantt and table views and an underlying filter,
  all on one page, all sharing one filtered dataset. Prefer this by default.
- **gantt** (`pictor.charts.build_chart` / `pictor gantt`) -- a standalone
  Plotly Gantt chart, same enrichment, bar length = days-to-expiry. Use when
  the caller specifically wants a single static Plotly figure (e.g. to embed
  elsewhere) rather than the full dashboard.

## When to use this

- The user asks to visualize their open spread positions against expiry.
- The user wants to check whether earnings or recent news collides with an
  expiry they're holding.
- The user wants a "what needs attention soon" view across many tickers.

## How to run it

From a checkout of this repo (or after `pip install pictor` / `uv add
pictor` -- antlia is a core dependency, not an extra):

```bash
# live account (default -- currently the only gateway actually running,
# a dockerized IB Gateway on host port 4001)
pictor calendar --open

# paper account, if/when a paper gateway is also running
pictor calendar --profile paper --open

# not a chart -- what each broker holds right now (IBKR options + shares,
# Trading212 shares). The quickest way to tell a credential/gateway problem
# apart from a charting one.
pictor positions
```

Positions come from [antlia](https://github.com/joshua-repo/antlia)'s IBKR
account source -- a read-only socket connection to TWS/IB Gateway. It needs
TWS/Gateway running and reachable, and credentials/host resolved via
environment variables or `~/.antlia/credentials.toml` (see antlia's README).
If neither is set up, `pictor calendar` will fail with antlia's own
connection error rather than silently falling back to anything.

antlia also reaches a Trading212 account (`pictor positions --source
trading212`), but that is a cash equity account with no options in it, so it
feeds nothing in these charts -- don't reach for it when asked for a spread
view.

The calendar page's fourth tab, **Accounts**, is where both brokers do show up
together: per-account net liquidation, cash, P&L, margin headroom and top
holdings. It is on by default; `--no-accounts` skips it and saves a round-trip
per broker.

That tab also has a display-currency picker and a combined **All accounts**
total, converted through `antlia.fx` (yfinance, falling back to ECB rates via
Frankfurter). If asked for a portfolio total across brokers, read it off that
card rather than adding the per-account numbers yourself -- and quote the rate
source and timestamp printed under it, since the total is only as good as that
rate. `--no-fx` skips the rate fetch, and then no total is offered at all.
Converted P&L is not FX-adjusted performance; don't present it as such.

Then open the HTML file in a browser (or use SendUserFile / a file link if
running non-interactively).

## Sourcing positions from IBKR MCP instead of antlia

If IBKR MCP tools (e.g. `get_account_positions`) are available in the
current session, that's usually the more convenient live source -- no local
TWS/Gateway connection or antlia setup needed. In that case, don't use
`pictor calendar` / `pictor gantt`; instead:

1. Call the IBKR MCP positions tool to get contract descriptions.
2. Use `pictor.pairing.parse_leg` to parse each `contract_description` /
   `position` / `unrealized_pnl` into an `OptionLeg`.
3. Call `pictor.pairing.pair_spreads(legs)` to get `Spread` objects.
4. Call `pictor.charts.build_calendar_html(spreads)` (or `build_chart` for
   the standalone Gantt) and write the result to a file.

This is exactly what `pictor.accounts.fetch_overview(...).option_legs` does
against antlia -- swap the data source, keep the rest of the pipeline; both
end up as the same `list[OptionLeg]`.

## Customizing decision zones

Per-ticker decision-zone thresholds (days-to-expiry at which a position
should be reviewed) live in `pictor.charts.gantt.DECISION_ZONE_DAYS`, with a
`"DEFAULT"` fallback. Pass a custom dict via `build_calendar_html(spreads,
decision_zone_days={...})` / `build_chart(spreads, decision_zone_days={...})`
rather than editing the module if the override is one-off.

## Notes

- Earnings/news lookups use `yfinance` (free, occasionally stale/incomplete),
  fetched once per unique underlying in parallel (`pictor.enrichment.enrich_tickers`).
  Not a big deal for a quick check; don't treat a missing earnings flag as
  confirmation there is no earnings date.
- Unmatched legs (no opposite-side counterpart in the same
  underlying/right/expiry group) are silently dropped by `pair_spreads` --
  this only visualizes paired vertical spreads, not naked positions.
- antlia's IBKR session connects `readonly=True` -- there is no order-placement
  path through pictor, by construction of the layer underneath it.
