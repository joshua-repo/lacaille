"""Reading vela's run folders -- the only interface between vela and pictor.

A run is a directory holding `summary.json`, `trades.csv` and `equity.csv`.
pictor reads them and never imports vela.

Licensing (house rule C15): `equity.csv` carries the underlying's close in
`spot`, and `trades.csv` carries option quotes in `legs`. Both are vendor data.
`equity` reads through a column allowlist, so neither can reach a chart or a
sentence by accident, and `trades.csv` is not read at all.

Cash carry: since 2026-10-07 vela pays interest on idle cash, and the account
is mostly cash -- a strategy that lost money trading can show a positive total
return. `trading_pnl` is therefore equity *less* the cumulative interest, which
is the series a chart about a strategy has to show.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Summary shapes this reader understands. vela has not versioned its summary
#: yet (absent = 0); an unknown version is refused rather than guessed at.
KNOWN_SCHEMAS = (0,)
EQUITY_COLUMNS = ("date", "equity")
#: Cumulative interest on cash, per session. Absent before vela had a cash rate.
INTEREST = "interest"


class RunError(ValueError):
    """A run folder pictor cannot read safely."""


@dataclass(frozen=True)
class Run:
    path: Path
    summary: dict[str, Any]
    run_at: dt.datetime

    @property
    def args(self) -> dict[str, Any]:
        return self.summary["invocation"]["args"]

    @property
    def name(self) -> str:
        return self.path.name


def default_root() -> Path:
    return Path(os.environ.get("VELA_RUNS") or "~/.vela/runs").expanduser()


def _load(summary_path: Path) -> Run | None:
    summary = json.loads(summary_path.read_text())
    schema = summary.get("schema", 0)
    if schema not in KNOWN_SCHEMAS:
        raise RunError(f"{summary_path.parent}: summary schema {schema} is not one pictor reads")
    if "invocation" not in summary:
        # Written before vela recorded its arguments: there is no way to tell
        # what it was asked for, so it cannot be matched to a question.
        return None
    return Run(
        path=summary_path.parent,
        summary=summary,
        run_at=dt.datetime.fromisoformat(summary["run_at"]),
    )


def discover(root: Path) -> tuple[list[Run], int]:
    """Every readable run under `root`, oldest first, and how many were skipped
    for predating recorded invocations."""
    runs, skipped = [], 0
    for path in sorted(Path(root).expanduser().rglob("summary.json")):
        run = _load(path)
        if run is None:
            skipped += 1
        else:
            runs.append(run)
    runs.sort(key=lambda r: r.run_at)
    return runs, skipped


def trading_pnl(run: Run) -> list[tuple[dt.date, float]]:
    """Cumulative trading P&L by date: equity, minus cash interest, minus the
    starting cash. Nothing else from that file."""
    initial = float(run.summary["engine"]["initial_cash"])
    with open(run.path / "equity.csv", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = set(reader.fieldnames or ())
        if not set(EQUITY_COLUMNS) <= columns:
            raise RunError(f"{run.path}/equity.csv lacks {EQUITY_COLUMNS}")
        has_interest = INTEREST in columns
        if not has_interest and run.summary["engine"].get("cash_rate"):
            # A cash rate with no interest column would put the carry back
            # into the line silently. Refuse rather than guess.
            raise RunError(f"{run.path}: a cash rate is set but equity.csv has no interest column")
        return [
            (
                dt.date.fromisoformat(r["date"]),
                float(r["equity"]) - (float(r[INTEREST]) if has_interest else 0.0) - initial,
            )
            for r in reader
        ]
