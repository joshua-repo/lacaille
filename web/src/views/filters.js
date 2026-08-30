import { DATA } from "../data.js";
import { state } from "../state.js";

export function underlyings() {
  // Only the tickers the selected account actually holds; offering a pill that
  // can only ever produce an empty view is a dead control.
  return [...new Set(accountChips().map(c => c.underlying))].sort();
}

/* Two filters, and they are different in kind. The account tab decides *whose*
   positions these are -- a Trading212 tab must not show spreads held at IBKR,
   which is a correctness question. The ticker pills are a lens on whatever is
   left. */
export function accountChips() {
  if (state.account === "all") return DATA.chips;
  return DATA.chips.filter(c => c.source === state.account);
}

export function filteredChips() {
  const chips = accountChips();
  if (state.selected.size === 0) return chips;
  return chips.filter(c => state.selected.has(c.underlying));
}

/* `onChange` rather than a direct call to render(): the filter row triggering
   a re-render, while render() builds the filter row, is a genuine import cycle.
   Passing the callback in inverts it -- this module no longer knows what a
   re-render is, which is also what makes it testable on its own. */
export function buildFilters(onChange) {
  const root = document.getElementById("filters");
  root.querySelectorAll(".pill").forEach(el => el.remove());

  const allPill = document.createElement("button");
  allPill.className = "pill" + (state.selected.size === 0 ? " active" : "");
  allPill.textContent = "All";
  allPill.addEventListener("click", () => {
    state.selected.clear();
    onChange();
  });
  root.appendChild(allPill);

  for (const tk of underlyings()) {
    const pill = document.createElement("button");
    pill.className = "pill" + (state.selected.has(tk) ? " active" : "");
    pill.textContent = tk;
    pill.addEventListener("click", () => {
      if (state.selected.has(tk)) state.selected.delete(tk);
      else state.selected.add(tk);
      onChange();
    });
    root.appendChild(pill);
  }
}
