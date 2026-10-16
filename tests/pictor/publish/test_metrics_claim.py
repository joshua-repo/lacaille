import pytest

from pictor.publish.claim import evaluate
from pictor.publish.metrics import dollars, percent, read
from pictor.publish.question import load_question
from tests.pictor.publish.conftest import QID, QUESTION


@pytest.fixture
def q(tmp_path):
    (tmp_path / QID).mkdir()
    (tmp_path / QID / "question.toml").write_text(QUESTION)
    return load_question(tmp_path / QID / "question.toml")


def summary(n, expectancy):
    return {"results": {"trades": {"n": n, "expectancy": expectancy}}}


def test_formats_carry_a_real_minus_sign():
    assert dollars(60.2) == "+$60"
    assert dollars(-43.1) == "−$43"
    assert percent(0.4528) == "+45.3%"


def test_total_return_cannot_be_claimed_alone():
    """The account is mostly cash: its total return is mostly the cash rate."""
    from pictor.publish.metrics import METRICS

    assert "total_return" not in METRICS
    assert "excess_return" in METRICS


def test_an_absent_metric_is_none_not_zero():
    assert read({"results": {"trades": {}}}, "expectancy") is None
    assert read({"results": {"curve": None}}, "sharpe") is None
    assert read(summary(5, 0.0), "expectancy") == 0.0


def test_the_rule_decides_the_title(q):
    o = evaluate(q, summary(20, 60.0), summary(40, -43.0))
    assert (o.verdict, o.title) == ("true", "The gate helped")
    o = evaluate(q, summary(20, -5.0), summary(40, 10.0))
    assert (o.verdict, o.title) == ("false", "The gate did not help")


def test_below_the_floor_on_either_side_is_inconclusive(q):
    assert evaluate(q, summary(9, 600.0), summary(40, -43.0)).verdict == "inconclusive"
    assert evaluate(q, summary(20, 600.0), summary(3, -43.0)).verdict == "inconclusive"


def test_a_metric_vela_did_not_compute_is_inconclusive(q):
    o = evaluate(q, summary(20, 60.0), {"results": {"trades": {"n": 40}}})
    assert o.verdict == "inconclusive"
    assert "did not compute" in o.reason
