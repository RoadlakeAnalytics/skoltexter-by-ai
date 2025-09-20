"""Extra tests for pipeline status helpers."""

import importlib

from src.setup.pipeline import status


def test_status_label_en_and_sv():
    assert "Waiting" in status._status_label("en", "waiting")
    assert "Väntar" in status._status_label("sv", "waiting")


def test_render_pipeline_table_fallback(monkeypatch):
    """If the rich Table raises, the fallback simple table should be returned."""
    ch = importlib.import_module("src.setup.console_helpers")

    # Make Table constructor raise to force fallback
    monkeypatch.setattr(ch, "Table", lambda *a, **k: (_ for _ in ()).throw(Exception("no rich")), raising=False)
    tbl = status._render_pipeline_table(lambda k: k, "S1", "S2", "S3")
    # Fallback simple table exposes columns and rows
    assert hasattr(tbl, "columns") and hasattr(tbl, "rows")
    assert len(tbl.rows) == 3

