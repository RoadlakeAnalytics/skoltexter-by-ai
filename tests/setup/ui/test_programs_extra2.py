"""Extra tests for programs UI helpers."""

import importlib
from types import SimpleNamespace
import src.setup.ui.programs as programs


def test_view_program_descriptions_rich_calls_rprint(monkeypatch):
    monkeypatch.setattr(
        programs, "get_program_descriptions", lambda: {"1": ("T", "BODY")}
    )
    monkeypatch.setattr(programs, "ui_menu", lambda items: None)
    seq = ["1", "0"]
    monkeypatch.setattr(programs, "ask_text", lambda prompt: seq.pop(0))
    monkeypatch.setattr(programs, "ui_has_rich", lambda: True)
    called = {}

    def rprint(v):
        called.setdefault("r", []).append(v)

    monkeypatch.setattr(programs, "rprint", rprint)
    programs.view_program_descriptions()
    assert called.get("r")


def test__view_logs_tui_invalid_selection_updates_info(monkeypatch, tmp_path):
    monkeypatch.setattr(programs, "LOG_DIR", tmp_path)
    # create a log file
    f = tmp_path / "a.log"
    f.write_text("hello")
    captured = {}

    def update_right(obj):
        captured["last"] = obj

    # choose an invalid selection then exit
    seq = ["nonexistent", "0"]
    monkeypatch.setattr(programs, "ask_text", lambda p: seq.pop(0))

    # Avoid importing/using the real `rich` Table/Panel/Syntax types which
    # can perform expensive operations. Provide minimal stand-ins that
    # implement the methods used by the code under test.
    class DummyTable:
        def __init__(self, *a, **k):
            pass

        def add_column(self, *a, **k):
            return None

        def add_row(self, *a, **k):
            return None

    class DummyPanel:
        def __init__(self, content, title=None, **k):
            self.content = content
            self.title = title

    class DummySyntax:
        def __init__(self, txt, lang, **k):
            self.txt = txt

    monkeypatch.setattr(programs, "Table", DummyTable, raising=False)
    monkeypatch.setattr(programs, "Panel", DummyPanel, raising=False)
    monkeypatch.setattr(programs, "Syntax", DummySyntax, raising=False)
    programs._view_logs_tui(update_right, lambda p: None)
    assert "last" in captured
