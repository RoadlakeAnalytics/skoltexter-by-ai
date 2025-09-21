"""Additional tests exercising branches in the concrete setup modules.

These tests were migrated away from the legacy `src.setup.app` shim and
now patch the concrete modules used by the application. This avoids
global mutable shims in `sys.modules` and makes test dependencies
explicit.
"""

from types import SimpleNamespace
import importlib
import types

import src.setup.app_ui as _app_ui


def test_sync_console_helpers_propagation(monkeypatch):
    """Ensure that console helper toggles are propagated from the app module.

    This test stubs the import machinery so that the synchronization helper
    reads the expected attributes from a fake "app" object without
    registering a global shim in ``sys.modules``.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        The pytest monkeypatch fixture used to replace importlib behaviour.

    Returns
    -------
    None
    """
    import src.setup.console_helpers as ch

    fake_q = object()
    fake_app = types.SimpleNamespace(_RICH_CONSOLE=object(), _HAS_Q=True, questionary=fake_q)

    # Patch the import system used inside the sync helper to return our
    # fake app object when the legacy name is requested.
    monkeypatch.setattr("importlib.import_module", lambda name: fake_app)

    # Call the concrete, refactored sync helper directly.
    _app_ui._sync_console_helpers()
    assert ch._HAS_Q is True
    assert ch.questionary is fake_q
