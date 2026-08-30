import { buildPlaceholder } from "../components/placeholder.js";

/* The Research workspace.
 *
 * What earns this its own workspace is the *data*, not the layout. Analysis
 * reads live broker state -- stale the instant it arrives, so every figure
 * there is "right now". Research runs over a fixed dataset, which is the only
 * thing that makes a backtest repeatable: the same inputs have to give the same
 * answer tomorrow. Those two kinds of number should not share a view, because
 * one moves under your cursor and the other must not.
 *
 * The work belongs to Vela; pictor's job here stays what it is in Analysis --
 * render what another layer produced.
 */
export function buildResearch() {
  buildPlaceholder(document.getElementById("researchWs"), {
    title: "Research",
    meta: "fixed datasets · nothing here is live",
    tag: "waiting on vela",
    lede: "Analysis answers what you hold right now, off a broker snapshot that is stale the "
        + "moment it is read. Research answers what a strategy would have done, off a dataset "
        + "that does not move -- which is the whole reason a backtest can be repeated.",
    items: [
      ["Backtests", "One strategy over a fixed window, with the dataset and its date range stated on the result."],
      ["Parameter sweeps", "The same strategy across a grid of parameters, so the shape of the result is visible rather than one lucky cell."],
      ["Deep dives", "One instrument, or a set of them, examined on their own terms -- chain, surface, history."],
    ],
    note: "Vela computes these; pictor renders them. Until it lands there is deliberately nothing to click here.",
  });
}
