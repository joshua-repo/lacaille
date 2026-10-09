"""The watchlist behind Analysis > Portfolio.

A hand-kept file, deliberately not derived from a broker: what you are watching
and what you hold are different lists, and the page stopped being about the
second one. The default location is outside every repository, because the
symbols in it are research identity and committed code carries none
(`watchlist.example.toml` shows the shape with a placeholder).

    [[symbol]]
    ticker = "XXXX"
    note = "optional, free text"
    tags = ["optional"]

A missing file is not an error. The page says where it looked and what to put
there, which is more use on a first run than a traceback. A file that exists
and cannot be parsed *is* an error and raises `ValueError`: silently showing an empty list
for a watchlist with a typo in it would look exactly like having none.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

#: Overrides the default location; `--watchlist` on the CLI wins over both.
ENV_PATH = "PICTOR_WATCHLIST"
DEFAULT_PATH = Path("~/.pictor/watchlist.toml")


@dataclass
class WatchSymbol:
    ticker: str
    note: str = ""
    tags: tuple[str, ...] = ()


@dataclass
class Watchlist:
    path: Path
    #: False when there was no file at `path` -- distinct from a file that
    #: lists nothing, and the page words the two differently.
    found: bool
    symbols: list[WatchSymbol] = field(default_factory=list)


def default_path() -> Path:
    return Path(os.environ.get(ENV_PATH) or DEFAULT_PATH).expanduser()


def load_watchlist(path: Path | None = None) -> Watchlist:
    path = (path or default_path()).expanduser()
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return Watchlist(path=path, found=False)

    try:
        rows = tomllib.loads(raw.decode()).get("symbol", [])
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"{path}: {exc}") from None
    symbols: dict[str, WatchSymbol] = {}
    for row in rows:
        if "ticker" not in row:
            raise ValueError(f"{path}: a [[symbol]] table has no `ticker`")
        ticker = str(row["ticker"]).strip().upper()
        # First mention wins; a ticker listed twice is one row, not two.
        symbols.setdefault(
            ticker,
            WatchSymbol(ticker, str(row.get("note", "")), tuple(str(t) for t in row.get("tags", ()))),
        )
    return Watchlist(path=path, found=True, symbols=list(symbols.values()))
