"""The paper guard: the only thing between puppis and a live account."""

from __future__ import annotations

import pytest

from puppis.guard import NotPaper, require_paper


def test_paper_accounts_pass():
    assert require_paper(["DU1234567", "DU7654321"]) == ["DU1234567", "DU7654321"]


@pytest.mark.parametrize("accounts", [["U16200976"], ["DU1234567", "U16200976"]])
def test_any_live_account_is_refused(accounts):
    with pytest.raises(NotPaper, match="U16200976 is not a paper account"):
        require_paper(accounts)


def test_no_accounts_is_refused_not_waved_through():
    # A gateway still logging in manages none; "nothing to check" is not "checked".
    with pytest.raises(NotPaper, match="no accounts"):
        require_paper([])
