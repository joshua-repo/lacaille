"""The dashboard page: one self-contained HTML file, built from a JSON payload.

Named for the view it started as -- a month calendar of option-spread
expiries -- and the name is kept because callers import it. The page is two
workspaces:

- **Analysis** -- Portfolio (a watchlist), Metrics, and a reserved Pipeline
  area. Only the watchlist carries data today; the rest is layout waiting on
  antlia's `live` layer.
- **Research** -- Data, Parameters and Results, layout waiting on vela's runs
  folder.

pictor reads no broker. The expiry views over the live option book (calendar,
Gantt, table) were removed on 2026-10-09, after antlia dropped its account
layer; nothing here reads positions any more.

No external assets (fonts/JS libs) -- the page is fully self-contained and
works offline.
"""

from __future__ import annotations

import datetime as dt
import json
import warnings
from pathlib import Path

from pictor.watchlist import Watchlist


def _display_path(path: Path) -> str:
    """`~/...` rather than the absolute path: the page is an artefact that gets
    archived and passed around, and a home directory is not its business."""
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(path)


def _watchlist_data(watchlist: Watchlist | None) -> dict | None:
    if watchlist is None:
        return None
    return {
        "path": _display_path(watchlist.path),
        "found": watchlist.found,
        "symbols": [
            {"ticker": s.ticker, "note": s.note, "tags": list(s.tags)} for s in watchlist.symbols
        ],
    }


def build_calendar_html(
    today: dt.date | None = None,
    *,
    watchlist: Watchlist | None = None,
) -> str:
    """Render the whole dashboard to one self-contained HTML string.

    `watchlist` is optional: with none passed, Portfolio says so.
    """
    today = today or dt.date.today()
    payload = json.dumps(
        {
            "today": today.isoformat(),
            "watchlist": _watchlist_data(watchlist),
        }
    ).replace("</", "<\\/")

    return _template().replace("__PICTOR_DATA__", payload)


#: The built front end: one self-contained HTML file with a `__PICTOR_DATA__`
#: placeholder where the payload goes. It is a build artefact of `web/` (see
#: `web/build.sh`) that is committed and shipped inside the package, so a
#: plain `pip install pictor` needs no Node and no build step.
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "_web" / "index.html"


#: Front-end sources, present in a checkout and absent from an installed wheel.
_SOURCE_DIR = _TEMPLATE_PATH.parents[3] / "web" / "src"


def _warn_if_stale(built_at: float) -> None:
    """Say so when the front-end sources are newer than the built page.

    The one failure mode this split introduces: edit `web/src`, forget to run
    `web/build.sh`, and the CLI cheerfully renders the previous build while
    reporting success. Silence there costs an hour of "my change did nothing",
    so it is worth a handful of `stat` calls. Skipped entirely for an installed
    wheel, which has no sources to compare against.
    """
    if not _SOURCE_DIR.is_dir():
        return
    newest = max(
        (p.stat().st_mtime for p in _SOURCE_DIR.rglob("*") if p.is_file()), default=0.0
    )
    if newest > built_at:
        warnings.warn(
            f"{_SOURCE_DIR} is newer than the built front end -- this page is from the "
            "previous build. Run web/build.sh.",
            stacklevel=3,
        )


def _template() -> str:
    """The built page shell.

    Read on every call rather than cached at import: during front-end work the
    file is rebuilt underneath a running process, and a cached copy would
    quietly serve the previous build.
    """
    try:
        text = _TEMPLATE_PATH.read_text()
    except FileNotFoundError:  # pragma: no cover -- a broken install or checkout
        raise RuntimeError(
            f"the built front end is missing at {_TEMPLATE_PATH}. It is committed, so this "
            "is either an incomplete checkout or an edit that deleted it; rebuild with "
            "web/build.sh (needs Docker, installs nothing on the host)."
        ) from None
    _warn_if_stale(_TEMPLATE_PATH.stat().st_mtime)
    return text
