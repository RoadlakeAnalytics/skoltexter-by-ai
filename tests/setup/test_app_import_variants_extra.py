"""Extra import-variant tests for ``src.setup.app``.

These reload the top-level module under different ``sys.modules`` states to
exercise the guarded optional-import logic for `rich` and the UI menu.
"""

import importlib
import sys
import types


def _reload_with_restore(stubs: dict[str, types.ModuleType]):
    backup = {}
    for name, mod in stubs.items():
        backup[name] = sys.modules.get(name)
        sys.modules[name] = mod
    if "src.setup.app" in sys.modules:
        del sys.modules["src.setup.app"]
    try:
        mod = importlib.import_module("src.setup.app")
    finally:
        for name, orig in backup.items():
            if orig is None:
                try:
                    del sys.modules[name]
                except Exception:
                    pass
            else:
                sys.modules[name] = orig
    return mod


def test_reload_app_with_realistic_rich_and_menu():
    # Provide a minimal ui.menu so the top-level import can succeed
    fake_menu = types.ModuleType("src.setup.ui.menu")
    fake_menu.main_menu = lambda: None
    # Ensure the system import path is used for rich.panel (may or may not
    # exist in the environment). This primarily triggers the importlib
    # import branch in the module top-level logic.
    mod = _reload_with_restore({"src.setup.ui.menu": fake_menu})
    assert getattr(mod, "__name__", "") == "src.setup.app"


def test_reload_app_with_stubbed_rich_panel(monkeypatch):
    # Simulate a stub 'rich' package (no __path__) and a 'rich.panel' stub
    fake_rich = types.ModuleType("rich")
    fake_rich.__path__ = None
    panel_mod = types.ModuleType("rich.panel")

    class DummyPanel:
        pass

    panel_mod.Panel = DummyPanel
    mod = _reload_with_restore(
        {
            "rich": fake_rich,
            "rich.panel": panel_mod,
            "src.setup.ui.menu": types.ModuleType("src.setup.ui.menu"),
        }
    )
    # Panel should be taken from the stubbed submodule
    assert getattr(mod, "Panel", None) is not None
