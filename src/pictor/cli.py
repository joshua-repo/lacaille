from __future__ import annotations

import functools
import os
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Annotated

import typer

from pictor.charts import build_chart
from pictor.pairing import pair_spreads

app = typer.Typer(help="Pictor: visualization layer for option spread positions.")


@app.callback()
def _main() -> None:
    pass


@app.command()
def gantt(
    live: Annotated[bool, typer.Option(help="Pull open positions from IBKR via ib_insync instead of the demo snapshot.")] = False,
    output: Annotated[Path, typer.Option("--output", "-o", help="Path to write the HTML chart to.")] = Path("bull_spread_gantt.html"),
    open_browser: Annotated[bool, typer.Option("--open", help="Open the chart in a browser after writing it.")] = False,
) -> None:
    """Render the bull-spread expiry Gantt chart."""
    if live:
        from pictor.sources import fetch_positions_live

        legs = fetch_positions_live()
    else:
        from pictor.sources import fetch_positions_demo

        legs = fetch_positions_demo()

    spreads = pair_spreads(legs)
    fig = build_chart(spreads)
    fig.write_html(output, include_plotlyjs="cdn")
    typer.echo(f"Wrote {output} ({len(spreads)} spreads)")

    if open_browser:
        _serve_and_open(output)


def _serve_and_open(output: Path) -> None:
    """Serve `output` over localhost and open it in a browser.

    Over a plain local session this just opens a file:// URL. Over
    Remote-SSH the local browser can't reach the remote filesystem, so we
    serve the file over HTTP instead -- VS Code auto-forwards a listening
    localhost port and, via the $BROWSER env var it injects into Remote-SSH
    terminals, hands the URL to your local browser. Serves exactly one
    request then exits; not a persistent daemon.
    """
    if "SSH_CONNECTION" not in os.environ and "SSH_CLIENT" not in os.environ:
        webbrowser.open(output.resolve().as_uri())
        return

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(output.parent))
    server = HTTPServer(("127.0.0.1", 0), handler)
    server.timeout = 20  # give VS Code's port forwarding a moment to kick in
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/{output.name}"

    typer.echo(f"Serving at {url}")
    typer.echo("(Remote-SSH: VS Code should auto-forward this port and open your local browser; "
               "if nothing opens within ~20s, check the Ports panel.)")
    webbrowser.open(url)
    server.handle_request()
    server.server_close()


if __name__ == "__main__":
    app()
