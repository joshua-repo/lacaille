"""Every attempt to record, so a self-recorded dataset shows its holes.

Read through `history.recordings()`. The module is `attempts`, not
`recordings`, so that importing it cannot rebind that function's name on the
package -- the trap `registry.chain()` documents for `sources`.

`history.record()` writes no ledger entry: a snapshot is a sample of one
moment, and there is no complete set of moments for `coverage()` to measure
against. But a dataset you recorded yourself is only worth something if you
can see where it is missing -- the 15:30 recording that failed, the ticks
skipped while a slow one ran. Nothing in `raw/` can say that, because a
recording that did not happen leaves no file.

So each attempt is a row here. Four statuses:

- `ok` -- rows were kept.
- `empty` -- the gateway answered, with nothing (a closed market, a slice
  that matches no contract).
- `failed` -- an error; `detail` says which.
- `skipped` -- a scheduled time that passed while another recording ran. The
  recorder never queues, so this is how its gaps are named.

Laid out and written like the ledger (one Parquet file per write, staged and
renamed), in `<store>/recordings/`. It is **not** the ledger and is never read
by `coverage()`.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json
import os
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from antlia.history.engine import pa, pq
from antlia.history.store import connect, recordings_dir

OK = "ok"
EMPTY = "empty"
FAILED = "failed"
SKIPPED = "skipped"

SCHEMA = pa.schema(
    [
        ("scheduled_at", pa.timestamp("us", tz="UTC")),
        ("started_at", pa.timestamp("us", tz="UTC")),
        ("finished_at", pa.timestamp("us", tz="UTC")),
        ("source", pa.string()),
        ("table", pa.string()),
        ("symbol", pa.string()),
        ("slice", pa.string()),
        ("rows", pa.int64()),
        ("status", pa.string()),
        ("detail", pa.string()),
    ]
)

_lock = threading.Lock()
_serial = itertools.count()


@dataclass(frozen=True, slots=True)
class Attempt:
    """One try at a recording, or one scheduled time that was skipped."""

    scheduled_at: dt.datetime
    source: str
    table: str
    symbol: str
    status: str
    rows: int = 0
    started_at: dt.datetime | None = None
    finished_at: dt.datetime | None = None
    #: The options the snapshot was asked with: what makes two recordings of
    #: one symbol comparable or not.
    slice: Mapping[str, Any] = field(default_factory=dict)
    detail: str = ""

    def __str__(self) -> str:
        took = ""
        if self.started_at and self.finished_at:
            took = f" in {(self.finished_at - self.started_at).total_seconds():.1f}s"
        note = f"  {self.detail}" if self.detail else ""
        return (
            f"{self.scheduled_at:%Y-%m-%d %H:%M}Z {self.status:7} {self.rows:>5} rows{took}{note}"
        )


def write(base: Path, attempts: Sequence[Attempt]) -> int:
    """Append attempts. One file per call, so a write is never half-done."""
    if not attempts:
        return 0
    frame = pa.Table.from_pydict(
        {
            "scheduled_at": [a.scheduled_at for a in attempts],
            "started_at": [a.started_at for a in attempts],
            "finished_at": [a.finished_at for a in attempts],
            "source": [a.source for a in attempts],
            "table": [a.table for a in attempts],
            "symbol": [a.symbol for a in attempts],
            "slice": [json.dumps(dict(a.slice), sort_keys=True, default=str) for a in attempts],
            "rows": [a.rows for a in attempts],
            "status": [a.status for a in attempts],
            "detail": [a.detail for a in attempts],
        },
        schema=SCHEMA,
    )
    directory = recordings_dir(base)
    stamp = dt.datetime.now(dt.UTC)
    with _lock:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{stamp:%Y%m%dT%H%M%S%f}-{os.getpid()}-{next(_serial)}.parquet"
        # Staged then renamed, as the ledger is: a killed process must not
        # leave a truncated file that makes the whole log unreadable.
        temp = target.with_suffix(".tmp")
        pq.write_table(frame, temp)
        os.replace(temp, target)
    return len(attempts)


def read(base: Path, symbol: str | None = None, table: str | None = None) -> Any:
    """Every attempt, oldest first, as a pyarrow.Table (empty if none yet)."""
    directory = recordings_dir(base)
    if not directory.exists() or not any(directory.glob("*.parquet")):
        return SCHEMA.empty_table()
    where, params = [], []
    if symbol is not None:
        where.append("symbol = ?")
        params.append(symbol)
    if table is not None:
        where.append('"table" = ?')
        params.append(table)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    con = connect()
    try:
        result = con.execute(
            f"SELECT * FROM read_parquet(?) {clause} ORDER BY scheduled_at, started_at",
            [str(directory / "*.parquet"), *params],
        )
        getter = getattr(result, "to_arrow_table", None) or result.fetch_arrow_table
        return getter().cast(SCHEMA)
    finally:
        con.close()
