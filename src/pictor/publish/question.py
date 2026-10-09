"""The registered question: one file, written and committed before any run.

Everything that decides what a post will say is in here and nowhere else --
the question, the two arms, the metric, the rule and all three possible
titles. Pre-registration only means something if the file holds the whole
decision; a title chosen afterwards would be a decision made after seeing the
result.

    id = "2026-w41-iv-gate"
    question = "Does ... ?"
    context = "optional, one or two sentences"
    kicker = "optional, the small caps line above the title"

    [run]          # vela arguments both arms share, by vela's own names
    symbol = "XXXX"
    start = "YYYY-MM-DD"
    end = "YYYY-MM-DD"

    [treatment]    # the arguments that differ, and nothing else
    iv_rank = 0.5
    label = "only when IV rank >= 0.5"

    [baseline]     # the same keys, the baseline's values
    iv_rank = "none"
    label = "every week"

    [claim]
    metric = "expectancy"
    op = ">"
    min_trades = 15
    title_if_true = "..."
    title_if_false = "..."
    title_if_inconclusive = "..."

TOML has no null, so `"none"` stands for vela's "not given" (`None` in its
recorded arguments).
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pictor.publish.metrics import METRICS

OPS = (">", "<")
VERDICTS = ("true", "false", "inconclusive")


class QuestionError(ValueError):
    """The file is not a valid registered question."""


@dataclass(frozen=True)
class Arm:
    #: vela arguments, as they appear in a run's `invocation.args`.
    args: dict[str, Any]
    #: How the post names this arm: chart label and text phrase.
    label: str


@dataclass(frozen=True)
class Claim:
    metric: str
    op: str
    min_trades: int
    titles: dict[str, str]


@dataclass(frozen=True)
class Question:
    path: Path
    sha256: str
    id: str
    question: str
    context: str
    kicker: str
    run: dict[str, Any]
    treatment: Arm
    baseline: Arm
    claim: Claim

    def wanted(self, arm: Arm) -> dict[str, Any]:
        """Every argument a run of this arm must have been given."""
        return {**self.run, **arm.args}

    @property
    def differs_in(self) -> set[str]:
        return set(self.treatment.args)


def _value(v: Any) -> Any:
    return None if v == "none" else v


def _arm(raw: dict[str, Any], name: str) -> Arm:
    if not isinstance(raw, dict):
        raise QuestionError(f"[{name}] is missing")
    label = raw.get("label")
    if not isinstance(label, str) or not label.strip():
        raise QuestionError(f"[{name}] needs a `label`: how the post names this arm")
    args = {k: _value(v) for k, v in raw.items() if k != "label"}
    if not args:
        raise QuestionError(f"[{name}] sets no argument, so it cannot differ from the other arm")
    return Arm(args=args, label=label.strip())


def _text(raw: dict[str, Any], key: str, where: str = "") -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QuestionError(f"`{where}{key}` is missing or empty")
    return value.strip()


def load_question(path: Path) -> Question:
    path = Path(path).expanduser().resolve()
    data = path.read_bytes()
    try:
        raw = tomllib.loads(data.decode())
    except tomllib.TOMLDecodeError as exc:
        raise QuestionError(f"{path}: {exc}") from None

    qid = _text(raw, "id")
    if qid != path.parent.name:
        # A copied question keeps its old id; a post must not silently inherit
        # another week's registration.
        raise QuestionError(f"id {qid!r} does not match its directory {path.parent.name!r}")

    run = {k: _value(v) for k, v in (raw.get("run") or {}).items()}
    treatment = _arm(raw.get("treatment"), "treatment")
    baseline = _arm(raw.get("baseline"), "baseline")
    if set(treatment.args) != set(baseline.args):
        raise QuestionError(
            "[treatment] and [baseline] must set the same arguments -- those are what the "
            f"comparison varies. treatment: {sorted(treatment.args)}, baseline: {sorted(baseline.args)}"
        )
    if same := [k for k in treatment.args if treatment.args[k] == baseline.args[k]]:
        raise QuestionError(f"the arms give the same value for {same}: that is not a difference")
    if shared := sorted(set(run) & set(treatment.args)):
        raise QuestionError(f"{shared} appear in [run] and in the arms; put them in one place")

    claim_raw = raw.get("claim") or {}
    metric = _text(claim_raw, "metric", "claim.")
    if metric not in METRICS:
        raise QuestionError(f"claim.metric {metric!r} is not one of {sorted(METRICS)}")
    op = claim_raw.get("op")
    if op not in OPS:
        raise QuestionError(f"claim.op must be one of {OPS}")
    min_trades = claim_raw.get("min_trades")
    if not isinstance(min_trades, int) or min_trades < 1:
        raise QuestionError("claim.min_trades must be a positive integer")
    titles = {v: _text(claim_raw, f"title_if_{v}", "claim.") for v in VERDICTS}

    return Question(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        id=qid,
        question=_text(raw, "question"),
        context=str(raw.get("context", "")).strip(),
        kicker=str(raw.get("kicker", "Weekly question")).strip(),
        run=run,
        treatment=treatment,
        baseline=baseline,
        claim=Claim(metric=metric, op=op, min_trades=min_trades, titles=titles),
    )
