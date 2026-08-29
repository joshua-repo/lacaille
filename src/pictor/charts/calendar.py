"""Calendar-grid view of vertical spread expiries -- an alternative to the
Gantt view in `pictor.charts.gantt`, organized as a month calendar with a
chip per spread on its expiry date. Ships a native (non-Plotly) Gantt view
and a table view alongside it, all driven by the same underlying-ticker
filter, so this one page covers all three ways of looking at the same data.

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

from pictor.charts.gantt import DECISION_ZONE_DAYS
from pictor.enrichment import enrich_tickers
from pictor.models import Spread


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


def build_calendar_html(
    spreads: list[Spread],
    today: dt.date | None = None,
    decision_zone_days: dict[str, int] | None = None,
) -> str:
    today = today or dt.date.today()
    decision_zone_days = decision_zone_days or DECISION_ZONE_DAYS
    chips = _build_chip_data(spreads, today, decision_zone_days)

    payload = json.dumps({"today": today.isoformat(), "chips": chips}).replace("</", "<\\/")

    return _TEMPLATE.replace("__PICTOR_DATA__", payload)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Spread expiry calendar</title>
<style>
  :root {
    color-scheme: light;
    /* Bayswater Research brand: deep navy #16324A, slate #3B5A70,
       copper accent #B05F3A / #D98A5C (dark), warm white #FAF9F7. */
    --surface-1:      rgba(255, 253, 250, 0.66);
    --surface-solid:  #fdfcfa;
    --page-plane:     #f2efe9;
    --text-primary:   #16324a;
    --text-secondary: #4a6377;
    --text-muted:     #8a99a4;
    --gridline:       rgba(22, 50, 74, 0.09);
    --baseline:       #c3c2b7;
    --border:         rgba(22, 50, 74, 0.14);
    --good:           #0ca30c;
    --good-text:      #006300;
    --critical:       #d03b3b;
    --warning:        #fab219;
    --cat-orange:     #eb6834;
    --cat-yellow:     #eda100;
    --accent:         #3b5a70;
    --accent-wash:    rgba(59, 90, 112, 0.10);
    --copper:         #b05f3a;
    --copper-wash:    rgba(176, 95, 58, 0.12);
    --glow:           rgba(59, 90, 112, 0.28);
    --blur: blur(18px);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --surface-1:      rgba(20, 32, 44, 0.58);
      --surface-solid:  #101c27;
      --page-plane:     #060b11;
      --text-primary:   #faf9f7;
      --text-secondary: #9fb3c4;
      --text-muted:     #62798c;
      --gridline:       rgba(159, 179, 196, 0.12);
      --baseline:       #383835;
      --border:         rgba(159, 179, 196, 0.16);
      --good:           #0ca30c;
      --good-text:      #0ca30c;
      --critical:       #e66767;
      --warning:        #fab219;
      --cat-orange:     #d95926;
      --cat-yellow:     #c98500;
      --accent:         #7ea0b8;
      --accent-wash:    rgba(126, 160, 184, 0.16);
      --copper:         #d98a5c;
      --copper-wash:    rgba(217, 138, 92, 0.16);
      --glow:           rgba(126, 160, 184, 0.45);
    }
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    background:
      radial-gradient(900px 480px at 10% -10%, var(--accent-wash), transparent 60%),
      radial-gradient(700px 420px at 100% 8%, var(--copper-wash), transparent 55%),
      var(--page-plane);
    background-attachment: fixed;
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .page {
    max-width: 1120px;
    margin: 0 auto;
    padding: 32px 20px 64px;
  }
  header.hd {
    position: relative;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
    padding-bottom: 14px;
    flex-wrap: wrap;
  }
  header.hd::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--text-primary), var(--accent) 55%, var(--copper));
    opacity: 0.5;
  }
  header.hd h1 {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }
  header.hd p {
    margin: 4px 0 0;
    color: var(--text-secondary);
    font-size: 13px;
  }

  .views {
    display: inline-flex;
    border: 1px solid var(--border);
    overflow: hidden;
    flex: none;
    background: var(--surface-1);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
  }
  .views button {
    border: none;
    border-right: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  }
  .views button:last-child { border-right: none; }
  .views button:hover { background: var(--accent-wash); }
  .views button.active {
    background: var(--accent-wash);
    color: var(--text-primary);
    box-shadow: inset 0 0 0 1px var(--accent), inset 0 0 14px var(--glow);
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 20px;
  }
  .filters .fl {
    font-size: 12px;
    color: var(--text-muted);
    margin-right: 4px;
  }
  .pill {
    border: 1px solid var(--border);
    background: var(--surface-1);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    color: var(--text-secondary);
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, box-shadow 0.15s;
  }
  .pill:hover { background: var(--accent-wash); }
  .pill.active {
    background: var(--accent-wash);
    border-color: var(--accent);
    color: var(--text-primary);
    box-shadow: 0 0 0 1px var(--accent), 0 0 14px var(--glow);
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    overflow: hidden;
    margin-bottom: 20px;
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
  }
  .stat {
    background: var(--surface-1);
    padding: 16px 18px;
  }
  .stat .label {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .stat .value {
    font-size: 26px;
    font-weight: 600;
    margin-top: 4px;
    font-variant-numeric: proportional-nums;
  }
  .stat .value.good { color: var(--good-text); }
  .stat .value.critical { color: var(--critical); }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    align-items: center;
    padding: 12px 16px;
    background: var(--surface-1);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    border: 1px solid var(--border);
    margin-bottom: 20px;
    font-size: 12px;
    color: var(--text-secondary);
  }
  .legend .item { display: flex; align-items: center; gap: 6px; }
  .legend .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
  .legend .diamond {
    width: 9px; height: 9px; flex: none;
    background: var(--cat-orange); transform: rotate(45deg);
  }
  .legend .star { width: 12px; height: 12px; flex: none; color: var(--cat-yellow); }
  .legend .ring {
    width: 9px; height: 9px; border-radius: 50%; flex: none;
    box-shadow: 0 0 0 2px var(--warning);
  }

  .card {
    background: var(--surface-1);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    border: 1px solid var(--border);
    overflow: hidden;
    margin-bottom: 28px;
  }
  .month-title {
    padding: 14px 18px;
    font-size: 14px;
    font-weight: 600;
    border-bottom: 1px solid var(--gridline);
  }
  .weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    border-bottom: 1px solid var(--gridline);
  }
  .weekdays div {
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .weeks { display: grid; }
  .week-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    border-bottom: 1px solid var(--gridline);
  }
  .week-row:last-child { border-bottom: none; }
  .day {
    min-height: 74px;
    padding: 6px;
    border-right: 1px solid var(--gridline);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .day:last-child { border-right: none; }
  .day.outside .daynum { color: var(--text-muted); opacity: 0.5; }
  .day.today { background: var(--accent-wash); }
  .daynum {
    font-size: 12px;
    color: var(--text-secondary);
    font-weight: 500;
  }
  .day.today .daynum {
    display: inline-flex;
    align-self: flex-start;
    align-items: center;
    justify-content: center;
    min-width: 18px; height: 18px;
    padding: 0 4px;
    background: var(--accent);
    color: white;
    font-weight: 600;
    box-shadow: 0 0 12px var(--glow);
  }
  .chip {
    position: relative;
    background: var(--surface-solid);
    border: 1px solid var(--border);
    border-left: 3px solid var(--good);
    padding: 3px 7px 3px 6px;
    cursor: default;
    transition: box-shadow 0.15s;
  }
  .chip:hover { box-shadow: 0 0 0 1px var(--border), 0 4px 16px rgba(0,0,0,0.12); }
  .chip.loss { border-left-color: var(--critical); }
  .chip.zone { box-shadow: 0 0 0 2px var(--warning), 0 0 10px rgba(250,178,25,0.35); }
  .chip .tk { font-size: 11.5px; font-weight: 600; }
  .chip .strikes { font-size: 10.5px; color: var(--text-secondary); }
  .chip .badges {
    position: absolute;
    top: 3px; right: 4px;
    display: flex;
    gap: 2px;
  }
  .chip .diamond {
    width: 7px; height: 7px;
    background: var(--cat-orange);
    transform: rotate(45deg);
  }
  .chip .star { width: 9px; height: 9px; color: var(--cat-yellow); }

  .gantt-card { padding-bottom: 8px; }
  .gantt-row {
    display: grid;
    grid-template-columns: 150px 1fr;
    align-items: center;
    gap: 12px;
    padding: 7px 18px;
    border-bottom: 1px solid var(--gridline);
  }
  .gantt-row:hover { background: var(--accent-wash); }
  .gantt-label .tk { font-size: 12px; font-weight: 600; }
  .gantt-label .strikes { font-size: 11px; color: var(--text-secondary); }
  .gantt-track { position: relative; height: 24px; }
  .gantt-track .zone-band {
    position: absolute;
    left: 0; top: 2px; bottom: 2px;
    background: rgba(250, 178, 25, 0.16);
  }
  .gantt-track .bar {
    position: absolute;
    left: 0; top: 5px; height: 14px;
    background: var(--good);
    min-width: 3px;
  }
  .gantt-track .bar.loss { background: var(--critical); }
  .gantt-track .tip-label {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    color: var(--text-secondary);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .gantt-track .marker {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
  }
  .gantt-track .marker.diamond {
    width: 8px; height: 8px;
    background: var(--cat-orange);
    transform: translate(-50%, -50%) rotate(45deg);
  }
  .gantt-track .marker.star { width: 11px; height: 11px; color: var(--cat-yellow); }
  .gantt-axis {
    display: grid;
    grid-template-columns: 150px 1fr;
    padding: 8px 18px 12px;
  }
  .gantt-axis .ticks {
    position: relative;
    height: 18px;
    border-top: 1px solid var(--gridline);
  }
  .gantt-axis .tick {
    position: absolute;
    top: 5px;
    font-size: 10px;
    color: var(--text-muted);
    transform: translateX(-50%);
  }
  .gantt-empty, .cal-empty {
    padding: 40px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }

  .tooltip {
    position: fixed;
    z-index: 20;
    background: var(--text-primary);
    color: var(--surface-solid);
    font-size: 12px;
    line-height: 1.5;
    padding: 8px 10px;
    pointer-events: none;
    max-width: 240px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25), 0 0 20px var(--glow);
    opacity: 0;
    transition: opacity 0.1s;
  }
  .tooltip.show { opacity: 1; }
  .tooltip b { font-weight: 600; }
  .tooltip .row { display: flex; justify-content: space-between; gap: 12px; }

  table.data {
    width: 100%;
    border-collapse: collapse;
    background: var(--surface-1);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    border: 1px solid var(--border);
    overflow: hidden;
    font-size: 13px;
  }
  table.data th, table.data td {
    text-align: left;
    padding: 9px 14px;
    border-bottom: 1px solid var(--gridline);
  }
  table.data tr:hover td { background: var(--accent-wash); }
  table.data th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    font-weight: 600;
  }
  table.data td.num { font-variant-numeric: tabular-nums; }
  table.data td.good { color: var(--good-text); }
  table.data td.critical { color: var(--critical); }
  table.data tr:last-child td { border-bottom: none; }

  .hidden { display: none !important; }
</style>
</head>
<body>
<div class="page">
  <header class="hd">
    <div>
      <h1>Bull put spread expiry calendar</h1>
      <p id="subtitle"></p>
    </div>
    <div class="views" id="views">
      <button data-view="calendar" class="active">Calendar</button>
      <button data-view="gantt">Gantt</button>
      <button data-view="table">Table</button>
    </div>
  </header>

  <div class="filters" id="filters">
    <span class="fl">Underlying</span>
  </div>

  <div class="stats" id="stats"></div>

  <div class="legend">
    <span class="item"><span class="dot" style="background:var(--good)"></span>Net gain</span>
    <span class="item"><span class="dot" style="background:var(--critical)"></span>Net loss</span>
    <span class="item"><span class="ring"></span>In decision zone</span>
    <span class="item"><span class="diamond"></span>Earnings before expiry</span>
    <span class="item"><svg class="star" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.9 6.6 7.1.6-5.4 4.7 1.7 7-6.3-3.9-6.3 3.9 1.7-7L2 9.2l7.1-.6z"/></svg>Recent headline</span>
  </div>

  <div id="calendarView"></div>
  <div id="ganttView" class="hidden"></div>
  <div id="tableView" class="hidden"></div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
const DATA = __PICTOR_DATA__;
const state = { view: "calendar", selected: new Set() };

function toLocalIso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return y + "-" + m + "-" + day;
}

const fmtMoney = n => (n < 0 ? "-$" : "+$") + Math.abs(n).toLocaleString(undefined, {maximumFractionDigits: 0});
const fmtDate = iso => {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, {month: "short", day: "numeric"});
};

function underlyings() {
  return [...new Set(DATA.chips.map(c => c.underlying))].sort();
}

function filteredChips() {
  if (state.selected.size === 0) return DATA.chips;
  return DATA.chips.filter(c => state.selected.has(c.underlying));
}

function buildFilters() {
  const root = document.getElementById("filters");
  root.querySelectorAll(".pill").forEach(el => el.remove());

  const allPill = document.createElement("button");
  allPill.className = "pill" + (state.selected.size === 0 ? " active" : "");
  allPill.textContent = "All";
  allPill.addEventListener("click", () => {
    state.selected.clear();
    render();
  });
  root.appendChild(allPill);

  for (const tk of underlyings()) {
    const pill = document.createElement("button");
    pill.className = "pill" + (state.selected.has(tk) ? " active" : "");
    pill.textContent = tk;
    pill.addEventListener("click", () => {
      if (state.selected.has(tk)) state.selected.delete(tk);
      else state.selected.add(tk);
      render();
    });
    root.appendChild(pill);
  }
}

function buildStats(chips) {
  const netPnl = chips.reduce((sum, c) => sum + c.pnl, 0);
  const zoneCount = chips.filter(c => c.inDecisionZone).length;
  const earningsCount = chips.filter(c => c.earningsFlag).length;

  const stats = [
    {label: "Open spreads", value: chips.length},
    {label: "Net unrealized P&L", value: fmtMoney(netPnl), cls: netPnl >= 0 ? "good" : "critical"},
    {label: "In decision zone", value: zoneCount},
    {label: "Earnings collisions", value: earningsCount},
  ];

  const el = document.getElementById("stats");
  el.innerHTML = "";
  for (const s of stats) {
    const div = document.createElement("div");
    div.className = "stat";
    const label = document.createElement("div");
    label.className = "label";
    label.textContent = s.label;
    const value = document.createElement("div");
    value.className = "value" + (s.cls ? " " + s.cls : "");
    value.textContent = s.value;
    div.append(label, value);
    el.appendChild(div);
  }
}

function chipsByDate(chips) {
  const map = {};
  for (const c of chips) {
    if (!map[c.expiry]) map[c.expiry] = [];
    map[c.expiry].push(c);
  }
  return map;
}

function buildCalendar(chips) {
  const root = document.getElementById("calendarView");
  root.innerHTML = "";

  if (chips.length === 0) {
    const empty = document.createElement("div");
    empty.className = "card cal-empty";
    empty.textContent = "No spreads match this filter.";
    root.appendChild(empty);
    return;
  }

  const byDate = chipsByDate(chips);
  const today = new Date(DATA.today + "T00:00:00");
  const todayIso = DATA.today;

  const dates = chips.map(c => new Date(c.expiry + "T00:00:00"));
  dates.push(today);
  const minD = new Date(Math.min(...dates));
  const maxD = new Date(Math.max(...dates));

  const months = [];
  let cursor = new Date(minD.getFullYear(), minD.getMonth(), 1);
  const end = new Date(maxD.getFullYear(), maxD.getMonth(), 1);
  while (cursor <= end) {
    months.push(new Date(cursor));
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
  }

  for (const monthStart of months) {
    const card = document.createElement("div");
    card.className = "card";

    const title = document.createElement("div");
    title.className = "month-title";
    title.textContent = monthStart.toLocaleDateString(undefined, {month: "long", year: "numeric"});
    card.appendChild(title);

    const weekdays = document.createElement("div");
    weekdays.className = "weekdays";
    for (const wd of ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]) {
      const d = document.createElement("div");
      d.textContent = wd;
      weekdays.appendChild(d);
    }
    card.appendChild(weekdays);

    const weeksEl = document.createElement("div");
    weeksEl.className = "weeks";

    const firstOfMonth = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1);
    const gridStart = new Date(firstOfMonth);
    gridStart.setDate(gridStart.getDate() - gridStart.getDay());
    const lastOfMonth = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
    const gridEnd = new Date(lastOfMonth);
    gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()));

    let day = new Date(gridStart);
    while (day <= gridEnd) {
      const weekRow = document.createElement("div");
      weekRow.className = "week-row";
      for (let i = 0; i < 7; i++) {
        const iso = toLocalIso(day);
        const cell = document.createElement("div");
        cell.className = "day";
        if (day.getMonth() !== monthStart.getMonth()) cell.classList.add("outside");
        if (iso === todayIso) cell.classList.add("today");

        const num = document.createElement("div");
        num.className = "daynum";
        num.textContent = day.getDate();
        cell.appendChild(num);

        for (const c of (byDate[iso] || [])) {
          cell.appendChild(buildChip(c));
        }

        weekRow.appendChild(cell);
        day = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1);
      }
      weeksEl.appendChild(weekRow);
    }
    card.appendChild(weeksEl);
    root.appendChild(card);
  }
}

function buildChip(c) {
  const chip = document.createElement("div");
  chip.className = "chip" + (c.gain ? "" : " loss") + (c.inDecisionZone ? " zone" : "");

  const tk = document.createElement("div");
  tk.className = "tk";
  tk.textContent = c.underlying;
  chip.appendChild(tk);

  const strikes = document.createElement("div");
  strikes.className = "strikes";
  strikes.textContent = c.label.slice(c.underlying.length + 1) + " · " + c.dte + "d";
  chip.appendChild(strikes);

  if (c.earningsFlag || c.news) {
    const badges = document.createElement("div");
    badges.className = "badges";
    if (c.earningsFlag) {
      const b = document.createElement("div");
      b.className = "diamond";
      badges.appendChild(b);
    }
    if (c.news) {
      badges.appendChild(starIcon());
    }
    chip.appendChild(badges);
  }

  wireHover(chip, c);
  return chip;
}

function starIcon() {
  const b = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  b.setAttribute("class", "star");
  b.setAttribute("viewBox", "0 0 24 24");
  b.setAttribute("fill", "currentColor");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M12 2l2.9 6.6 7.1.6-5.4 4.7 1.7 7-6.3-3.9-6.3 3.9 1.7-7L2 9.2l7.1-.6z");
  b.appendChild(path);
  return b;
}

function wireHover(el, c) {
  el.addEventListener("pointerenter", e => showTooltip(e, c));
  el.addEventListener("pointermove", e => positionTooltip(e));
  el.addEventListener("pointerleave", hideTooltip);
  el.tabIndex = 0;
  el.addEventListener("focus", e => showTooltip(e, c));
  el.addEventListener("blur", hideTooltip);
}

function buildGantt(chips) {
  const root = document.getElementById("ganttView");
  root.innerHTML = "";

  if (chips.length === 0) {
    const empty = document.createElement("div");
    empty.className = "card gantt-empty";
    empty.textContent = "No spreads match this filter.";
    root.appendChild(empty);
    return;
  }

  const sorted = [...chips].sort((a, b) => a.dte - b.dte);
  const today = new Date(DATA.today + "T00:00:00");
  const maxDte = Math.max(...sorted.map(c => c.dte), ...sorted.map(c => c.zoneDays), 1);
  const axisMax = Math.ceil((maxDte + 3) / 7) * 7;

  const card = document.createElement("div");
  card.className = "card gantt-card";

  for (const c of sorted) {
    const row = document.createElement("div");
    row.className = "gantt-row";

    const label = document.createElement("div");
    label.className = "gantt-label";
    const tk = document.createElement("div");
    tk.className = "tk";
    tk.textContent = c.underlying;
    const strikes = document.createElement("div");
    strikes.className = "strikes";
    strikes.textContent = c.label.slice(c.underlying.length + 1);
    label.append(tk, strikes);
    row.appendChild(label);

    const track = document.createElement("div");
    track.className = "gantt-track";

    const zoneBand = document.createElement("div");
    zoneBand.className = "zone-band";
    zoneBand.style.width = pct(c.zoneDays, axisMax);
    track.appendChild(zoneBand);

    const bar = document.createElement("div");
    bar.className = "bar" + (c.gain ? "" : " loss");
    bar.style.width = pct(c.dte, axisMax);
    track.appendChild(bar);

    const tipLabel = document.createElement("div");
    tipLabel.className = "tip-label";
    tipLabel.textContent = c.dte + "d";
    tipLabel.style.left = "calc(" + pct(c.dte, axisMax) + " + 6px)";
    track.appendChild(tipLabel);

    if (c.earningsFlag) {
      const earningsDte = Math.round((new Date(c.earningsDate + "T00:00:00") - today) / 86400000);
      const marker = document.createElement("div");
      marker.className = "marker diamond";
      marker.style.left = pct(earningsDte, axisMax);
      track.appendChild(marker);
    }
    if (c.news) {
      const marker = starIcon();
      marker.classList.add("marker");
      marker.style.left = pct(c.dte + 1, axisMax);
      track.appendChild(marker);
    }

    row.appendChild(track);
    wireHover(row, c);
    card.appendChild(row);
  }

  const axis = document.createElement("div");
  axis.className = "gantt-axis";
  const axisLabelSpacer = document.createElement("div");
  axis.appendChild(axisLabelSpacer);
  const ticks = document.createElement("div");
  ticks.className = "ticks";
  for (let d = 0; d <= axisMax; d += 7) {
    const tick = document.createElement("div");
    tick.className = "tick";
    tick.style.left = pct(d, axisMax);
    tick.textContent = d + "d";
    ticks.appendChild(tick);
  }
  axis.appendChild(ticks);
  card.appendChild(axis);

  root.appendChild(card);
}

function pct(value, max) {
  return Math.max(0, Math.min(100, (value / max) * 100)) + "%";
}

const tooltipEl = document.getElementById("tooltip");

function showTooltip(e, c) {
  tooltipEl.innerHTML = "";
  const title = document.createElement("div");
  title.innerHTML = "<b></b>";
  title.querySelector("b").textContent = c.label;
  tooltipEl.appendChild(title);

  const rows = [
    ["Expiry", fmtDate(c.expiry) + " (" + c.dte + "d)"],
    ["Unrealized P&L", fmtMoney(c.pnl)],
  ];
  if (c.inDecisionZone) rows.push(["Decision zone", "within " + c.zoneDays + "d of expiry"]);
  if (c.earningsFlag) rows.push(["Earnings", fmtDate(c.earningsDate) + " (before expiry)"]);
  if (c.news) rows.push(["News", "recent headline"]);

  for (const [k, v] of rows) {
    const row = document.createElement("div");
    row.className = "row";
    const kEl = document.createElement("span");
    kEl.textContent = k;
    const vEl = document.createElement("b");
    vEl.textContent = v;
    row.append(kEl, vEl);
    tooltipEl.appendChild(row);
  }

  tooltipEl.classList.add("show");
  positionTooltip(e);
}

function positionTooltip(e) {
  const pad = 14;
  let x = e.clientX + pad;
  let y = e.clientY + pad;
  const rect = tooltipEl.getBoundingClientRect();
  if (x + rect.width > window.innerWidth) x = e.clientX - rect.width - pad;
  if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - pad;
  tooltipEl.style.left = x + "px";
  tooltipEl.style.top = y + "px";
}

function hideTooltip() {
  tooltipEl.classList.remove("show");
}

function buildTable(chips) {
  const root = document.getElementById("tableView");
  root.innerHTML = "";
  const table = document.createElement("table");
  table.className = "data";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const h of ["Ticker", "Strikes", "Expiry", "DTE", "P&L", "Decision zone", "Earnings", "News"]) {
    const th = document.createElement("th");
    th.textContent = h;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const sorted = [...chips].sort((a, b) => a.dte - b.dte);
  for (const c of sorted) {
    const tr = document.createElement("tr");
    const cells = [
      c.underlying,
      c.label.slice(c.underlying.length + 1),
      fmtDate(c.expiry),
      c.dte + "d",
      fmtMoney(c.pnl),
      c.inDecisionZone ? "Yes (≤" + c.zoneDays + "d)" : "—",
      c.earningsFlag ? fmtDate(c.earningsDate) : "—",
      c.news ? "Yes" : "—",
    ];
    cells.forEach((val, i) => {
      const td = document.createElement("td");
      td.textContent = val;
      if (i === 3 || i === 4) td.classList.add("num");
      if (i === 4) td.classList.add(c.gain ? "good" : "critical");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  root.appendChild(table);
}

function render() {
  const chips = filteredChips();
  buildFilters();
  buildStats(chips);
  buildCalendar(chips);
  buildGantt(chips);
  buildTable(chips);
}

document.getElementById("subtitle").textContent =
  DATA.chips.length + " open spreads · generated " +
  new Date(DATA.today + "T00:00:00").toLocaleDateString(undefined, {month: "long", day: "numeric", year: "numeric"});

const views = { calendar: document.getElementById("calendarView"), gantt: document.getElementById("ganttView"), table: document.getElementById("tableView") };
document.getElementById("views").addEventListener("click", e => {
  const btn = e.target.closest("button[data-view]");
  if (!btn) return;
  state.view = btn.dataset.view;
  document.querySelectorAll("#views button").forEach(b => b.classList.toggle("active", b === btn));
  for (const [name, el] of Object.entries(views)) el.classList.toggle("hidden", name !== state.view);
});

render();
</script>
</body>
</html>
"""
