"""Fixtures: a posts repo with a committed question, and vela-shaped runs.

Commit times and `run_at` are set explicitly, so every test states the order of
events it is about instead of depending on how fast it ran.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import pytest

QID = "2026-w01-test"
QUESTION = f'''
id = "{QID}"
question = "Does the gate help?"

[run]
symbol = "XYZ"
start = "2025-01-02"
end = "2025-12-31"

[treatment]
iv_rank = 0.5
label = "only when IV rank is high"

[baseline]
iv_rank = "none"
label = "every week"

[claim]
metric = "expectancy"
op = ">"
min_trades = 10
title_if_true = "The gate helped"
title_if_false = "The gate did not help"
title_if_inconclusive = "Too few trades to tell"
'''

#: vela's parsed arguments with its defaults, as `invocation.args` records them.
ARGS = {
    "symbol": "XYZ", "start": "2025-01-02", "end": "2025-12-31", "as_of": None, "max_dte": 45,
    "right": "P", "moneyness": 0.95, "width": 5.0, "entry_dte": [30, 45], "take_profit": 0.5,
    "stop_loss": 0.5, "exit_dte": 7, "max_concurrent": 3, "spacing": 7, "cash": 100000.0,
    "risk": 1000.0, "iv_rank": None, "iv_lookback": 120, "iv_warmup": 20, "haircut": 0.5,
    "commission": 0.65, "blackout": None, "rate": 0.04, "dividend_yield": 0.0, "out": "runs",
    "label": None, "envelope": False, "breakeven": False, "fetch": False,
}

T0 = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC)


def git(repo: Path, *args: str, when: dt.datetime | None = None) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    if when:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = when.isoformat()
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


@pytest.fixture
def posts(tmp_path):
    repo = tmp_path / "posts"
    (repo / QID).mkdir(parents=True)
    git(repo, "init", "-q")
    return repo


def register(repo: Path, text: str = QUESTION, when: dt.datetime = T0) -> Path:
    path = repo / QID / "question.toml"
    path.write_text(text)
    git(repo, "add", str(path))
    git(repo, "commit", "-q", "-m", "register", when=when)
    return path


def make_run(root: Path, name: str, *, run_at: dt.datetime, n: int = 20, expectancy: float = 10.0,
             dirty: bool = False, sha: str = "abc123", schema: int | None = None,
             interest: bool = True, **args) -> Path:
    out = root / "xyz" / name
    out.mkdir(parents=True)
    summary = {
        "run_at": run_at.isoformat(),
        "git": {"sha": sha, "dirty": dirty},
        "data": {"source": "antlia", "symbol": "XYZ", "start": "2025-01-02", "end": "2025-12-31",
                 "sessions": 3, "underlying_move": 0.12},
        "engine": {"initial_cash": 100000.0, "cash_rate": 0.04 if interest else None, "fill": {"type": "FillModel", "haircut": 0.5,
                                                      "commission": 0.65}},
        "strategy": {"name": "s", "params": {}},
        "results": {"trades": {"n": n, "expectancy": expectancy, "total_pnl": n * expectancy},
                    "curve": {"sharpe": 0.5}},
        "invocation": {"argv": [], "args": {**ARGS, **args}},
    }
    if schema is not None:
        summary["schema"] = schema
    (out / "summary.json").write_text(json.dumps(summary))
    # Cumulative interest; equity includes it, as vela writes it.
    rows = [("2025-01-02", 100.0, 100000, 0.0), ("2025-06-30", 105.0, 100500, 2000.0),
            ("2025-12-31", 112.0, 101000, 4000.0)]
    head = "date,spot,cash,market_value,equity" + (",interest" if interest else "")
    lines = [f"{d},{spot},100000,0,{eq + (i if interest else 0)}" + (f",{i}" if interest else "")
             for d, spot, eq, i in rows]
    (out / "equity.csv").write_text("\n".join([head, *lines]) + "\n")
    return out
