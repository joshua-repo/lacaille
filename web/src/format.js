export function toLocalIso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return y + "-" + m + "-" + day;
}

export const fmtMoney = n => (n < 0 ? "-$" : "+$") + Math.abs(n).toLocaleString(undefined, {maximumFractionDigits: 0});

export const fmtDate = iso => {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, {month: "short", day: "numeric"});
};

export const money0 = ccy => v => v.toLocaleString(undefined, {style: "currency", currency: ccy, maximumFractionDigits: 0});

export const int0 = v => Math.round(v).toLocaleString();

export const pct1 = v => (v * 100).toFixed(1) + "%";


/* ---- Accounts view ---------------------------------------------------
   One card per broker account, plus a combined card on top. Deliberately not
   filtered by the underlying pills above -- those select spreads, and an
   account balance is not a property of a ticker.

   Every money figure is stated in the display currency the picker selects,
   converted from the currency it was reported in through the rate table in
   the payload (antlia.fx builds it; pictor/fx.py only decides what happens
   when there is none). Conversion happens here rather than in
   Python so switching currency is instant and works offline -- and so each
   change re-`set`s the tickers, which is what makes every digit on the page
   roll to its new value at once. */

export const DASH = "—";

export function fmtCcy(value, currency) {
  return value.toLocaleString(undefined, {style: "currency", currency: currency, maximumFractionDigits: 0});
}
