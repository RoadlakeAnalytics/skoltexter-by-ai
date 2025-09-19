"""Tests for src.setup.pipeline.status helpers."""

from src.setup.pipeline import status


def test_status_label_en_and_sv():
    assert "Waiting" in status._status_label("en", "waiting")
    assert "Väntar" in status._status_label("sv", "waiting")


def test_render_pipeline_table_fallback(monkeypatch):
    # Force the Table constructor to raise so the fallback SimpleTable is used
    import src.setup.console_helpers as ch

    monkeypatch.setattr(ch, "Table", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    tbl = status._render_pipeline_table(lambda k: k, "s1", "s2", "s3")
    # The fallback exposes columns and rows for inspection
    assert hasattr(tbl, "columns") and hasattr(tbl, "rows")
