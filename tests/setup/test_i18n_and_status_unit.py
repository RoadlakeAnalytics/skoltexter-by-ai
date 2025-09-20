"""Tests for i18n helpers and pipeline status rendering."""

from types import SimpleNamespace

import src.setup.i18n as i18n
from src.setup.pipeline import status as status_mod


def test_status_label_en_and_sv():
    assert "Waiting" in status_mod._status_label("en", "waiting")
    assert "Väntar" in status_mod._status_label("sv", "waiting")


def test_render_pipeline_table_fallback(monkeypatch):
    # Force Table constructor to raise so fallback _SimpleTable is used
    import src.setup.console_helpers as ch

    class BadTable:
        def __init__(self, *a, **k):
            raise RuntimeError("no table")

    monkeypatch.setattr(ch, "Table", BadTable)

    def translate(k: str) -> str:
        return "T"

    t = status_mod._render_pipeline_table(translate, "s1", "s2", "s3")
    # Fallback table exposes .rows
    assert hasattr(t, "rows") and len(t.rows) == 3


def test_set_language_selects_and_exits(monkeypatch):
    monkeypatch.setattr(i18n, "LANG", "en")
    # Simulate selecting Swedish
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    i18n.set_language()
    assert i18n.LANG == "sv"

