import { makeTicker } from "../components/ticker.js";
import { DATA, FX } from "../data.js";
import { el } from "../dom.js";
import { DASH, fmtCcy, int0, pct1 } from "../format.js";
import { convert, fxNodes, refreshFx } from "../fx.js";
import { state } from "../state.js";

export const acctTickers = [];


/* A money figure, as a rolling ticker. `value` is stated in `currency`; what
   gets shown is the display currency, falling back to the native one when the
   rate table cannot make the trip (or when "Native" is selected). The
   currency actually shown is tracked per node so the symbol never contradicts
   the number in front of it. */
export function moneyFigure(value, currency, cls) {
  if (value === null || value === undefined) return el("span", "value-sm" + (cls ? " " + cls : ""), DASH);
  let shown = currency;
  const ticker = makeTicker(v => fmtCcy(v, shown), "value-sm" + (cls ? " " + cls : ""));
  acctTickers.push(ticker);
  fxNodes.push(() => {
    const converted = state.display === "native" ? null : convert(value, currency, state.display);
    shown = converted === null ? currency : state.display;
    ticker.set(converted === null ? value : converted);
  });
  return ticker.el;
}


/* Money that lives in a caption rather than in a ticker. Same conversion,
   same fallback, no wheel. */
export function moneyText(node, prefix, value, currency) {
  fxNodes.push(() => {
    if (value === null || value === undefined) { node.textContent = ""; return; }
    const converted = state.display === "native" ? null : convert(value, currency, state.display);
    node.textContent = prefix + fmtCcy(converted === null ? value : converted, converted === null ? currency : state.display);
  });
  return node;
}

export function cell(label, node, sub, extra) {
  const div = el("div", "cell" + (extra ? " " + extra : ""));
  div.appendChild(el("div", "label", label));
  div.appendChild(node);
  if (sub) div.appendChild(typeof sub === "string" ? el("div", "sub", sub) : sub);
  return div;
}


/* A plain (non-money) figure: counts and percentages, which no exchange rate
   touches. */
export function figure(value, format, cls) {
  if (value === null || value === undefined) return el("span", "value-sm", DASH);
  const ticker = makeTicker(format, "value-sm" + (cls ? " " + cls : ""));
  acctTickers.push(ticker);
  ticker.set(value);
  return ticker.el;
}

export function currencyPicker() {
  const wrap = el("div", "fx-pick");
  wrap.appendChild(el("span", "fl", "Show in"));
  const options = [...FX.currencies, "native"];
  for (const code of options) {
    const button = el("button", "pill" + (code === state.display ? " active" : ""), code === "native" ? "Native" : code);
    button.dataset.ccy = code;
    button.addEventListener("click", () => {
      state.display = code;
      wrap.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === button));
      refreshFx();
    });
    wrap.appendChild(button);
  }
  return wrap;
}


/* The combined card. This is the one place pictor adds figures from accounts
   in different currencies, and it is only defensible because the rate and its
   timestamp are stated right underneath -- see the note it carries. */
export function buildTotalCard(accounts) {
  const readable = accounts.filter(a => a.ok);
  if (!FX || readable.length < 2) return null;

  const card = el("section", "acct total");
  const head = el("div", "acct-hd");
  const left = el("div");
  left.appendChild(el("h2", null, "All accounts"));
  const meta = el("div", "acct-meta");
  left.appendChild(meta);
  head.appendChild(left);
  card.appendChild(head);

  // "Native" cannot express a total, so the combined figures fall back to the
  // rate table's own pivot and the caption says which currency that is.
  const totalIn = () => (state.display === "native" ? FX.base : state.display);
  // "Native" is a coherent answer for a single account and no answer at all
  // for a total, so the caption names the currency the total fell back to.
  fxNodes.push(() => {
    meta.textContent = readable.length + " accounts · " + readable.map(a => a.currency).join(" + ")
      + " · totalled in " + totalIn() + (state.display === "native" ? " (pivot currency)" : "");
  });
  const sum = pick => () => {
    let total = 0;
    for (const a of readable) {
      const converted = convert(pick(a), a.currency, totalIn());
      if (converted === null) return null;   // one unconvertible leg voids the total
      total += converted;
    }
    return total;
  };

  const body = el("div", "acct-body");
  const totalCell = (label, pick, colour) => {
    let shown = FX.base;
    const ticker = makeTicker(v => fmtCcy(v, shown), "value-sm" + (label === "Net liquidation" ? " tk-lg" : ""));
    acctTickers.push(ticker);
    fxNodes.push(() => {
      const total = sum(pick)();
      shown = totalIn();
      if (total === null) { ticker.el.textContent = DASH; return; }
      ticker.set(total);
      if (colour) {
        ticker.el.classList.toggle("good", total >= 0);
        ticker.el.classList.toggle("critical", total < 0);
      }
    });
    return ticker.el;
  };

  body.appendChild(cell("Net liquidation", totalCell("Net liquidation", a => a.netLiquidation), null, "hero"));
  body.appendChild(cell("Cash", totalCell("Cash", a => a.cash)));
  body.appendChild(cell("Unrealized P&L", totalCell("P&L", a => a.unrealizedPnl, true)));
  card.appendChild(body);

  const rows = el("div", "acct-rows");
  rows.appendChild(el("h3", null, "Contribution"));
  for (const a of readable) {
    const row = el("div", "hold");
    const name = el("div");
    name.appendChild(el("div", "sym", a.label));
    name.appendChild(el("div", "qty", a.account));
    const track = el("div", "track");
    const bar = document.createElement("i");
    track.appendChild(bar);
    const amt = el("div");
    const main = el("div", "amt");
    const native = el("div", "qty");
    amt.append(main, native);
    fxNodes.push(() => {
      const target = totalIn();
      const converted = convert(a.netLiquidation, a.currency, target);
      const total = sum(x => x.netLiquidation)();
      main.textContent = converted === null ? DASH : fmtCcy(converted, target);
      // The native figure stays visible: it is the number the broker itself
      // shows, and the converted one is derived from it.
      native.textContent = a.currency === target || a.netLiquidation === null
        ? "" : fmtCcy(a.netLiquidation, a.currency);
      bar.style.width = (total && converted !== null ? Math.abs(converted / total) * 100 : 0) + "%";
    });
    row.append(name, track, amt);
    rows.appendChild(row);
  }

  const note = el("div", "note" + (FX.stale ? " warn" : ""));
  // A daily bar (yfinance) and a daily fixing (frankfurter) both land on
  // midnight-or-16:00 of a date; printing "12:00 AM" against one would claim a
  // precision the rate does not have.
  const stamp = new Date(FX.asOf);
  const when = stamp.getHours() === 0 && stamp.getMinutes() === 0
    ? stamp.toLocaleDateString(undefined, {dateStyle: "medium"})
    : stamp.toLocaleString(undefined, {dateStyle: "medium", timeStyle: "short"});
  note.textContent = (FX.stale ? "STALE RATES — every live source failed; last known table from " : "Converted at " + FX.source + " rates, ")
    + when + ". P&L restated this way moves with the exchange rate as well as with the positions.";
  rows.appendChild(note);
  card.appendChild(rows);
  return card;
}

export function buildAccountCard(a) {
  const card = el("section", "acct" + (a.ok ? "" : " failed"));

  const head = el("div", "acct-hd");
  const left = el("div");
  left.appendChild(el("h2", null, a.label));
  const bits = [a.account || a.source, a.profile];
  if (a.asOf) bits.push("as of " + new Date(a.asOf).toLocaleTimeString(undefined, {hour: "2-digit", minute: "2-digit"}));
  left.appendChild(el("div", "acct-meta", bits.filter(Boolean).join("  ·  ")));
  head.appendChild(left);
  if (a.ok && a.currency) {
    // The badge says what the account is denominated in, and what it is being
    // shown in when those differ -- so a converted number is never mistaken
    // for the broker's own.
    const tag = el("span", "acct-tag");
    fxNodes.push(() => {
      const target = state.display === "native" ? a.currency : state.display;
      tag.textContent = target === a.currency || !FX ? a.currency : a.currency + " → " + target;
    });
    head.appendChild(tag);
  }
  card.appendChild(head);

  if (!a.ok) {
    // The reason, verbatim. A broker that cannot be read is a fact about the
    // gateway or the key, and paraphrasing it would only cost debugging time.
    card.appendChild(el("div", "err", a.error));
    return card;
  }

  const body = el("div", "acct-body");
  body.appendChild(cell("Net liquidation", moneyFigure(a.netLiquidation, a.currency, "tk-lg"), null, "hero"));
  body.appendChild(cell("Cash", moneyFigure(a.cash, a.currency, a.cash !== null && a.cash < 0 ? "critical" : null),
    a.cash !== null && a.cash < 0 ? "borrowed against the account" : null));
  body.appendChild(cell("Unrealized P&L",
    moneyFigure(a.unrealizedPnl, a.currency, a.unrealizedPnl === null ? null : (a.unrealizedPnl >= 0 ? "good" : "critical"))));

  // A cash account leading with "Option legs: 0" says nothing; it reports
  // what it actually holds instead.
  if (a.optionCount === 0 && a.equityCount > 0) {
    body.appendChild(cell("Share lines", figure(a.equityCount, int0), "no options in this account"));
  } else {
    body.appendChild(cell("Option legs", figure(a.optionCount, int0),
      a.equityCount + (a.equityCount === 1 ? " share line" : " share lines")));
  }

  if (a.margin) {
    const m = a.margin;
    const used = cell("Margin used", figure(m.utilisation, pct1),
      m.maintenance === null ? null : moneyText(el("div", "sub"), "maintenance ", m.maintenance, a.currency));
    if (m.utilisation !== null) {
      // A meter, so it is data colour, not chrome: room / getting close / past.
      const level = m.utilisation >= 0.8 ? " crit" : m.utilisation >= 0.5 ? " warn" : "";
      const meter = el("div", "meter" + level);
      const fill = el("span");
      fill.style.width = Math.min(100, Math.max(0, m.utilisation * 100)) + "%";
      meter.appendChild(fill);
      used.appendChild(meter);
    }
    body.appendChild(used);
    body.appendChild(cell("Excess liquidity", moneyFigure(m.excess, a.currency),
      m.cushion === null ? null : "cushion " + pct1(m.cushion)));
    body.appendChild(cell("Buying power", moneyFigure(m.buyingPower, a.currency)));
  } else {
    body.appendChild(cell("Account type", el("span", "value-sm", "Cash"), "no margin reported"));
  }
  card.appendChild(body);

  if (a.holdings.length) {
    const rows = el("div", "acct-rows");
    rows.appendChild(el("h3", null, "Top holdings"));
    // Ranked on the account-base value, so a JPY line and a USD line are
    // compared on what they are worth rather than on the size of the number.
    const peak = Math.max(...a.holdings.map(h => Math.abs(h.baseValue || 0)), 1);
    for (const h of a.holdings) {
      const row = el("div", "hold");
      const name = el("div");
      name.appendChild(el("div", "sym", h.symbol));
      name.appendChild(el("div", "qty", h.quantity.toLocaleString() + (Math.abs(h.quantity) === 1 ? " share" : " shares")));
      const track = el("div", "track");
      const bar = document.createElement("i");
      bar.style.width = (Math.abs(h.baseValue || 0) / peak * 100) + "%";
      track.appendChild(bar);
      const amt = el("div");
      // The instrument's own currency stays the headline -- that is the price
      // it actually trades at -- with the display currency underneath it.
      amt.appendChild(el("div", "amt", h.marketValue === null ? DASH : fmtCcy(h.marketValue, h.currency || a.currency)));
      const converted = el("div", "qty");
      fxNodes.push(() => {
        const target = state.display === "native" ? h.baseCurrency : state.display;
        const value = convert(h.marketValue, h.currency || a.currency, target);
        converted.textContent = value === null || target === (h.currency || a.currency) ? "" : "≈ " + fmtCcy(value, target);
      });
      amt.appendChild(converted);
      row.append(name, track, amt);
      rows.appendChild(row);
    }
    card.appendChild(rows);
  }

  if (a.currencies.length > 1) {
    const rows = el("div", "acct-rows");
    rows.appendChild(el("h3", null, "Currencies"));
    // Native throughout on purpose: this section exists to show the split
    // between currencies, which converting them away would erase.
    for (const cur of a.currencies) {
      const row = el("div", "ccy-row");
      row.appendChild(el("b", null, cur.currency));
      if (cur.cash !== null) row.appendChild(el("span", null, "cash " + fmtCcy(cur.cash, cur.currency)));
      if (cur.netLiquidation !== null) row.appendChild(el("span", null, "net liq " + fmtCcy(cur.netLiquidation, cur.currency)));
      if (cur.rate !== null && cur.currency !== a.currency) {
        row.appendChild(el("span", null, "1 " + cur.currency + " = " + cur.rate.toPrecision(4) + " " + a.currency + " (broker)"));
      }
      rows.appendChild(row);
    }
    card.appendChild(rows);
  }

  if (a.unavailable.length) {
    const note = el("div", "acct-rows");
    // Worth stating rather than hiding: it is why a list is empty.
    note.appendChild(el("div", "note", "Not permitted by this key: " + a.unavailable.join("; ")));
    card.appendChild(note);
  }
  return card;
}

export function buildAccounts() {
  const root = document.getElementById("accountsView");
  if (!DATA.accounts.length) return;
  root.innerHTML = "";
  acctTickers.length = 0;
  fxNodes.length = 0;
  // The picker sits above everything, not inside the combined card: it drives
  // every card on the tab, and a single readable account (the other broker
  // down, or only one configured) still wants its own currency switched.
  if (FX) root.appendChild(currencyPicker());
  const total = buildTotalCard(DATA.accounts);
  if (total) root.appendChild(total);
  for (const a of DATA.accounts) root.appendChild(buildAccountCard(a));
  refreshFx();
}
