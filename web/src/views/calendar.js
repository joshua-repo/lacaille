import { starIcon } from "../dom.js";
import { wireHover } from "../components/tooltip.js";
import { DATA } from "../data.js";
import { toLocalIso } from "../format.js";

export function chipsByDate(chips) {
  const map = {};
  for (const c of chips) {
    if (!map[c.expiry]) map[c.expiry] = [];
    map[c.expiry].push(c);
  }
  return map;
}

export function buildCalendar(chips) {
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

  // The months grid does the wrapping; how many fit is the CSS's call, not
  // this function's.
  const grid = document.createElement("div");
  grid.className = "months";
  root.appendChild(grid);

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
    grid.appendChild(card);
  }
}

export function buildChip(c) {
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

