import { buildPlaceholder } from "../components/placeholder.js";

/* The Market view, beside Accounts inside Analysis.
 *
 * The split at this level is what you own versus what the market is doing.
 * Accounts is answered entirely by a broker snapshot; Market is not answered at
 * all yet -- it needs a market-data layer in antlia, which today does not exist
 * (auth, account and fx are the three layers there). pictor currently reaches
 * yfinance directly for earnings and news, which is exactly the thing that
 * should move behind that layer rather than grow here.
 */
export function buildMarket() {
  buildPlaceholder(document.getElementById("marketView"), {
    title: "Market",
    meta: "live, like Accounts · not yet wired",
    tag: "needs antlia.market",
    lede: "Accounts answers what you hold. Market answers what is happening to the things you "
        + "hold, or might: quotes, chains, surfaces, the calendar of events that moves them. It "
        + "is live data like Accounts, which is why it belongs in this workspace and not in Research.",
    items: [
      ["Quotes and chains", "Prices and option chains per underlying, through one rate-limited session rather than a scraper per caller."],
      ["Volatility surface", "Strike by expiry by IV, for the underlyings actually held or watched."],
      ["Events", "Earnings and headlines -- today pictor fetches these itself, bypassing antlia's session and pacing entirely."],
    ],
    note: "Blocked on a market layer in antlia; nothing here is faked in the meantime.",
  });
}
