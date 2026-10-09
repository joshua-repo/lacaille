/* One segmented control, wired once. The page has three of them -- the
   workspace switch and a tab row per workspace -- and they differ only in
   which data attribute names the target and what happens after the swap, so
   those are the two things a caller passes in.

   `panes` maps a button's value to the node it reveals. `onShow` runs after
   the swap, so whatever it does sees the new pane already on screen. */
export function wireTabs(bar, attr, panes, onShow) {
  bar.addEventListener("click", e => {
    const btn = e.target.closest("button[data-" + attr + "]");
    if (!btn) return;
    const name = btn.dataset[attr];
    bar.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === btn));
    for (const [key, pane] of Object.entries(panes)) pane.classList.toggle("hidden", key !== name);
    if (onShow) onShow(name);
  });
}
