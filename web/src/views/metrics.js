import { emptyPanel } from "../components/panel.js";
import { el } from "../dom.js";

/* Analysis > Metrics.
 *
 * The usual ways of looking at a list of instruments, one pane each, laid out
 * so the grid can be judged before any of it is wired. Every pane names the
 * layer it waits on, because "where would this number come from" has a
 * different answer per pane: prices are antlia's, implied volatility is
 * pricing and so vela's, and nothing here is pictor's to compute.
 */
const PANES = [
  {title: "Price & returns", meta: "close and cumulative return, per watched symbol",
   tag: "needs antlia live/", text: "A line per symbol, rebased to the start of the window."},
  {title: "Realized volatility", meta: "rolling close-to-close, by window",
   tag: "needs antlia live/", text: "Annualised volatility over short, medium and long windows."},
  {title: "Drawdown", meta: "depth and duration from the running peak",
   tag: "needs antlia live/", text: "Underwater curve per symbol, with the current drawdown called out."},
  {title: "Correlation", meta: "pairwise return correlation across the watchlist",
   tag: "needs antlia live/", text: "A symbol-by-symbol matrix over the selected window."},
  {title: "Implied volatility", meta: "IV rank and term structure",
   tag: "needs an IV source", text: "Where each symbol's implied volatility sits in its own history, and across expiries."},
  {title: "Events", meta: "earnings dates and headlines for the watchlist",
   tag: "not wired", text: "What is scheduled, and what just happened, per symbol."},
];

export function buildMetrics() {
  const root = document.getElementById("metricsTab");
  const grid = el("div", "panel-grid wide");
  for (const pane of PANES) grid.appendChild(emptyPanel({...pane, height: 220}));
  root.appendChild(grid);
}
