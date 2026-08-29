import { fmtDate, fmtMoney } from "../format.js";

export const tooltipEl = document.getElementById("tooltip");

export function showTooltip(e, c) {
  tooltipEl.innerHTML = "";
  const title = document.createElement("div");
  title.innerHTML = "<b></b>";
  title.querySelector("b").textContent = c.label;
  tooltipEl.appendChild(title);

  const rows = [
    ["Expiry", fmtDate(c.expiry) + " (" + c.dte + "d)"],
    ["Unrealized P&L", fmtMoney(c.pnl)],
  ];
  if (c.inDecisionZone) rows.push(["Decision zone", "within " + c.zoneDays + "d of expiry"]);
  if (c.earningsFlag) rows.push(["Earnings", fmtDate(c.earningsDate) + " (before expiry)"]);
  if (c.news) rows.push(["News", "recent headline"]);

  for (const [k, v] of rows) {
    const row = document.createElement("div");
    row.className = "row";
    const kEl = document.createElement("span");
    kEl.textContent = k;
    const vEl = document.createElement("b");
    vEl.textContent = v;
    row.append(kEl, vEl);
    tooltipEl.appendChild(row);
  }

  tooltipEl.classList.add("show");
  positionTooltip(e);
}

export function positionTooltip(e) {
  const pad = 14;
  let x = e.clientX + pad;
  let y = e.clientY + pad;
  const rect = tooltipEl.getBoundingClientRect();
  if (x + rect.width > window.innerWidth) x = e.clientX - rect.width - pad;
  if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - pad;
  tooltipEl.style.left = x + "px";
  tooltipEl.style.top = y + "px";
}

export function hideTooltip() {
  tooltipEl.classList.remove("show");
}

/* Attaching the tooltip to one element is tooltip business, and both spread
   views need it -- it does not belong to whichever view happened to define it
   first. */
export function wireHover(el, c) {
  el.addEventListener("pointerenter", e => showTooltip(e, c));
  el.addEventListener("pointermove", e => positionTooltip(e));
  el.addEventListener("pointerleave", hideTooltip);
  el.tabIndex = 0;
  el.addEventListener("focus", e => showTooltip(e, c));
  el.addEventListener("blur", hideTooltip);
}
