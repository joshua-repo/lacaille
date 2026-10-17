"""One weekly post: `post.png`, `post.md` and `lock.json`, or a refusal.

The order is the point. The question is loaded and the house rules checked
before a single number is read for display; the verdict comes from the
registered rule; only then is anything drawn or written. Every sentence of the
text is assembled from the registered question and the verified figures --
nothing here chooses a phrasing after seeing the result.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

from pictor.publish.brand import Brand, load_brand
from pictor.publish.chart import equity_vs_baseline
from pictor.publish.claim import Outcome, evaluate
from pictor.publish.metrics import percent
from pictor.publish.provenance import Refused, Selection, select
from pictor.publish.question import Question, load_question
from pictor.publish.render import screenshot
from pictor.publish.runs import discover, trading_pnl

SIZE = (1200, 627)          # LinkedIn's link-image size
DASH = "—"
TEMPLATE = Path(__file__).with_name("templates") / "post.html"


@dataclass(frozen=True)
class Text:
    body: str
    limitations: str
    words: int


@dataclass(frozen=True)
class Built:
    out: Path
    outcome: Outcome
    selection: Selection
    words: int


def _fmt(outcome: Outcome, value: float | None) -> str:
    return DASH if value is None else outcome.metric.fmt(value)


def compose(q: Question, outcome: Outcome, t: dict[str, Any], b: dict[str, Any]) -> Text:
    data = t["data"]
    fill = t["engine"]["fill"]
    args = t["invocation"]["args"]
    sym = data["symbol"]

    sentences = [q.question]
    if q.context:
        sentences.append(q.context)
    sentences.append(
        f"We compared trading {q.treatment.label} with trading {q.baseline.label}, "
        f"on {sym} from {data['start']} to {data['end']}."
    )
    sentences.append(
        f"{outcome.title}: the {outcome.metric.label} was {_fmt(outcome, outcome.treatment)} "
        f"against {_fmt(outcome, outcome.baseline)}, over {outcome.treatment_trades} and "
        f"{outcome.baseline_trades} trades."
    )
    body = " ".join(sentences)

    move = data.get("underlying_move")
    limits = [
        f"{sym} only, {data['start']} to {data['end']} ({data['sessions']} sessions); "
        f"{outcome.treatment_trades} and {outcome.baseline_trades} trades; in-sample only.",
        f"{sym} moved {percent(move)} over the window." if move is not None else
        "The underlying's move over the window was not recorded.",
        f"Costs assume {fill['haircut']:g} half-spreads crossed per leg and "
        f"${fill['commission']:.2f} per contract.",
    ]
    cash_rate = t["engine"].get("cash_rate")
    if cash_rate:
        limits.append(
            f"Idle cash earns {cash_rate * 100:.1f}% a year in the backtest; the chart and the "
            "per-trade figures exclude it."
        )
    version = data.get("version") or {}
    if version.get("as_of"):
        limits.append(f"Data as stored on {version['as_of'][:10]}.")
    if outcome.verdict == "inconclusive":
        limits.append(f"Inconclusive: {outcome.reason}.")
    return Text(body=body, limitations=" ".join(limits), words=len(body.split()))


def _page(brand: Brand, q: Question, outcome: Outcome, chart: str) -> str:
    c = brand.color
    e = html.escape
    numsub = (
        f"{e(outcome.metric.label)}, vs {e(_fmt(outcome, outcome.baseline))} {e(q.baseline.label)}"
        f"<br>{outcome.treatment_trades} vs {outcome.baseline_trades} trades · in-sample"
    )
    return Template(TEMPLATE.read_text()).substitute(
        fonts=brand.font_faces(),
        bg=c["bg"], ink=c["ink"], sub=c["sub"], accent=c["accent"], muted=c["muted"], rule=c["rule"],
        head=brand.head, body=brand.body, gradient=brand.gradient_css,
        kicker=e(q.kicker), title=e(outcome.title), number=e(_fmt(outcome, outcome.treatment)),
        numsub=numsub, lockup=brand.svg("lockup", 46, "lk"), chart=chart, footer=e(brand.footer),
    )


def _markdown(q: Question, outcome: Outcome, text: Text, brand: Brand) -> str:
    return "\n".join([
        f"# {outcome.title}",
        "",
        f"**{_fmt(outcome, outcome.treatment)}** {outcome.metric.label} {q.treatment.label}, "
        f"vs {_fmt(outcome, outcome.baseline)} {q.baseline.label}",
        "",
        text.body,
        "",
        f"**Limitations.** {text.limitations}",
        "",
        f"*{brand.footer}*",
        "",
    ])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pictor_git() -> dict[str, Any]:
    here = Path(__file__).resolve().parent
    def git(*a: str) -> str:
        r = subprocess.run(["git", "-C", str(here), *a], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    return {"sha": git("rev-parse", "HEAD") or None, "dirty": bool(git("status", "--porcelain"))}


def build_post(question_path: Path, runs_root: Path, brand_root: Path | None = None) -> Built:
    q = load_question(question_path)
    brand = load_brand(brand_root)
    runs, _ = discover(runs_root)
    sel = select(q, runs)                      # raises Refused
    t, b = sel.treatment.run, sel.baseline.run
    outcome = evaluate(q, t.summary, b.summary)
    text = compose(q, outcome, t.summary, b.summary)

    chart = equity_vs_baseline(
        brand, trading_pnl(t), trading_pnl(b), (q.treatment.label, q.baseline.label),
        initial=float(t.summary["engine"]["initial_cash"]), size=(7.0, 4.05),
    )
    out = q.path.parent / "out"
    out.mkdir(exist_ok=True)
    page = out / "post.html"
    page.write_text(_page(brand, q, outcome, chart))
    png = out / "post.png"
    screenshot(page, png, SIZE)
    md = out / "post.md"
    md.write_text(_markdown(q, outcome, text, brand))

    def run_record(choice) -> dict[str, Any]:
        r = choice.run
        return {"run": str(r.path), "run_at": r.run_at.isoformat(), "matched": choice.matched,
                "vela": r.summary["git"], "data_version": r.summary["data"].get("version")}

    lock = {
        "question": {"id": q.id, "path": str(q.path), "sha256": q.sha256,
                     "registered_at": sel.registered_at.isoformat()},
        "treatment": run_record(sel.treatment),
        "baseline": run_record(sel.baseline),
        "outcome": {"verdict": outcome.verdict, "reason": outcome.reason, "title": outcome.title,
                    "metric": outcome.metric.key, "treatment": outcome.treatment,
                    "baseline": outcome.baseline},
        "words": text.words,
        "outputs": {p.name: _sha256(p) for p in (png, md, page)},
        "pictor": _pictor_git(),
        "built_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    (out / "lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    return Built(out=out, outcome=outcome, selection=sel, words=text.words)


__all__ = ["Built", "Refused", "build_post", "compose"]
