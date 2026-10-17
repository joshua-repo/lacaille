"""`antlia` -- the one command. The first word picks an area; the rest is its own.

    antlia auth [sources] [--verify] [-p PROFILE] [--init]   # credentials and sessions
    antlia gateway [-s SOURCE] [-p PROFILE] [--restart]      # the gateway behind a source
    antlia fx [--verify] [--convert AMOUNT FROM TO]          # the rate table
    antlia history [plan|fill|coverage|...] ...              # the store
    antlia <area> -h                                         # that area's own flags

This file is a dispatcher and nothing else. Each area keeps its CLI beside the
code it drives (`auth/cli.py`, `gateway/cli.py`, `fx/cli.py`,
`history/cli.py`), and is handed the rest of the line unchanged -- no flag is
added or interpreted here, so an area's `-h` is the whole truth about it.

**The area is imported by name, only once chosen.** `antlia auth` must not
import the query engine and `antlia gateway` must not import a vendor SDK;
importing every area up front to build one big parser would cost both.

There is no `__main__.py` anywhere in antlia: `antlia` is the console script,
and `python -m antlia.cli` is the same thing for a checkout with no install.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Area:
    name: str
    module: str
    help: str


AREAS: tuple[Area, ...] = (
    Area("auth", "antlia.auth.cli", "what resolves, what connects, what verifies"),
    Area("gateway", "antlia.gateway.cli", "where a source's gateway is; restart it"),
    Area("fx", "antlia.fx.cli", "the FX rate table, and whether each source answers"),
    Area("history", "antlia.history.cli", "the store: doctor, plan, fill, coverage, check"),
)


def usage() -> str:
    width = max(len(a.name) for a in AREAS)
    lines = ["usage: antlia <area> [args...]", "", "areas:"]
    lines += [f"  {a.name:<{width}}  {a.help}" for a in AREAS]
    lines += ["", "antlia <area> -h lists that area's own flags."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print(usage())
        return 0
    chosen = {a.name: a for a in AREAS}.get(args[0])
    if chosen is None:
        print(f"antlia: unknown area {args[0]!r}\n\n{usage()}", file=sys.stderr)
        return 2
    run: int = importlib.import_module(chosen.module).main(args[1:])
    return run


if __name__ == "__main__":
    sys.exit(main())
