"""The registered rule, applied: which of the three titles the post carries.

Nothing here is discretionary. The verdict comes from the metric, the operator
and the trade floor that were committed before the runs; the title is the one
written for that verdict at the same time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pictor.publish.metrics import METRICS, Metric, read
from pictor.publish.question import Question


@dataclass(frozen=True)
class Outcome:
    verdict: str           # "true" | "false" | "inconclusive"
    title: str
    reason: str
    metric: Metric
    treatment: float | None
    baseline: float | None
    treatment_trades: int
    baseline_trades: int


def _trades(summary: dict[str, Any]) -> int:
    return int(((summary.get("results") or {}).get("trades") or {}).get("n") or 0)


def evaluate(question: Question, treatment: dict[str, Any], baseline: dict[str, Any]) -> Outcome:
    claim = question.claim
    metric = METRICS[claim.metric]
    tv, bv = read(treatment, claim.metric), read(baseline, claim.metric)
    tn, bn = _trades(treatment), _trades(baseline)

    # A5: below the floor, on either side, the rule is not applied at all.
    if min(tn, bn) < claim.min_trades:
        verdict = "inconclusive"
        reason = f"{min(tn, bn)} trades on one side, below the registered floor of {claim.min_trades}"
    elif tv is None or bv is None:
        verdict = "inconclusive"
        reason = f"vela did not compute the {metric.label} for both runs"
    else:
        holds = tv > bv if claim.op == ">" else tv < bv
        verdict = "true" if holds else "false"
        reason = f"{metric.label}: {metric.fmt(tv)} {claim.op} {metric.fmt(bv)} is {holds}"

    return Outcome(
        verdict=verdict,
        title=claim.titles[verdict],
        reason=reason,
        metric=metric,
        treatment=tv,
        baseline=bv,
        treatment_trades=tn,
        baseline_trades=bn,
    )
