"""Tests for the basic UI primitives exercising both rich and fallback paths."""

import types
import sys

import src.setup.ui.basic as basic


def test_ui_basic_fallback(monkeypatch, capsys):
    # Force fallback path
    monkeypatch.setattr(basic, "ui_has_rich", lambda: False)
    monkeypatch.setattr(basic, "_RICH_CONSOLE", None)

    basic.ui_rule("T")
    basic.ui_header("H")
    with basic.ui_status("Working"):
        pass
    basic.ui_info("info")
    basic.ui_success("ok")
    basic.ui_warning("warn")
    basic.ui_error("err")
    basic.ui_menu([("1", "A"), ("2", "B")])
    out = capsys.readouterr().out
    assert "T" in out or "H" in out


def test_ui_basic_rich(monkeypatch):
    # Provide a fake console with a print method to capture calls
    class FakeConsole:
        def __init__(self):
            self.calls = []

        def print(self, *a, **k):
            self.calls.append((a, k))

        def status(self, message, spinner=None):
            # Provide a simple synchronous context manager compatible with
            # the usage in ui_status (which is not async).
            class Ctx:
                def __enter__(self):
                    return None

                def __exit__(self, exc_type, exc, tb):
                    return False

            return Ctx()

    fake = FakeConsole()
    monkeypatch.setattr(basic, "ui_has_rich", lambda: True)
    monkeypatch.setattr(basic, "_RICH_CONSOLE", fake)

    # Provide simple fakes for Rule, Panel.fit and Table so Rich-branches
    # construct objects without needing the real `rich` package.
    class FakeRule:
        def __init__(self, title, style=None):
            self.title = title

        def __str__(self):
            return f"RULE:{self.title}"

    class FakePanel:
        def __init__(self, renderable: any = "", title: str = "") -> None:
            self.renderable = renderable
            self.title = title

        @classmethod
        def fit(cls, title: str, **kwargs):
            return cls(renderable=title, title=title)

    class FakeTable:
        def __init__(self, *a, **k):
            self._cols = []
            self._rows = []

        def add_column(self, name, **k):
            self._cols.append(name)

        def add_row(self, *row):
            self._rows.append(tuple(row))

        def __str__(self):
            return f"TABLE rows={self._rows}"

    monkeypatch.setattr(basic, "Rule", FakeRule)
    monkeypatch.setattr(basic, "Panel", FakePanel)
    monkeypatch.setattr(basic, "Table", FakeTable)

    basic.ui_rule("T")
    basic.ui_header("H")
    # status returns a context manager; invoke it to ensure no exceptions
    with basic.ui_status("Working"):
        pass
    basic.ui_info("info")
    basic.ui_success("ok")
    basic.ui_warning("warn")
    basic.ui_error("err")
    basic.ui_menu([("1", "A"), ("2", "B")])

    # Ensure the fake console received print calls
    assert fake.calls
