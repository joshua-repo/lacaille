import { DATA } from "./data.js";
import { state } from "./state.js";
import { acctTickers, buildAccounts } from "./views/accounts.js";
import { buildCalendar } from "./views/calendar.js";
import { accountChips, buildFilters, filteredChips } from "./views/filters.js";
import { buildGantt } from "./views/gantt.js";
import { buildStats } from "./views/stats.js";
import { buildMarket } from "./views/market.js";
import { buildResearch } from "./views/research.js";
import { buildTable } from "./views/table.js";

/* Switching account re-renders everything below it too. Exported rather than
   imported into accounts.js the other way round for the same reason
   buildFilters takes a callback: render() builds the account cards, so the
   cards cannot import render() without a cycle -- but a function *declaration*
   is hoisted, so this direction is safe and needs no indirection. */
export function onAccountChange() {
  state.selected.clear();   // a ticker pill from another account means nothing here
  render();
}

export function render() {
  /* A cash account has no options, and a Positions region showing a lone "All"
     pill over a row of zeros and an empty calendar is three controls that can
     only ever say nothing. Hide the region and say so in one line. */
  const any = accountChips().length > 0;
  document.getElementById("positions").classList.toggle("hidden", !any);
  document.getElementById("positionsNone").classList.toggle("hidden", any);

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

/* Inside Analysis: what you own, and what the market is doing. The expiry
   views are not peers of Accounts -- they are ways of looking at the positions
   an account holds -- so they fold in under it rather than sitting beside it. */
export const views = {
  accounts: document.getElementById("accountsView"),
  market: document.getElementById("marketView"),
};

/* The three expiry views share one slot. Stacking them was three screens of
   scrolling to answer a question any one of them answers on its own. */
const posViews = {
  calendar: document.getElementById("calendarView"),
  gantt: document.getElementById("ganttView"),
  table: document.getElementById("tableView"),
};
document.getElementById("posViews").addEventListener("click", e => {
  const btn = e.target.closest("button[data-pos]");
  if (!btn) return;
  state.positions = btn.dataset.pos;
  document.querySelectorAll("#posViews button").forEach(b => b.classList.toggle("active", b === btn));
  for (const [name, node] of Object.entries(posViews)) node.classList.toggle("hidden", name !== state.positions);
});

document.getElementById("views").addEventListener("click", e => {
  const btn = e.target.closest("button[data-view]");
  if (!btn) return;
  state.view = btn.dataset.view;
  document.querySelectorAll("#views button").forEach(b => b.classList.toggle("active", b === btn));
  for (const [name, node] of Object.entries(views)) node.classList.toggle("hidden", name !== state.view);
  if (state.view === "market") buildMarket();
  // Tickers cannot animate inside a hidden pane; roll them on the way back.
  else acctTickers.forEach(ticker => ticker.replay());
});

render();
