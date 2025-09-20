"""Tests that reload ``src.setup.app`` under different import conditions.

These tests manipulate ``sys.modules`` to simulate absence or presence of
the optional ``rich`` package so both import branches in the module are
executed for coverage.
"""

import importlib
import sys
import types


def _reload_with_stubs(stubs: dict[str, types.ModuleType]):
    # Insert stubs and reload the target module
    backup = {}
    for name, mod in stubs.items():
        backup[name] = sys.modules.get(name)
        sys.modules[name] = mod
    # Remove module if already loaded
    if "src.setup.app" in sys.modules:
        del sys.modules["src.setup.app"]
    try:
        mod = importlib.import_module("src.setup.app")
    finally:
        # Restore original modules
        for name, orig in backup.items():
            if orig is None:
                del sys.modules[name]
            else:
                sys.modules[name] = orig
    return mod


def test_import_app_without_rich(monkeypatch):
    # Stub out src.setup.ui.menu to avoid heavy imports during reload
    fake_menu = types.ModuleType("src.setup.ui.menu")
    fake_menu.main_menu = lambda: None
    # Provide a dummy 'rich' package module so import of rich.panel fails
    fake_rich = types.ModuleType("rich")
    mod = _reload_with_stubs({"src.setup.ui.menu": fake_menu, "rich": fake_rich})
    assert getattr(mod, "Panel", None) is None


def test_import_app_with_minimal_rich(monkeypatch):
    fake_menu = types.ModuleType("src.setup.ui.menu")
    fake_menu.main_menu = lambda: None
    # Create a minimal rich.panel module with Panel attribute
    panel_mod = types.ModuleType("rich.panel")

    class DummyPanel:
        pass

    panel_mod.Panel = DummyPanel
    # Inject both package and submodule entries
    fake_rich_pkg = types.ModuleType("rich")
    sysmods = {
        "src.setup.ui.menu": fake_menu,
        "rich.panel": panel_mod,
        "rich": fake_rich_pkg,
    }
    mod = _reload_with_stubs(sysmods)
    assert getattr(mod, "Panel", None) is not None
