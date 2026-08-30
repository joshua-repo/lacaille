import { el } from "../dom.js";

/* The Research workspace.
 *
 * A placeholder on purpose, and an honest one: it says what will live here and
 * what it is waiting on, rather than mocking up controls that do nothing. A
 * fake chart in an empty workspace is worse than an empty workspace, because
 * the next person cannot tell which parts are real.
 *
 * The distinction that earns this its own workspace is the *data*, not the
 * layout. Analysis reads live broker state -- stale the instant it arrives, so
 * every figure there is "right now". Research runs over a fixed dataset, which
 * is the only thing that makes a backtest repeatable: the same inputs have to
 * give the same answer tomorrow. Those two kinds of number should not sit in
 * one view, because one of them moves under your cursor and the other must not.
 *
 * The work itself belongs to Vela; pictor's job here stays what it is in
 * Analysis -- read what another layer produced and render it.
 */

const PLANNED = [
  ["Backtests", "One strategy over a fixed window, with the dataset and its date range stated on the result."],
  ["Parameter sweeps", "The same strategy across a grid of parameters, so the shape of the result is visible rather than one lucky cell."],
  ["Deep dives", "One instrument, or a set of them, examined on their own terms -- chain, surface, history."],
];

export function buildResearch() {
  const root = document.getElementById("researchWs");
  if (root.childElementCount) return;   // built once; nothing here is live

  const card = el("section", "acct placeholder");
  const head = el("div", "acct-hd");
  const left = el("div");
  left.appendChild(el("h2", null, "Research"));
  left.appendChild(el("div", "acct-meta", "fixed datasets · nothing here is live"));
  head.appendChild(left);
  head.appendChild(el("span", "acct-tag", "waiting on vela"));
  card.appendChild(head);

  const body = el("div", "acct-rows");
  body.appendChild(el("p", "ph-lede",
    "Analysis answers what you hold right now, off a broker snapshot that is stale the "
    + "moment it is read. Research answers what a strategy would have done, off a dataset "
    + "that does not move -- which is the whole reason a backtest can be repeated."));
  const list = el("div", "ph-list");
  for (const [name, what] of PLANNED) {
    const item = el("div", "ph-item");
    item.appendChild(el("div", "sym", name));
    item.appendChild(el("div", "qty", what));
    list.appendChild(item);
  }
  body.appendChild(list);
  body.appendChild(el("div", "note",
    "Vela computes these; pictor renders them. Until it lands there is deliberately "
    + "nothing to click here."));
  card.appendChild(body);
  root.appendChild(card);
}
