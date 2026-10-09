import { emptyBody, emptyPanel, panel } from "../components/panel.js";
import { el } from "../dom.js";

/* Research > Results.
 *
 * What a combo wrote, read back from vela's runs folder. Two rules shape the
 * layout before a single run exists:
 *
 * - **Nothing here picks a winner.** The table lists every cell, with the
 *   in-sample and out-of-sample halves side by side and the null beside each
 *   gated cell, so a good-looking row is always read against the rest.
 * - **Absent is not zero.** A figure vela did not compute renders as a dash.
 */
const HALVES = ["In-sample", "Out-of-sample"];
const FIGURES = ["Trades", "t-stat", "Total P&L", "Sharpe"];

function cellsTable() {
  const table = el("table", "data");
  const thead = el("thead");

  const groups = el("tr");
  for (const h of ["", ""]) groups.appendChild(el("th", null, h));
  for (const half of HALVES) {
    const th = el("th", "group", half);
    th.colSpan = FIGURES.length;
    groups.appendChild(th);
  }
  groups.appendChild(el("th", null, ""));
  thead.appendChild(groups);

  const cols = el("tr");
  cols.appendChild(el("th", null, "Cell"));
  cols.appendChild(el("th", null, "Parameters"));
  for (let i = 0; i < HALVES.length; i++) {
    for (const f of FIGURES) cols.appendChild(el("th", "num", f));
  }
  cols.appendChild(el("th", "num", "Null"));
  thead.appendChild(cols);

  table.appendChild(thead);
  return table;
}

export function buildResults() {
  const root = document.getElementById("resultsTab");

  const {root: cells, body} = panel({
    title: "Cells",
    meta: "every configuration of the selected run, none hidden",
    tag: "needs vela runs",
    cls: "stack",
  });
  body.classList.add("flush");
  body.appendChild(cellsTable());
  body.appendChild(emptyBody("No run to show. A run is a folder vela writes; this table gets one row per cell in it.", 120));
  root.appendChild(cells);

  const grid = el("div", "panel-grid");
  const panes = [
    {title: "Equity", meta: "the selected cell's curve, with the in-sample boundary marked",
     tag: "needs vela runs", text: "Equity over the window, the null's curve behind it."},
    {title: "Parameter map", meta: "one figure across two axes of the grid",
     tag: "needs vela runs", text: "A heatmap of the grid, so the shape of the result is visible rather than one cell."},
    {title: "Trades", meta: "the selected cell's trades, entry to exit",
     tag: "needs vela runs", text: "One mark per trade, by date and return on risk."},
    {title: "Volatility surface", meta: "strike by expiry by IV, per session",
     tag: "needs a vela IV grid", text: "Stays empty until vela writes an IV grid per session."},
  ];
  for (const pane of panes) grid.appendChild(emptyPanel({...pane, height: 240}));
  root.appendChild(grid);
}
