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

The pairing and charting logic doesn't care where positions came from --
feed it `OptionLeg` objects from [antlia](https://github.com/joshua-repo/antlia)
(the default, see below), IBKR MCP, a local JSON dump, or anything else.

## Usage

```bash
uv sync   # pulls in antlia[ibkr] (ib_insync, tzdata) -- pictor's only position source

uv run pictor calendar --open                        # live account, opens in browser
uv run pictor calendar --profile paper --open         # paper account, if one is running
uv run pictor gantt --output gantt.html
```

Positions come from [antlia](https://github.com/joshua-repo/antlia)'s IBKR
account source -- a socket connection to TWS/IB Gateway, read-only by
construction. `--profile` picks which antlia-configured connection to use
(`live` by default -- currently the only gateway actually running, a
dockerized IB Gateway on host port 4001; `paper` if/when a paper gateway is
also up). See antlia's own README for how to point it at your gateway and
set up `~/.antlia/credentials.toml`.

Or as a library:

```python
from pictor import pair_spreads
from pictor.charts import build_calendar_html, build_chart
from pictor.sources import fetch_positions_live

legs = fetch_positions_live(profile="live")
spreads = pair_spreads(legs)

open("calendar.html", "w").write(build_calendar_html(spreads))
build_chart(spreads).write_html("gantt.html")
```

`pair_spreads` and the chart builders take plain `OptionLeg`/`Spread`
objects, so a caller that already has positions from elsewhere (IBKR MCP,
Vela, a backtest) can skip `pictor.sources` entirely -- see
[skills/pictor-gantt/SKILL.md](skills/pictor-gantt/SKILL.md) for that path.
