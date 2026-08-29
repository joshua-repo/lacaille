import { fmtDate, fmtMoney } from "../format.js";

export function buildTable(chips) {
  const root = document.getElementById("tableView");
  root.innerHTML = "";
  const table = document.createElement("table");
  table.className = "data";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const h of ["Ticker", "Strikes", "Expiry", "DTE", "P&L", "Decision zone", "Earnings", "News"]) {
    const th = document.createElement("th");
    th.textContent = h;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const sorted = [...chips].sort((a, b) => a.dte - b.dte);
  for (const c of sorted) {
    const tr = document.createElement("tr");
    const cells = [
      c.underlying,
      c.label.slice(c.underlying.length + 1),
      fmtDate(c.expiry),
      c.dte + "d",
      fmtMoney(c.pnl),
      c.inDecisionZone ? "Yes (≤" + c.zoneDays + "d)" : "—",
      c.earningsFlag ? fmtDate(c.earningsDate) : "—",
      c.news ? "Yes" : "—",
    ];
    cells.forEach((val, i) => {
      const td = document.createElement("td");
      td.textContent = val;
      if (i === 3 || i === 4) td.classList.add("num");
      if (i === 4) td.classList.add(c.gain ? "good" : "critical");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  root.appendChild(table);
}
