---
name: pictor-gantt
description: Render an interactive expiry Gantt chart for open vertical option spreads (e.g. bull put credit spreads), with per-ticker decision-zone windows and earnings/recent-news flags pulled from a real or demo IBKR positions snapshot. Use when the user wants to visualize option spread expiries, check for earnings colliding with expiry, or decide which spreads need attention soon.
---

# Pictor Gantt

Renders an interactive Plotly HTML chart of open vertical option spreads
(e.g. bull put credit spreads), sorted by days-to-expiry, with:

- Bars colored by unrealized P&L (green/red).
- A per-ticker "decision zone" shaded region -- the days-to-expiry window in
  which the position should be reviewed for close/roll.
- A red diamond marker if an earnings date falls before expiry.
- A yellow star marker if there's been a headline in the last few days.
- Full detail on hover (ticker, strikes, expiry, P&L, flags) to keep the
  chart itself uncluttered.

## When to use this

- The user asks to visualize their open spread positions against expiry.
- The user wants to check whether earnings or recent news collides with an
  expiry they're holding.
- The user wants a "what needs attention soon" view across many tickers.

## How to run it

From a checkout of this repo (or after `pip install pictor` / `uv add
pictor`):

```bash
# demo snapshot (no live connection needed)
pictor gantt --output bull_spread_gantt.html

# live positions via ib_insync (requires TWS/IB Gateway running locally,
# API enabled, default port 7497 paper / 7496 live)
pictor gantt --live --output bull_spread_gantt.html
```

Then open the HTML file in a browser (or use SendUserFile / a file link if
running non-interactively).

## Sourcing positions from IBKR MCP instead of ib_insync

If IBKR MCP tools (e.g. `get_account_positions`) are available in the
current session, that's usually the more convenient live source -- no local
TWS/Gateway connection needed. In that case, don't use `pictor gantt --live`;
instead:

1. Call the IBKR MCP positions tool to get contract descriptions.
2. Use `pictor.pairing.parse_leg` to parse each `contract_description` /
   `position` / `unrealized_pnl` into an `OptionLeg`.
3. Call `pictor.pairing.pair_spreads(legs)` to get `Spread` objects.
4. Call `pictor.charts.build_chart(spreads)` to get the Plotly figure, then
   `fig.write_html(path)`.

This is exactly what `pictor.sources.demo.fetch_positions_demo` does against
the static snapshot -- swap the data source, keep the rest of the pipeline.

## Customizing decision zones

Per-ticker decision-zone thresholds (days-to-expiry at which a position
should be reviewed) live in `pictor.charts.gantt.DECISION_ZONE_DAYS`, with a
`"DEFAULT"` fallback. Pass a custom dict via
`build_chart(spreads, decision_zone_days={...})` rather than editing the
module if the override is one-off.

## Notes

- Earnings/news lookups use `yfinance` (free, occasionally stale/incomplete).
  Not a big deal for a quick check; don't treat a missing earnings flag as
  confirmation there is no earnings date.
- Unmatched legs (no opposite-side counterpart in the same
  underlying/right/expiry group) are silently dropped by `pair_spreads` --
  this only visualizes paired vertical spreads, not naked positions.
