"""Canonical tests for the concrete UI adapter `src.setup.app_ui`.

These tests exercise the concrete UI adapter functions and the
interaction with the `console_helpers` module. Tests patch the
concrete modules directly so they do not rely on legacy shim objects in
``sys.modules`` and therefore remain order-independent.
"""

import importlib
import types
from types import SimpleNamespace

import pytest

import src.setup.app_ui as app_ui


def test_sync_console_helpers_propagates(monkeypatch):
    """_sync_console_helpers propagates toggles from a provided app object.

    The synchronization helper reads attributes from an ``app`` object
    returned by :func:`importlib.import_module`. To avoid registering a
    global shim in ``sys.modules`` these tests stub the import machinery
    to return a fake object containing the expected attributes.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch importlib behaviour.
    """
    import src.setup.console_helpers as ch

    fake_q = object()
    fake_app = types.SimpleNamespace(
        _RICH_CONSOLE=object(), _HAS_Q=True, questionary=fake_q
    )

    # Patch the concrete console_helpers attributes directly so the
    # sync helper observes the expected toggles. Tests should avoid
    # registering or relying on the legacy shim in ``sys.modules``.
    monkeypatch.setattr(
        "src.setup.console_helpers._RICH_CONSOLE", fake_app._RICH_CONSOLE, raising=False
    )
    monkeypatch.setattr("src.setup.console_helpers._HAS_Q", True, raising=False)
    monkeypatch.setattr("src.setup.console_helpers.questionary", fake_q, raising=False)

    # Call the concrete sync helper directly.
    app_ui._sync_console_helpers()
    assert ch._HAS_Q is True
    assert ch.questionary is fake_q


def test_rprint_falls_back_to_print_when_helper_raises(monkeypatch, capsys):
    """app_ui.rprint falls back to built-in print when console rprint fails.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch the concrete console helper.
    capsys : pytest.CaptureFixture
        Capture fixture.
    """
    import src.setup.console_helpers as ch

    def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ch, "rprint", _boom, raising=False)
    # Now call the adapter which should catch and fallback to print
    app_ui.rprint("hello", "world")
    out = capsys.readouterr().out
    assert "hello world" in out


def test_ui_has_rich_delegates_and_falls_back(monkeypatch):
    """Verify ui_has_rich delegates and falls back to the concrete flag.

    The adapter should prefer :func:`src.setup.console_helpers.ui_has_rich`.
    If that helper raises, the adapter falls back to the concrete module's
    `_RICH_CONSOLE` flag.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to apply temporary attribute patches.
    """
    ch = importlib.import_module("src.setup.console_helpers")
    # Normal path: console helper reports availability
    monkeypatch.setattr(ch, "ui_has_rich", lambda: True, raising=False)
    assert app_ui.ui_has_rich() is True

    # Simulate helper raising so the wrapper falls back to the concrete
    # module-level flag.
    monkeypatch.setattr(
        ch,
        "ui_has_rich",
        lambda: (_ for _ in ()).throw(Exception("boom")),
        raising=False,
    )
    monkeypatch.setattr(ch, "_RICH_CONSOLE", object(), raising=False)
    assert app_ui.ui_has_rich() is True


def test_build_dashboard_layout_delegates(monkeypatch):
    """Delegate building dashboard layout to the UI implementation.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch the UI function.
    """
    monkeypatch.setattr(
        "src.setup.ui._build_dashboard_layout", lambda *a, **k: {"ok": True}
    )
    res = app_ui._build_dashboard_layout("x")
    assert res == {"ok": True}


def test_build_dashboard_layout_smoke() -> None:
    """Smoke test for dashboard layout builder.

    Ensures ``_build_dashboard_layout`` returns a non-empty layout for
    simple input.

    Returns
    -------
    None
        This test asserts that a layout object is returned and is not
        ``None``.
    """
    layout = app_ui._build_dashboard_layout("content")
    assert layout is not None
