from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def no_real_antlia_config(tmp_path, monkeypatch):
    """puppis resolves the gateway's endpoints through antlia.auth; never let a
    test read the developer's own ~/.antlia or ANTLIA_* settings."""
    monkeypatch.setenv("ANTLIA_HOME", str(tmp_path))
    for key in [k for k in os.environ if k.startswith("ANTLIA_") and k != "ANTLIA_HOME"]:
        monkeypatch.delenv(key, raising=False)
