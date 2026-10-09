"""House rules A1, A3, A4 and A6, checked before anything is drawn.

Each check either passes or raises `Refused` with a sentence saying which rule
and why. There is no flag to skip one: a post that cannot show where its
numbers came from does not get made.

- **A1, registered first.** The question file is committed, unchanged since,
  and every run used is newer than that commit. A matching run that is *older*
  than the commit is a refusal, not a footnote: it means the result existed
  before the question was fixed -- which is also what editing a question after
  seeing its result looks like.
- **A3, no choosing.** Of the runs that match an arm, the earliest is used,
  always. How many matched is recorded.
- **A4, a real baseline.** The two runs differ in exactly the arguments the
  question says they differ in. Anything else and the comparison is not the one
  that was registered.
- **A6, reproducible.** Both runs come from a clean, identical vela checkout,
  and neither was allowed to fetch.
"""

from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pictor.publish.question import Arm, Question
from pictor.publish.runs import Run

#: Arguments that change where or how a run is reported, not what it computes.
IGNORED = frozenset({"out", "label", "envelope", "breakeven"})


class Refused(Exception):
    """A house rule is not met; no artefact is produced."""


@dataclass(frozen=True)
class Choice:
    run: Run
    #: Runs that matched this arm after registration (the chosen one included).
    matched: int


@dataclass(frozen=True)
class Selection:
    registered_at: dt.datetime
    treatment: Choice
    baseline: Choice


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise Refused(f"A1: git failed in {repo}: {out.stderr.strip()}")
    return out.stdout.strip()


def registered_at(question: Question) -> dt.datetime:
    """When the question, exactly as it is now, was committed."""
    repo, name = question.path.parent, question.path.name
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--error-unmatch", name], capture_output=True
    )
    if tracked.returncode != 0:
        raise Refused(f"A1: {question.path} is not committed. Register the question before running it.")
    if _git(repo, "status", "--porcelain", "--", name):
        raise Refused(
            f"A1: {question.path} has changes that are not committed. A question is fixed by its "
            "commit; an edit is a new registration, and runs made before it no longer count."
        )
    stamp = _git(repo, "log", "-1", "--format=%cI", "--", name)
    return dt.datetime.fromisoformat(stamp)


def _norm(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_norm(v) for v in value]
    return value


def _differs(args: dict[str, Any], wanted: dict[str, Any]) -> list[str]:
    return [k for k, v in wanted.items() if _norm(args.get(k, KeyError)) != _norm(v)]


def _choose(question: Question, arm: Arm, name: str, runs: list[Run], since: dt.datetime) -> Choice:
    wanted = question.wanted(arm)
    matching = [r for r in runs if not _differs(r.args, wanted)]
    early = [r for r in matching if r.run_at <= since]
    if early:
        raise Refused(
            f"A1: {len(early)} {name} run(s) matching this question predate its registration "
            f"({since.isoformat()}), the oldest {early[0].name}. The result existed before the "
            "question was fixed."
        )
    if not matching:
        nearest = min(runs, key=lambda r: len(_differs(r.args, wanted)), default=None)
        hint = (
            f" The nearest run, {nearest.name}, differs in {_differs(nearest.args, wanted)}."
            if nearest
            else " There are no runs at all."
        )
        raise Refused(f"no {name} run matches the question.{hint}")
    return Choice(run=matching[0], matched=len(matching))


def _check_pair(question: Question, t: Run, b: Run) -> None:
    keys = (set(t.args) | set(b.args)) - IGNORED
    differ = {k for k in keys if _norm(t.args.get(k)) != _norm(b.args.get(k))}
    if differ != question.differs_in:
        raise Refused(
            f"A4: the runs differ in {sorted(differ)}, the question registers a difference in "
            f"{sorted(question.differs_in)} only. That baseline is not the registered one."
        )
    for run in (t, b):
        if run.args.get("fetch"):
            raise Refused(f"A6: {run.name} was allowed to fetch data; a published run must be offline.")
        git = run.summary.get("git") or {}
        if git.get("dirty") is not False:
            raise Refused(
                f"A6: {run.name} ran from a vela checkout with uncommitted changes "
                f"(git.dirty = {git.get('dirty')}). Its code cannot be named, so it cannot be reproduced."
            )
    if (t.summary["git"].get("sha")) != (b.summary["git"].get("sha")):
        raise Refused("A6: the two runs come from different vela versions.")


def select(question: Question, runs: list[Run]) -> Selection:
    since = registered_at(question)
    treatment = _choose(question, question.treatment, "treatment", runs, since)
    baseline = _choose(question, question.baseline, "baseline", runs, since)
    _check_pair(question, treatment.run, baseline.run)
    return Selection(registered_at=since, treatment=treatment, baseline=baseline)
