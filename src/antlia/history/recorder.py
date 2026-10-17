"""The recorder: live option chains kept on a schedule, every attempt logged.

A data job, so antlia's, and independent of puppis (which records the one
snapshot it decides on). `antlia history record` is its command.

**One process, one session, a wall-clock grid.** The loop stays up and holds
one gateway session -- the auth pool keeps it between recordings and replaces
it after the gateway's nightly restart -- and records at fixed New York times:
every `every` from 09:30 to 16:00 inclusive, so 16:00 is always a recording
(the one that compares with a vendor's end-of-day row). Weekdays only; there
is no holiday calendar, and a holiday records empty quotes, which says so.

**Never queued.** A recording that overruns its slot does not make the next
one late: the grid times it ran through are logged `skipped` and the loop
waits for the next one ahead. How long a chain takes is the user's to find
out from the log, not this module's to hide.

**Its own client id** (`CLIENT_ID`, 950). Automatic ids restart at 900 in
every process, so a recorder holding 900 all day would collide with the next
script run by hand.

`antlia.live` is imported inside `record_once`, not at the top: importing
`antlia.history` must never pull in a live source.
"""

from __future__ import annotations

import datetime as dt
import re
import time
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from antlia.history import attempts
from antlia.history.attempts import EMPTY, FAILED, OK, SKIPPED, Attempt

NY = ZoneInfo("America/New_York")
OPEN = dt.time(9, 30)
CLOSE = dt.time(16, 0)

#: The recorder's gateway client id. 900+ is antlia's automatic range, 100 is
#: puppis.
CLIENT_ID = 950

SOURCE = "ibkr"
TABLE = "option_quote"

Clock = Callable[[], dt.datetime]

UNITS = {"s": "seconds", "m": "minutes", "h": "hours"}


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def parse_every(text: str) -> dt.timedelta:
    """`15m`, `1m`, `30s`, `1h` -> a timedelta. At least 10 seconds."""
    found = re.fullmatch(r"\s*(\d+)\s*([smh])\s*", text)
    if not found:
        raise ValueError(f"cannot read {text!r} as an interval; write 15m, 1m, 30s or 1h")
    amount, unit = int(found[1]), found[2]
    every = dt.timedelta(**{UNITS[unit]: amount})
    if every < dt.timedelta(seconds=10):
        raise ValueError(f"{text!r} is shorter than one snapshot can take; use 10s or more")
    return every


def grid(day: dt.date, every: dt.timedelta) -> list[dt.datetime]:
    """The day's recording times in UTC: 09:30 New York, every `every`, and 16:00."""
    if day.weekday() >= 5:
        return []
    opening = dt.datetime.combine(day, OPEN, tzinfo=NY)
    closing = dt.datetime.combine(day, CLOSE, tzinfo=NY)
    times = []
    tick = opening
    while tick < closing:
        times.append(tick)
        tick += every
    times.append(closing)
    return [t.astimezone(dt.UTC) for t in times]


def ticks(after: dt.datetime, every: dt.timedelta) -> Iterator[dt.datetime]:
    """Every grid time at or after `after`, in order, for as long as asked."""
    day = after.astimezone(NY).date()
    while True:
        for tick in grid(day, every):
            if tick >= after:
                yield tick
        day += dt.timedelta(days=1)


def next_tick(at: dt.datetime, every: dt.timedelta) -> dt.datetime:
    return next(ticks(at, every))


def missed(done: dt.datetime, at: dt.datetime, every: dt.timedelta) -> list[dt.datetime]:
    """Grid times after `done` that had passed by `at`: skipped, never caught up."""
    passed = []
    for tick in ticks(done + dt.timedelta(microseconds=1), every):
        if tick > at:
            break
        passed.append(tick)
    return passed


def record_once(
    symbol: str,
    options: Mapping[str, Any],
    scheduled_at: dt.datetime,
    base: Path,
    *,
    client_id: int = CLIENT_ID,
    clock: Clock = now,
) -> Attempt:
    """One snapshot, kept. Any error becomes a `failed` attempt, not a crash."""
    from antlia import live
    from antlia.history.writes import record

    started = clock()
    rows, status, detail = 0, FAILED, ""
    try:
        snap = live.option_chain(symbol, client_id=client_id, **options)
        rows = record(snap, store=base)
        status = OK if rows else EMPTY
    except Exception as exc:  # the loop must outlive any one recording
        detail = f"{type(exc).__name__}: {exc}"
    return Attempt(
        scheduled_at=scheduled_at,
        source=SOURCE,
        table=TABLE,
        symbol=symbol,
        status=status,
        rows=rows,
        started_at=started,
        finished_at=clock(),
        slice=dict(options),
        detail=detail,
    )


def run(
    symbol: str,
    options: Mapping[str, Any],
    every: dt.timedelta,
    base: Path,
    *,
    client_id: int = CLIENT_ID,
    clock: Clock = now,
    sleep: Callable[[float], None] = time.sleep,
    report: Callable[[Attempt], None] = print,
    until: dt.datetime | None = None,
) -> None:
    """Record on the grid until interrupted (or, for tests, until `until`)."""
    while True:
        tick = next_tick(clock(), every)
        if until is not None and tick > until:
            return
        wait = (tick - clock()).total_seconds()
        if wait > 0:
            sleep(wait)
        attempt = record_once(symbol, options, tick, base, client_id=client_id, clock=clock)
        skipped = [
            Attempt(
                scheduled_at=t,
                source=SOURCE,
                table=TABLE,
                symbol=symbol,
                status=SKIPPED,
                slice=dict(options),
                detail=f"busy with {tick:%H:%M}Z",
            )
            for t in missed(tick, clock(), every)
        ]
        attempts.write(base, [attempt, *skipped])
        for logged in (attempt, *skipped):
            report(logged)
