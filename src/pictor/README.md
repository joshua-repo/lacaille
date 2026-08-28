# pictor

Visualization layer for option spread positions. Currently ships one view:
an interactive expiry Gantt chart for vertical spreads (e.g. bull put credit
spreads), with per-ticker decision-zone windows and earnings/recent-news
flags.

Not tied to any particular position source -- feed it `OptionLeg` objects
from IBKR MCP, `ib_insync`, a local JSON dump, or anything else; the
pairing and charting logic doesn't care.

## Usage

```bash
uv sync
uv run pictor gantt --output bull_spread_gantt.html          # demo snapshot
uv run pictor gantt --live --output bull_spread_gantt.html   # live via ib_insync
```

Or as a library:

```python
from pictor import pair_spreads, build_chart
from pictor.sources import fetch_positions_demo

legs = fetch_positions_demo()
spreads = pair_spreads(legs)
fig = build_chart(spreads)
fig.write_html("out.html")
```

See [skills/pictor-gantt/SKILL.md](skills/pictor-gantt/SKILL.md) for the
Claude Skill version of this workflow.
