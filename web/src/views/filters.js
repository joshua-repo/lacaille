import { DATA } from "../data.js";
import { state } from "../state.js";

export function underlyings() {
  return [...new Set(DATA.chips.map(c => c.underlying))].sort();
}

export function filteredChips() {
  if (state.selected.size === 0) return DATA.chips;
  return DATA.chips.filter(c => state.selected.has(c.underlying));
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
