from __future__ import annotations

import functools
import platform
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Annotated

import typer

from pictor.accounts import fetch_overviews
from pictor.charts import build_calendar_html, build_chart
from pictor.fx import DEFAULT_CURRENCIES, fetch_rates
from pictor.pairing import pair_spreads

app = typer.Typer(help="Pictor: visualization layer for option spread positions.")


@app.callback()
def _main() -> None:
    pass


def _fetch_legs(profile: str):
    from pictor.sources import fetch_positions_live

    return fetch_positions_live(profile=profile)


ProfileOption = Annotated[str, typer.Option(help="antlia IBKR profile to connect with: 'live' (default) or 'paper'.")]


@app.command()
def gantt(
    profile: ProfileOption = "live",
    output: Annotated[Path, typer.Option("--output", "-o", help="Path to write the HTML chart to.")] = Path("bull_spread_gantt.html"),
    open_browser: Annotated[bool, typer.Option("--open", help="Open the chart in a browser after writing it.")] = False,
) -> None:
    """Render the bull-spread expiry Gantt chart."""
    spreads = pair_spreads(_fetch_legs(profile))
    fig = build_chart(spreads)
    fig.write_html(output, include_plotlyjs="cdn")
    typer.echo(f"Wrote {output} ({len(spreads)} spreads)")

    if open_browser:
        _serve_and_open(output)


@app.command()
def calendar(
    profile: ProfileOption = "live",
    output: Annotated[Path, typer.Option("--output", "-o", help="Path to write the HTML chart to.")] = Path("bull_spread_calendar.html"),
    open_browser: Annotated[bool, typer.Option("--open", help="Open the chart in a browser after writing it.")] = False,
    accounts: Annotated[bool, typer.Option("--accounts/--no-accounts", help="Include the per-account view (reads every configured broker).")] = True,
    t212_profile: Annotated[str, typer.Option(help="antlia Trading212 profile: 'live' (default) or 'demo'.")] = "live",
    fx: Annotated[bool, typer.Option("--fx/--no-fx", help="Fetch exchange rates so accounts can be shown in one currency and totalled.")] = True,
) -> None:
    """Render the bull-spread expiry calendar (month grid with per-day chips)."""
    if accounts:
        # One snapshot per account, feeding both the spread views and the
        # Accounts tab -- reading the option legs separately would open a
        # second connection to the same gateway for the same data.
        overviews = fetch_overviews((("ibkr", profile), ("trading212", t212_profile)))
        legs = [leg for o in overviews if o.ok for leg in o.option_legs]
        for o in overviews:
            if not o.ok:
                # Not fatal: the other broker's card, and the whole spread
                # view, are still worth rendering. The page says so too.
                typer.echo(f"warning: {o.source} ({o.profile}) unreadable -- {o.error}", err=True)
    else:
        overviews, legs = [], _fetch_legs(profile)

    # Fetched whenever there is an account to show. Not gated on holding two
    # currencies: a single GBP account is still worth viewing in USD, and one
    # USD account can hold JPY lines. antlia caches the table for 6h, so the
    # round-trip is paid about twice a day however often this runs.
    rates = None
    if fx and any(o.ok for o in overviews):
        held = {o.currency for o in overviews if o.ok and o.currency}
        held |= {h.currency for o in overviews if o.ok for h in o.holdings if h.currency}
        rates = fetch_rates(tuple(dict.fromkeys((*DEFAULT_CURRENCIES, *sorted(held)))))
        if rates is None:
            typer.echo("warning: no exchange rates available -- accounts stay in their own currencies", err=True)
        elif rates.stale:
            typer.echo(f"warning: using stale {rates.source} rates from {rates.as_of:%Y-%m-%d %H:%M}", err=True)

    spreads = pair_spreads(legs)
    html = build_calendar_html(spreads, accounts=overviews, rates=rates)
    output.write_text(html)
    reached = sum(1 for o in overviews if o.ok)
    suffix = f", {reached} of {len(overviews)} accounts" if overviews else ""
    if rates:
        suffix += f", fx via {rates.source}"
    typer.echo(f"Wrote {output} ({len(spreads)} spreads{suffix})")

    if open_browser:
        _serve_and_open(output)


@app.command()
def positions(
    source: Annotated[str, typer.Option(help="Broker to read: 'ibkr', 'trading212', or 'all'.")] = "all",
    profile: Annotated[str, typer.Option(help="antlia profile: ibkr 'live'/'paper', trading212 'live'/'demo'.")] = "live",
) -> None:
    """Print what each broker currently holds -- options from IBKR, shares from both.

    A read-only reachability check as much as a report: it is the quickest way
    to tell a credential/gateway problem apart from a charting one, since the
    charts only ever show IBKR's option book.
    """
    from pictor.sources import fetch_equity_positions, fetch_option_legs

    names = ["ibkr", "trading212"] if source == "all" else [source]
    for name in names:
        typer.echo(f"\n{name} ({profile})")
        try:
            legs = fetch_option_legs(name, profile) if name == "ibkr" else []
            shares = fetch_equity_positions(name, profile)
        except Exception as exc:  # antlia raises per-vendor auth/connection errors
            typer.echo(f"  unavailable -- {type(exc).__name__}: {exc}")
            continue
        for leg in legs:
            typer.echo(
                f"  option  {leg.underlying:<6} {leg.expiry} {leg.strike:>8g}{leg.right}"
                f"  {leg.position:>+5g}  pnl {leg.unrealized_pnl:>10,.2f}"
            )
        for pos in shares:
            value = f"{pos.market_value:>12,.2f}" if pos.market_value is not None else f"{'--':>12}"
            typer.echo(
                f"  share   {pos.symbol:<6} {pos.quantity:>10g} @ {pos.price or 0:>10,.2f}"
                f"  {value} {pos.currency}"
            )
        if not legs and not shares:
            typer.echo("  (no positions)")


def _is_wsl() -> bool:
    return "microsoft" in platform.uname().release.lower()


def _open_url(url: str) -> None:
    if _is_wsl():
        # webbrowser/gio have no browser registered inside WSL itself; hop
        # out to the Windows side, which owns the actual default browser.
        # WSL2 forwards 127.0.0.1 to the host, so the URL is reachable.
        subprocess.Popen(["explorer.exe", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def _serve_and_open(output: Path) -> None:
    """Serve `output` over localhost and open it in a browser.

    Always uses an http://127.0.0.1 URL rather than file:// -- under plain
    local use that opens directly; under WSL the local filesystem path isn't
    what Windows' browser expects either, and 127.0.0.1 is forwarded to the
    host; under Remote-SSH the local browser can't reach the remote
    filesystem at all, so file:// fails there too
    (`gio: ... Failed to find default application`). Serves exactly one
    request then exits; not a persistent daemon.
    """
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(output.parent))
    server = HTTPServer(("127.0.0.1", 0), handler)
    server.timeout = 20  # give port forwarding (Remote-SSH / WSL) a moment to kick in
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/{output.name}"

    typer.echo(f"Serving at {url}")
    typer.echo("(if nothing opens within ~20s, open that URL manually.)")
    _open_url(url)
    server.handle_request()
    server.server_close()


if __name__ == "__main__":
    app()
