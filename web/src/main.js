import { DATA } from "./data.js";
import { state } from "./state.js";
import { acctTickers, buildAccounts } from "./views/accounts.js";
import { buildCalendar } from "./views/calendar.js";
import { buildFilters, filteredChips } from "./views/filters.js";
import { buildGantt } from "./views/gantt.js";
import { buildStats } from "./views/stats.js";
import { buildResearch } from "./views/research.js";
import { buildTable } from "./views/table.js";

export function render() {
  const chips = filteredChips();
  buildFilters(render);
  buildStats(chips);
  buildCalendar(chips);
  buildGantt(chips);
  buildTable(chips);
  buildAccounts();
}

/* Workspaces. Analysis is live broker state; Research runs over fixed datasets
   and is a placeholder until Vela produces them. Switching hides one pane and
   shows the other -- the view tabs belong to Analysis, so they go with it. */
const panes = {
  analysis: document.getElementById("analysisWs"),
  research: document.getElementById("researchWs"),
};
const wsTitle = document.getElementById("wsTitle");

document.getElementById("workspaces").addEventListener("click", e => {
  const btn = e.target.closest("button[data-ws]");
  if (!btn) return;
  state.workspace = btn.dataset.ws;
  document.querySelectorAll("#workspaces button").forEach(b => b.classList.toggle("active", b === btn));
  for (const [name, pane] of Object.entries(panes)) pane.classList.toggle("hidden", name !== state.workspace);
  wsTitle.textContent = btn.textContent;
  setSubtitle();
  if (state.workspace === "research") buildResearch();
  // Tickers cannot animate inside a hidden pane, so re-roll on the way back.
  else if (state.view === "accounts") acctTickers.forEach(t => t.replay());
});

function setSubtitle() {
  document.getElementById("subtitle").textContent = state.workspace === "research"
    ? "fixed datasets · backtests, sweeps and deep dives"
    : DATA.chips.length + " open spreads · generated " +
      new Date(DATA.today + "T00:00:00").toLocaleDateString(undefined, {month: "long", day: "numeric", year: "numeric"});
}

setSubtitle();

export const views = {
  calendar: document.getElementById("calendarView"),
  gantt: document.getElementById("ganttView"),
  table: document.getElementById("tableView"),
  accounts: document.getElementById("accountsView"),
};
if (DATA.accounts.length) document.getElementById("accountsTab").classList.remove("hidden");

document.getElementById("views").addEventListener("click", e => {
  const btn = e.target.closest("button[data-view]");
  if (!btn) return;
  state.view = btn.dataset.view;
  document.querySelectorAll("#views button").forEach(b => b.classList.toggle("active", b === btn));
  for (const [name, node] of Object.entries(views)) node.classList.toggle("hidden", name !== state.view);
  // The ticker filter, the stat row and the legend all describe spreads;
  // none of them says anything about an account balance.
  const spreadView = state.view !== "accounts";
  document.querySelectorAll(".spread-only").forEach(node => node.classList.toggle("hidden", !spreadView));
  // Tickers built inside a hidden tab could not animate; roll them now.
  if (state.view === "accounts") acctTickers.forEach(ticker => ticker.replay());
});

render();
