"""The fixed metric set (house rule C13).

One definition per metric, the same every week: a post may only headline a
metric listed here, and it is read from the same place in vela's summary every
time. Adding one is a deliberate change to this table, never a per-post choice.

Changed 2026-10-09 to follow vela paying interest on idle cash (2026-10-07): `sharpe`
is now measured over cash (vela's own definition), `excess_return` was added,
and `total_return` was **removed**. The account is mostly cash, so its total
return is mostly the cash rate; the workspace contract says it is never shown
alone, and a headline is exactly "alone".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MINUS = "−"


def _sign(v: float) -> str:
    return "+" if v > 0 else (MINUS if v < 0 else "")


def dollars(v: float) -> str:
    return f"{_sign(v)}${abs(v):,.0f}"


def percent(v: float) -> str:
    return f"{_sign(v)}{abs(v) * 100:.1f}%"


def ratio(v: float) -> str:
    return f"{_sign(v)}{abs(v):.2f}"


@dataclass(frozen=True)
class Metric:
    key: str
    path: tuple[str, ...]
    #: How the text names it: "the average trade was ...".
    label: str
    fmt: Callable[[float], str]


METRICS: dict[str, Metric] = {
    m.key: m
    for m in (
        Metric("expectancy", ("results", "trades", "expectancy"), "average trade", dollars),
        Metric("total_pnl", ("results", "trades", "total_pnl"), "total P&L", dollars),
        Metric("win_rate", ("results", "trades", "win_rate"), "win rate", percent),
        Metric("t_stat", ("results", "trades", "t_stat"), "t-statistic of the average trade", ratio),
        Metric("sharpe", ("results", "curve", "sharpe"), "Sharpe ratio over cash", ratio),
        Metric("max_drawdown", ("results", "curve", "max_drawdown"), "maximum drawdown", percent),
        Metric("excess_return", ("results", "curve", "excess_return"), "return over cash", percent),
    )
}


def read(summary: dict[str, Any], key: str) -> float | None:
    """The metric's value, or None when vela did not compute it. Never 0 for
    absent: a figure nobody computed and a figure of zero are different."""
    node: Any = summary
    for part in METRICS[key].path:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return float(node) if isinstance(node, (int, float)) else None
