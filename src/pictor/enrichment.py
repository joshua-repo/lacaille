"""Best-effort earnings / recent-news enrichment for a ticker.

Uses yfinance, which is free but occasionally incomplete or stale. Swap
`get_earnings_date` / `has_recent_news` for a paid source (Finnhub, Alpha
Vantage, IBKR's own news feed via ib_insync's reqNewsArticle, etc.) if you
need something sturdier -- callers only care about the return shape.
"""

from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

NEWS_LOOKBACK_DAYS = 3


def get_earnings_date(ticker: str) -> dt.date | None:
    try:
        import yfinance as yf

        cal = yf.Ticker(ticker).get_earnings_dates(limit=4)
        if cal is None or cal.empty:
            return None
        future = [idx.date() for idx in cal.index if idx.date() >= dt.date.today()]
        return min(future) if future else None
    except Exception:
        return None


def has_recent_news(ticker: str, days: int = NEWS_LOOKBACK_DAYS) -> bool:
    try:
        import yfinance as yf

        items = yf.Ticker(ticker).news or []
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        for item in items:
            ts = item.get("providerPublishTime")
            if ts and dt.datetime.fromtimestamp(ts, dt.timezone.utc) >= cutoff:
                return True
        return False
    except Exception:
        return False


@dataclass
class TickerEnrichment:
    earnings_date: dt.date | None
    news: bool


def enrich_tickers(tickers: list[str], max_workers: int = 8) -> dict[str, TickerEnrichment]:
    """Look up earnings date + recent news for each ticker, once per unique
    ticker, in parallel. A chart with several spreads on the same underlying
    (or several underlyings) would otherwise make redundant, serial yfinance
    calls per spread -- this is the fix for both.
    """
    unique = sorted(set(tickers))
    if not unique:
        return {}

    def _fetch(ticker: str) -> tuple[str, TickerEnrichment]:
        return ticker, TickerEnrichment(get_earnings_date(ticker), has_recent_news(ticker))

    with ThreadPoolExecutor(max_workers=min(max_workers, len(unique))) as pool:
        return dict(pool.map(_fetch, unique))
