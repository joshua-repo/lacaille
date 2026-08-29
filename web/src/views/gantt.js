import { DATA } from "../data.js";
import { wireHover } from "../components/tooltip.js";
import { starIcon } from "../dom.js";

export function buildGantt(chips) {
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

export function pct(value, max) {
  return Math.max(0, Math.min(100, (value / max) * 100)) + "%";
}
