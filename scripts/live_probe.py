"""Take one live option-chain snapshot, then break holding it.

    python scripts/live_probe.py SPY --max-dte 30 --rights P
    python scripts/live_probe.py SPY --strikes 740,780 --profile paper

Meant for the launch configurations in `.vscode/launch.json`. It prints what
came back and breaks with the result bound so you can poke at it:

    >>> snap.table          # canonical OPTION_QUOTE columns
    >>> snap.raw            # what the gateway sent, IBKR's own field names
    >>> snap.table.to_pandas()

It never records: keeping a snapshot is `history.record(snap)`, by hand.

Breakpoints in `src/antlia/live/` hit on the way in; run with
`justMyCode: false` to step into ib_async as well.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from antlia import auth, live  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--profile", default="paper")
    parser.add_argument("--min-dte", type=int, default=None)
    parser.add_argument("--max-dte", type=int, default=30)
    parser.add_argument("--rights", default="CP", help="C, P or CP")
    parser.add_argument("--strikes", default=None, metavar="LO,HI", help="default: +/-15%%")
    parser.add_argument("--no-repl", dest="repl", action="store_false", help="skip the breakpoint")
    args = parser.parse_args(argv)

    strikes = None
    if args.strikes:
        lo, hi = (float(x) for x in args.strikes.split(","))
        strikes = (lo, hi)

    started = time.monotonic()
    snap = live.option_chain(
        args.symbol,
        profile=args.profile,
        min_dte=args.min_dte,
        max_dte=args.max_dte,
        strikes=strikes,
        rights=args.rights,
    )
    print(f"{snap}   ({time.monotonic() - started:.1f}s)")
    table = snap.table
    if table.num_rows:
        print(f"expirations {sorted(set(table.column('expiration').to_pylist()))}")
        for name in ("bid", "ask", "last", "iv", "delta"):
            values = table.column(name).to_pylist()
            print(f"{name:<11} non-null {sum(v is not None for v in values)}/{len(values)}")

    if args.repl:
        breakpoint()  # snap, table
    auth.close_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
