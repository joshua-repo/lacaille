import pytest

from pictor.publish.question import QuestionError, load_question
from tests.pictor.publish.conftest import QID, QUESTION


def write(tmp_path, text, folder=QID):
    d = tmp_path / folder
    d.mkdir(exist_ok=True)
    (d / "question.toml").write_text(text)
    return d / "question.toml"


def test_a_valid_question_loads(tmp_path):
    q = load_question(write(tmp_path, QUESTION))
    assert q.id == QID
    assert q.baseline.args == {"iv_rank": None}  # "none" is vela's not-given
    assert q.wanted(q.treatment)["iv_rank"] == 0.5
    assert q.differs_in == {"iv_rank"}
    assert set(q.claim.titles) == {"true", "false", "inconclusive"}


def test_a_copied_question_keeps_the_wrong_id(tmp_path):
    with pytest.raises(QuestionError, match="does not match its directory"):
        load_question(write(tmp_path, QUESTION, folder="2026-w02-other"))


def test_the_arms_must_vary_the_same_arguments(tmp_path):
    text = QUESTION.replace('iv_rank = "none"', 'width = 10')
    with pytest.raises(QuestionError, match="must set the same arguments"):
        load_question(write(tmp_path, text))


def test_an_arm_identical_to_the_other_is_not_a_comparison(tmp_path):
    text = QUESTION.replace('iv_rank = "none"', "iv_rank = 0.5")
    with pytest.raises(QuestionError, match="same value"):
        load_question(write(tmp_path, text))


def test_only_the_fixed_metrics_can_be_claimed(tmp_path):
    text = QUESTION.replace('metric = "expectancy"', 'metric = "best_month"')
    with pytest.raises(QuestionError, match="not one of"):
        load_question(write(tmp_path, text))


def test_every_outcome_needs_its_title_written_in_advance(tmp_path):
    text = QUESTION.replace('title_if_inconclusive = "Too few trades to tell"\n', "")
    with pytest.raises(QuestionError, match="title_if_inconclusive"):
        load_question(write(tmp_path, text))


def test_a_question_must_pin_its_data(tmp_path):
    text = QUESTION.replace("as_of = 2026-01-01T00:00:00Z\n", "")
    with pytest.raises(QuestionError, match="as_of"):
        load_question(write(tmp_path, text))
