"""`puppis` -- the forward test's command. M0 has one subcommand.

    puppis check                    # connect, run the paper guard, show what is held
    puppis check --client-id 101    # a second process on the same gateway

`check` places nothing and writes nothing. It connects on puppis's own
writable socket, refuses any account that is not paper, and prints the
account, its positions and today's executions -- which is how M0 is shown to
work against the real gateway.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from puppis.broker import Broker, Execution, Instrument, Position
from puppis.guard import NotPaper
from puppis.ibkr import CLIENT_ID, IbkrBroker


def describe(i: Instrument) -> str:
    if i.sec_type == "OPT" and i.expiration is not None:
        return f"{i.symbol} {i.expiration:%Y-%m-%d} {i.strike:g}{i.right}"
    return f"{i.symbol} {i.sec_type}"


def show_position(p: Position) -> str:
    return f"  {describe(p.instrument):<28} {p.quantity:>8g}  avg cost {p.avg_cost:,.2f}"


def show_execution(e: Execution) -> str:
    fee = "?" if e.commission is None else f"{e.commission:.2f}"
    return (
        f"  {e.time:%H:%M:%S}Z {e.side} {e.quantity:g} {describe(e.instrument):<28} "
        f"@ {e.price:,.4f}  fee {fee}  ref {e.order_ref or '-'}"
    )


def check(broker: Broker) -> int:
    try:
        broker.connect()
    except NotPaper as exc:
        print(f"REFUSED  {exc}", file=sys.stderr)
        return 3
    try:
        print(f"accounts   {', '.join(broker.accounts())}   (paper)")
        positions = broker.positions()
        print(f"positions  {len(positions)}")
        for p in positions:
            print(show_position(p))
        fills = broker.executions()
        print(f"executions {len(fills)} today")
        for e in fills:
            print(show_execution(e))
    finally:
        broker.close()
    return 0


def main(argv: list[str] | None = None, make: Callable[..., Broker] = IbkrBroker) -> int:
    parser = argparse.ArgumentParser(prog="puppis", description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    sub = subs.add_parser("check", help="connect, run the paper guard, show what is held")
    sub.add_argument("-p", "--profile", default="paper", help="antlia's ibkr profile")
    sub.add_argument("--client-id", type=int, default=CLIENT_ID)
    args = parser.parse_args(argv)
    try:
        return check(make(args.profile, client_id=args.client_id))
    except Exception as exc:
        print(f"FAILED   {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
