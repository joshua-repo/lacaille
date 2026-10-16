import { emptyPanel, regionTitle } from "../components/panel.js";
import { el } from "../dom.js";

/* Research > Data.
 *
 * Three questions, top to bottom: what can be run to get data, what is already
 * held, and is what is held fit to backtest on.
 *
 * The jobs are other projects' commands, shown in the order they depend on
 * each other. pictor does not run them: there is no backend to run them
 * through, so there is no Run button -- a button that cannot work is not drawn.
 * Fetching stays antlia's (it is the only layer that talks to a vendor) and
 * the readiness judgement stays vela's (it depends on vela's own guards), so
 * when these are wired, this page triggers and displays; it does not decide.
 */
const JOBS = [
  {name: "plan", owner: "antlia", command: "antlia history plan",
   what: "What a fill would ask the vendor for, without asking."},
  {name: "fill", owner: "antlia", command: "antlia history fill",
   what: "Fetch what is missing and append it to the store. Spends metered requests."},
  {name: "check", owner: "antlia", command: "antlia history check",
   what: "Unreadable files, leaked writes, ledger mismatches."},
  {name: "readiness", owner: "vela", command: "vela check",
   what: "Is this window runnable, and if not, why. Writes readiness.json.", pending: true},
  {name: "combo", owner: "vela", command: "vela combo",
   what: "Run every cell of a parameter grid against one pinned dataset.", pending: true},
];

function jobNode(job) {
  const node = el("div", "dag-node");
  const head = el("div", "dag-hd");
  head.appendChild(el("span", "dag-name", job.name));
  head.appendChild(el("span", "dag-owner", job.owner));
  node.appendChild(head);
  node.appendChild(el("code", "dag-cmd", job.command));
  node.appendChild(el("div", "dag-what", job.what));
  node.appendChild(el("div", "dag-state", job.pending ? "not built in vela yet" : "not wired"));
  return node;
}

export function buildData() {
  const root = document.getElementById("dataTab");

  root.appendChild(regionTitle("Jobs"));
  const dag = el("div", "dag");
  for (const job of JOBS) dag.appendChild(jobNode(job));
  root.appendChild(dag);
  root.appendChild(el("div", "note",
    "Shown in dependency order, left to right. Nothing is triggered from this page yet; the commands are the ones each project already ships or has planned."));

  root.appendChild(regionTitle("Datasets"));
  const grid = el("div", "panel-grid wide");
  grid.appendChild(emptyPanel({
    title: "Cache",
    meta: "what the store holds: symbol, table, date range, last ingest",
    tag: "needs a store read",
    text: "One row per symbol and table, with the dates held drawn as a band and the gaps left open.",
    height: 260,
  }));
  grid.appendChild(emptyPanel({
    title: "Quality",
    meta: "per window: held, missing, denied, sessions without a chain, divergent sessions",
    tag: "needs vela check",
    text: "One readiness report per checked window. A refusal is a result and is listed with its reason.",
    height: 260,
  }));
  root.appendChild(grid);
}
