import { emptyBody, panel } from "../components/panel.js";
import { DATA } from "../data.js";
import { el } from "../dom.js";
import { DASH } from "../format.js";

/* Analysis > Portfolio.
 *
 * A watchlist, not a book: what is being watched, kept by hand in a file, with
 * no broker behind it. Holdings, balances and P&L used to live here and do not
 * any more -- the question this tab answers is "what am I looking at", not
 * "what is it worth".
 *
 * The quote columns are part of the layout and empty on purpose. They wait on
 * a market-data layer in antlia; pictor does not reach a vendor to fill them.
 */

const SAMPLE = [
  "[[symbol]]",
  'ticker = "XXXX"',
  'note = "why it is on the list"',
  'tags = ["sector", "theme"]',
].join("\n");

const QUOTE_COLUMNS = ["Last", "Change", "IV rank"];

export function watched() {
  return DATA.watchlist ? DATA.watchlist.symbols : [];
}

export function buildPortfolio() {
  const root = document.getElementById("portfolioTab");
  const list = DATA.watchlist;
  const symbols = watched();

  const {root: card, body} = panel({
    title: "Watchlist",
    meta: list
      ? list.path + " · " + symbols.length + (symbols.length === 1 ? " symbol" : " symbols")
      : "no watchlist was given to this page",
    tag: "quotes need antlia live/",
  });

  if (!symbols.length) {
    /* Three different empties, worded apart: no file, a file that lists
       nothing, and a caller that never passed one. */
    const why = !list ? "This page was rendered without a watchlist."
      : !list.found ? "No watchlist file at " + list.path + "."
      : list.path + " lists no symbols.";
    const empty = emptyBody(why + " One [[symbol]] table per row:");
    empty.appendChild(el("pre", "sample", SAMPLE));
    body.appendChild(empty);
    root.appendChild(card);
    return;
  }

  const table = el("table", "data");
  const head = el("tr");
  for (const h of ["Ticker", "Note", "Tags", ...QUOTE_COLUMNS]) {
    const th = el("th", QUOTE_COLUMNS.includes(h) ? "num" : null, h);
    head.appendChild(th);
  }
  const thead = el("thead");
  thead.appendChild(head);
  table.appendChild(thead);

  const tbody = el("tbody");
  for (const s of symbols) {
    const tr = el("tr");
    tr.appendChild(el("td", "sym", s.ticker));
    tr.appendChild(el("td", "muted", s.note || ""));
    const tags = el("td");
    for (const t of s.tags) tags.appendChild(el("span", "tagchip", t));
    tr.appendChild(tags);
    for (let i = 0; i < QUOTE_COLUMNS.length; i++) tr.appendChild(el("td", "num muted", DASH));
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  body.classList.add("flush");
  body.appendChild(table);
  card.appendChild(el("div", "note pad",
    "Last, Change and IV rank stay empty until there is a market-data layer to read them from. Nothing on this tab is fetched."));
  root.appendChild(card);
}
