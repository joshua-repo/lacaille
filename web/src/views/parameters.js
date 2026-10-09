import { panel } from "../components/panel.js";
import { el } from "../dom.js";
import { DASH } from "../format.js";

/* Research > Parameters.
 *
 * The shape of one combo config: four groups, and any value given as a list is
 * an axis of the grid. This is a read-only layout of that shape, not a form --
 * there is nothing to submit it to yet. When there is, the config file is the
 * hook: this page writes one and vela runs it.
 *
 * Field names follow vela's combo config, so the page and the file it will
 * write use one vocabulary.
 */
const GROUPS = [
  {title: "Data", meta: "the window every cell runs on, loaded once", fields: [
    ["symbol", "the underlying"],
    ["start", "first session"],
    ["end", "last session"],
    ["max_dte", "how far out the chain is read"],
    ["as_of", "optional: pin the read to one ingest"],
  ]},
  {title: "Split", meta: "mandatory: every cell is scored on both sides", fields: [
    ["in_sample_end", "choosing among cells uses only what is before this"],
  ]},
  {title: "Strategy", meta: "a list here is an axis", fields: [
    ["right", "P or C"],
    ["moneyness", "short strike / spot"],
    ["width", "dollars between strikes"],
    ["entry_dte", "the entry window, in days"],
    ["take_profit", "fraction of max profit"],
    ["stop_loss", "fraction of max loss"],
    ["exit_dte", "close at this many days"],
    ["gate", "none, or a signal with its threshold; none is the null"],
  ]},
  {title: "Execution", meta: "costs decide the sign of a result", fields: [
    ["haircut", "half-spreads crossed per leg"],
    ["commission", "dollars per contract"],
  ]},
];

function fieldRows(body, fields) {
  for (const [name, what] of fields) {
    const row = el("div", "kv");
    row.appendChild(el("code", "kv-key", name));
    row.appendChild(el("span", "kv-what", what));
    row.appendChild(el("span", "kv-val", DASH));
    body.appendChild(row);
  }
}

export function buildParameters() {
  const root = document.getElementById("parametersTab");
  const layout = el("div", "split-layout");

  /* Two columns of groups, filled so the heights come out close: the long
     group (Strategy) shares a column with the shortest ones. */
  const columns = [el("div"), el("div")];
  const placement = {Data: 0, Split: 0, Strategy: 1, Execution: 0};
  for (const group of GROUPS) {
    const {root: card, body} = panel({title: group.title, meta: group.meta});
    fieldRows(body, group.fields);
    columns[placement[group.title]].appendChild(card);
  }
  layout.append(...columns);

  const {root: grid, body} = panel({
    title: "Grid",
    meta: "the cartesian product of every axis",
    tag: "no config loaded",
  });
  fieldRows(body, [
    ["axes", "values given as lists"],
    ["cells", "how many configurations were tried"],
    ["config", "the file this grid was read from"],
  ]);
  body.appendChild(el("div", "note",
    "Every cell is written, including the ones that lose and the ones that never trade. The count is kept so the best cell can be weighed against the number of tries."));
  layout.appendChild(grid);

  root.appendChild(layout);
}
