from __future__ import annotations

import functools
import platform
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Annotated

import typer

from pictor.charts import build_calendar_html, build_chart
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
) -> None:
    """Render the bull-spread expiry calendar (month grid with per-day chips)."""
    spreads = pair_spreads(_fetch_legs(profile))
    html = build_calendar_html(spreads)
    output.write_text(html)
    typer.echo(f"Wrote {output} ({len(spreads)} spreads)")

    if open_browser:
        _serve_and_open(output)


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
