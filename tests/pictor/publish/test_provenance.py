"""The house rules a post cannot be made without."""

import datetime as dt

import pytest

from pictor.publish.provenance import Refused, select
from pictor.publish.question import load_question
from pictor.publish.runs import discover, trading_pnl
from tests.publish.conftest import T0, make_run, register

H = dt.timedelta(hours=1)


def pick(posts, root):
    return select(load_question(posts / "2026-w01-test" / "question.toml"), discover(root)[0])


def both(root, at, **kw):
    make_run(root, f"{at:%H%M}_t", run_at=at, iv_rank=0.5, **kw)
    make_run(root, f"{at:%H%M}_b", run_at=at + dt.timedelta(minutes=1), **kw)


def test_registered_then_run_is_accepted(posts, tmp_path):
    register(posts)
    both(tmp_path / "runs", T0 + H)
    sel = pick(posts, tmp_path / "runs")
    assert sel.treatment.run.args["iv_rank"] == 0.5
    assert sel.baseline.run.args["iv_rank"] is None


def test_the_earliest_run_is_used_and_the_rest_are_counted(posts, tmp_path):
    register(posts)
    both(tmp_path / "runs", T0 + H, expectancy=1.0)
    both(tmp_path / "runs", T0 + 2 * H, expectancy=99.0)  # a nicer rerun does not win
    sel = pick(posts, tmp_path / "runs")
    assert sel.treatment.run.summary["results"]["trades"]["expectancy"] == 1.0
    assert sel.treatment.matched == 2


def test_an_uncommitted_question_is_refused(posts, tmp_path):
    from tests.publish.conftest import QUESTION

    (posts / "2026-w01-test" / "question.toml").write_text(QUESTION)
    with pytest.raises(Refused, match="A1: .* not committed"):
        pick(posts, tmp_path / "runs")


def test_an_edit_not_yet_committed_is_refused(posts, tmp_path):
    path = register(posts)
    path.write_text(path.read_text().replace("The gate helped", "The gate helped a lot"))
    with pytest.raises(Refused, match="A1: .* not committed"):
        pick(posts, tmp_path / "runs")


def test_a_result_older_than_its_question_is_refused(posts, tmp_path):
    both(tmp_path / "runs", T0 - H)
    register(posts)
    with pytest.raises(Refused, match="A1: .* predate its registration"):
        pick(posts, tmp_path / "runs")


def test_rewriting_a_question_after_its_runs_is_refused(posts, tmp_path):
    path = register(posts)
    both(tmp_path / "runs", T0 + H)
    path.write_text(path.read_text().replace("The gate helped", "The gate clearly helped"))
    from tests.publish.conftest import git
    git(posts, "commit", "-qam", "reword after seeing it", when=T0 + 2 * H)
    with pytest.raises(Refused, match="predate its registration"):
        pick(posts, tmp_path / "runs")


def test_a_baseline_that_differs_in_more_than_the_question_is_refused(posts, tmp_path):
    register(posts)
    make_run(tmp_path / "runs", "t", run_at=T0 + H, iv_rank=0.5)
    make_run(tmp_path / "runs", "b", run_at=T0 + H, rate=0.05)  # and a different rate
    with pytest.raises(Refused, match="A4"):
        pick(posts, tmp_path / "runs")


@pytest.mark.parametrize("kw, rule", [({"dirty": True}, "uncommitted changes"),
                                      ({"fetch": True}, "allowed to fetch")])
def test_an_irreproducible_run_is_refused(posts, tmp_path, kw, rule):
    register(posts)
    both(tmp_path / "runs", T0 + H, **kw)
    with pytest.raises(Refused, match=f"A6: .*{rule}"):
        pick(posts, tmp_path / "runs")


def test_runs_from_two_vela_versions_are_refused(posts, tmp_path):
    register(posts)
    make_run(tmp_path / "runs", "t", run_at=T0 + H, iv_rank=0.5, sha="aaa")
    make_run(tmp_path / "runs", "b", run_at=T0 + H, sha="bbb")
    with pytest.raises(Refused, match="different vela versions"):
        pick(posts, tmp_path / "runs")


def test_no_match_names_the_nearest_run(posts, tmp_path):
    register(posts)
    make_run(tmp_path / "runs", "t", run_at=T0 + H, iv_rank=0.6)
    with pytest.raises(Refused, match=r"no treatment run matches.*differs in \['iv_rank'\]"):
        pick(posts, tmp_path / "runs")


def test_trading_pnl_excludes_cash_interest_and_vendor_columns(tmp_path):
    """Equity 105,000 with 4,000 of it interest is 1,000 of trading P&L."""
    make_run(tmp_path, "r", run_at=T0)
    rows = trading_pnl(discover(tmp_path)[0][0])
    assert rows[0] == (dt.date(2025, 1, 2), 0.0)
    assert rows[-1] == (dt.date(2025, 12, 31), 1000.0)  # no `spot`, no carry


def test_a_run_from_before_the_cash_rate_has_no_carry_to_remove(tmp_path):
    make_run(tmp_path, "r", run_at=T0, interest=False)
    assert trading_pnl(discover(tmp_path)[0][0])[-1][1] == 1000.0


def test_a_cash_rate_without_an_interest_column_is_refused(tmp_path):
    import json

    from pictor.publish.runs import RunError

    out = make_run(tmp_path, "r", run_at=T0, interest=False)
    summary = json.loads((out / "summary.json").read_text())
    summary["engine"]["cash_rate"] = 0.04
    (out / "summary.json").write_text(json.dumps(summary))
    with pytest.raises(RunError, match="no interest column"):
        trading_pnl(discover(tmp_path)[0][0])


def test_an_unknown_summary_schema_is_refused(tmp_path):
    from pictor.publish.runs import RunError

    make_run(tmp_path, "r", run_at=T0, schema=7)
    with pytest.raises(RunError, match="schema 7"):
        discover(tmp_path)
