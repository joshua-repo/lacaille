from __future__ import annotations

import functools
import platform
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Annotated

import typer

from pictor.charts import build_calendar_html
from pictor.watchlist import load_watchlist

app = typer.Typer(help="Pictor: the rendering layer -- a market/research dashboard and weekly posts.")


@app.callback()
def _main() -> None:
    pass


@app.command()
def calendar(
    output: Annotated[Path, typer.Option("--output", "-o", help="Path to write the HTML page to.")] = Path("bull_spread_calendar.html"),
    open_browser: Annotated[bool, typer.Option("--open", help="Open the page in a browser after writing it.")] = False,
    watchlist: Annotated[Path | None, typer.Option("--watchlist", help="Watchlist TOML for Analysis > Portfolio (default: $PICTOR_WATCHLIST, else ~/.pictor/watchlist.toml).")] = None,
) -> None:
    """Render the dashboard: the Analysis and Research workspaces in one page."""
    try:
        watch = load_watchlist(watchlist)
    except ValueError as exc:
        # A watchlist with a typo in it is fatal, unlike a missing one: an
        # empty Portfolio would look exactly like having no list at all.
        typer.echo(f"error: watchlist unreadable -- {exc}", err=True)
        raise typer.Exit(1) from None
    if not watch.found:
        typer.echo(f"note: no watchlist at {watch.path} -- Portfolio will be empty", err=True)

    output.write_text(build_calendar_html(watchlist=watch))
    typer.echo(f"Wrote {output} ({len(watch.symbols)} watched)")

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
