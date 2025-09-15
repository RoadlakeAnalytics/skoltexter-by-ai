"""Tests for `src/setup/ui/basic.py`."""

from src.setup.ui.basic import (
    ui_error,
    ui_header,
    ui_info,
    ui_menu,
    ui_rule,
    ui_status,
    ui_success,
    ui_warning,
)


def test_rich_ui_helpers_basic():
    """Exercise UI helpers; ensure no exceptions during rendering."""
    ui_rule("Test Section")
    ui_header("Test Header")
    with ui_status("Working..."):
        pass
    ui_info("info")
    ui_success("ok")
    ui_warning("warn")
    ui_error("err")
    ui_menu([("1", "Alpha"), ("2", "Beta")])


def test_rich_import_fallback_module_load(monkeypatch):
    """Simulate no-rich environment by causing import failure."""
    import builtins
    import importlib

    orig_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("no rich for this test")
        return orig_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    import src.setup.console_helpers as ch
    import src.setup.ui.basic as basic

    importlib.reload(ch)
    importlib.reload(basic)

    assert hasattr(ch, "ui_has_rich") and ch.ui_has_rich() is False
    basic.ui_rule("Fallback Rule")
    basic.ui_header("Fallback Header")
    with basic.ui_status("Working..."):
        pass
    basic.ui_info("info")
    basic.ui_success("ok")
    basic.ui_warning("warn")
    basic.ui_error("err")
    basic.ui_menu([("1", "Alpha"), ("2", "Beta")])
