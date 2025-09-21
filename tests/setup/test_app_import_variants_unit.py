"""Tests that exercise the top-level import-time branches in ``src.setup.app``.

Reloading the module under controlled ``sys.modules`` setups exercises
different import/fallback paths and increases coverage of the guarded
optional-import logic.
"""

import importlib
import sys
import types

import importlib

# Import the actual module object so import-time tests can access its
# `__file__` attribute deterministically and so reloads behave as
# expected when manipulating ``sys.modules``.
app = importlib.import_module("src.setup.app")


def test_app_import_with_rich_panel_stub(monkeypatch):
    """When a stubbed ``rich`` and ``rich.panel`` are present the module
    should pick up the provided ``Panel`` implementation.
    """
    rich = types.ModuleType("rich")
    # Simulate a stubbed package (no __path__)
    rich.__path__ = None
    panel_mod = types.ModuleType("rich.panel")

    class P:
        def __init__(self, renderable, title=""):
            self.renderable = renderable
            self.title = title

    panel_mod.Panel = P
    monkeypatch.setitem(sys.modules, "rich", rich)
    monkeypatch.setitem(sys.modules, "rich.panel", panel_mod)

    # Load the source as a fresh module so import-time logic runs
    # against the manipulated sys.modules entries.
    import importlib.util

    spec = importlib.util.spec_from_file_location("tmp_app_mod", app.__file__)
    tmp_mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "tmp_app_mod", tmp_mod)
    spec.loader.exec_module(tmp_mod)
    assert getattr(tmp_mod, "Panel", None) is P


def test_app_import_with_rich_stub_but_no_panel(monkeypatch):
    """If ``rich`` is stubbed but no ``rich.panel`` is available the
    import logic should gracefully fall back to Panel=None.
    """
    rich = types.ModuleType("rich")
    rich.__path__ = None
    monkeypatch.setitem(sys.modules, "rich", rich)
    # Ensure there is no rich.panel entry
    monkeypatch.setitem(sys.modules, "rich.panel", None)

    import importlib.util

    spec = importlib.util.spec_from_file_location("tmp_app_mod2", app.__file__)
    tmp2 = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "tmp_app_mod2", tmp2)
    spec.loader.exec_module(tmp2)
    assert getattr(tmp2, "Panel", None) is None
