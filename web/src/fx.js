import { FX } from "./data.js";


/* Restate an amount, crossing through the rate table's pivot currency.
   Mirrors antlia.fx.types.RateTable.convert -- null whenever it cannot be
   done exactly, never a guess. */
export function convert(amount, frm, to) {
  if (amount === null || amount === undefined) return null;
  if (frm === to) return amount;
  if (!FX) return null;
  const from = FX.rates[frm], into = FX.rates[to];
  if (!from || into === undefined) return null;
  return amount / from * into;
}


/* Nodes that have to be recomputed when the display currency changes. */
export const fxNodes = [];

export function refreshFx() { for (const update of fxNodes) update(); }
