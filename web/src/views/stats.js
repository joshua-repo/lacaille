import { makeTicker } from "../components/ticker.js";
import { el } from "../dom.js";
import { fmtMoney, int0 } from "../format.js";

export const statTickers = [];

export function buildStats(chips) {
  const netPnl = chips.reduce((sum, c) => sum + c.pnl, 0);
  const zoneCount = chips.filter(c => c.inDecisionZone).length;
  const earningsCount = chips.filter(c => c.earningsFlag).length;

  const stats = [
    {label: "Open spreads", value: chips.length, format: int0},
    {label: "Net unrealized P&L", value: netPnl, format: fmtMoney, cls: netPnl >= 0 ? "good" : "critical"},
    {label: "In decision zone", value: zoneCount, format: int0},
    {label: "Earnings collisions", value: earningsCount, format: int0},
  ];

  /* Built once, then updated. Keeping the ticker instances alive is the
     whole point: on a filter change the digits roll from the previous
     number to the new one, which a rebuild would turn back into a snap. */
  const el = document.getElementById("stats");
  if (!statTickers.length) {
    for (const s of stats) {
      const div = document.createElement("div");
      div.className = "stat";
      const label = document.createElement("div");
      label.className = "label";
      label.textContent = s.label;
      const value = document.createElement("div");
      value.className = "value";
      const ticker = makeTicker(s.format);
      value.appendChild(ticker.el);
      div.append(label, value);
      el.appendChild(div);
      statTickers.push(ticker);
    }
  }
  stats.forEach((s, i) => {
    statTickers[i].el.classList.toggle("good", s.cls === "good");
    statTickers[i].el.classList.toggle("critical", s.cls === "critical");
    statTickers[i].set(s.value);
  });
}
