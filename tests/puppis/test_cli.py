"""`puppis check` against a fake broker."""

from __future__ import annotations

from puppis.cli import main
from puppis.guard import NotPaper
from tests.puppis.fakes import FakeBroker


def test_check_shows_account_positions_and_fills(capsys):
    broker = FakeBroker()
    assert main(["check"], make=lambda *a, **k: broker) == 0
    out = capsys.readouterr().out
    assert "DU1234567" in out and "(paper)" in out
    assert "SPY 2026-11-20 550P" in out
    assert "fee 1.30" in out and "ref p-1" in out
    assert broker.closed


def test_a_refusal_is_its_own_exit_code(capsys):
    broker = FakeBroker(refuse=NotPaper("U1 is not a paper account"))
    assert main(["check"], make=lambda *a, **k: broker) == 3
    assert "REFUSED" in capsys.readouterr().err


def test_the_client_id_reaches_the_broker():
    seen: dict[str, object] = {}

    def make(profile, client_id):
        seen.update(profile=profile, client_id=client_id)
        return FakeBroker()

    assert main(["check", "--client-id", "101"], make=make) == 0
    assert seen == {"profile": "paper", "client_id": 101}
