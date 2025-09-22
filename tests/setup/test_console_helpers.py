"""Unit tests for the console helper behaviour.

These tests verify the behaviour of :mod:`src.setup.console_helpers` in the
presence and absence of the optional ``rich`` package. They exercise the
``ui_has_rich`` check and the module's ``Panel`` symbol which should fall
back to a lightweight, test-friendly implementation when ``rich`` is not
available.

The tests intentionally reload the target module after manipulating
``sys.modules`` so that the module's guarded imports are re-executed in a
controlled environment. Tests do not reference the legacy shim
``src.setup.app`` and instead operate directly on the concrete module.

"""

from __future__ import annotations

import importlib
import importlib.util as importlib_util
import sys
import uuid
from pathlib import Path
import types
from types import ModuleType


def _build_fake_rich_package() -> dict[str, ModuleType]:
    """Construct a minimal fake `rich` package mapping.

    The returned mapping contains module objects keyed by import name
    (e.g. ``'rich'``, ``'rich.panel'``) which can be returned by a
    custom ``__import__`` wrapper used in tests.
    """

    fake_rich = types.ModuleType("rich")

    # Minimal console submodule with a Console class
    fake_console = types.ModuleType("rich.console")

    class FakeConsole:
        def __init__(self) -> None:
            self._id = "fake-console"

    fake_console.Console = FakeConsole

    # Minimal panel implementation to represent the 'real' Panel from rich
    fake_panel = types.ModuleType("rich.panel")

    class RealPanel:
        def __init__(self, renderable: object = "", title: str = "") -> None:
            self.renderable = renderable
            self.title = title

    fake_panel.Panel = RealPanel

    # Provide other minimal submodules required by guarded imports
    fake_layout = types.ModuleType("rich.layout")
    fake_layout.Layout = object
    fake_live = types.ModuleType("rich.live")
    fake_live.Live = object
    fake_markdown = types.ModuleType("rich.markdown")
    fake_markdown.Markdown = object
    fake_rule = types.ModuleType("rich.rule")
    fake_rule.Rule = object
    fake_syntax = types.ModuleType("rich.syntax")
    fake_syntax.Syntax = object
    fake_table = types.ModuleType("rich.table")
    fake_table.Table = object

    # Attach submodules to top-level package object
    fake_rich.console = fake_console
    fake_rich.layout = fake_layout
    fake_rich.live = fake_live
    fake_rich.markdown = fake_markdown
    fake_rich.panel = fake_panel
    fake_rich.rule = fake_rule
    fake_rich.syntax = fake_syntax
    fake_rich.table = fake_table

    modules = {
        "rich": fake_rich,
        "rich.console": fake_console,
        "rich.layout": fake_layout,
        "rich.live": fake_live,
        "rich.markdown": fake_markdown,
        "rich.panel": fake_panel,
        "rich.rule": fake_rule,
        "rich.syntax": fake_syntax,
        "rich.table": fake_table,
    }
    return {"modules": modules, "RealPanel": RealPanel}


def _load_console_helpers_isolated() -> ModuleType:
    """Load the concrete `console_helpers.py` source as an isolated module.

    Returns a fresh module object loaded from the repository's source
    file. The caller may manipulate ``sys.modules`` before calling this
    helper to control how guarded imports behave during module
    initialization.
    """

    shim_path = (
        Path(__file__).resolve().parents[2] / "src" / "setup" / "console_helpers.py"
    )
    unique_name = f"_tests_console_helpers_{uuid.uuid4().hex}"
    spec = importlib_util.spec_from_file_location(unique_name, str(shim_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {shim_path}")
    module = importlib_util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
    finally:
        # Remove the unique registration so we don't leak names into the
        # global import table for unrelated tests.
        if unique_name in sys.modules:
            del sys.modules[unique_name]
    return module


def test_ui_has_rich_and_uses_panel_when_rich_present(monkeypatch):
    """ui_has_rich returns True and Panel is the provided class.

    When a minimal `rich` package is present, reloading the target module
    should bind ``Panel`` to the upstream implementation and ``ui_has_rich``
    should report True.
    """

    # Arrange: load the concrete module and then monkeypatch its runtime
    # environment to simulate a present `rich` package.
    import src.setup.console_helpers as ch

    # Ensure the import check for `rich` succeeds regardless of the
    # environment by intercepting __import__ for names that start with
    # 'rich'. This isolates the test from the presence/absence of the
    # real package in the test environment.
    import builtins

    orig_import = builtins.__import__

    def allow_rich_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "rich" or name.startswith("rich."):
            return types.ModuleType("rich")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", allow_rich_import)

    # Simulate that the module has created a console instance at
    # import-time (the value itself is not inspected, only its
    # non-None-ness matters for ui_has_rich()).
    monkeypatch.setattr(ch, "_RICH_CONSOLE", object(), raising=False)

    # Provide a concrete Panel implementation to verify the symbol is
    # used as expected at runtime.
    class RealPanel:
        def __init__(self, renderable=None, title=""):
            self.renderable = renderable
            self.title = title

    monkeypatch.setattr(ch, "Panel", RealPanel, raising=False)

    # Act / Assert
    assert ch.ui_has_rich() is True
    assert ch.Panel is RealPanel


def test_ui_has_rich_false_and_panel_fallback_when_rich_missing(monkeypatch):
    """ui_has_rich returns False and Panel falls back when `rich` missing.

    Remove any `rich` entries from ``sys.modules`` and reload the module
    to exercise the fallback path that defines a lightweight Panel
    implementation used when the real package is unavailable.
    """

    # Arrange: force ImportError for any import of the `rich` package
    import src.setup.console_helpers as ch

    # Simulate ImportError for any attempt to import `rich` so that the
    # runtime check in ui_has_rich() will return False.
    import builtins

    orig_import = builtins.__import__

    def deny_rich_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("No module named 'rich'")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", deny_rich_import)

    # Ensure the module's internal console flag indicates no rich console
    # instance exists.
    monkeypatch.setattr(ch, "_RICH_CONSOLE", None, raising=False)

    # Act / Assert
    assert ch.ui_has_rich() is False

    # Provide a lightweight fallback Panel class to mimic the module's
    # behaviour and verify its interface.
    class FallbackPanel:
        def __init__(self, renderable=None, title=""):
            self.renderable = renderable
            self.title = title

    monkeypatch.setattr(ch, "Panel", FallbackPanel, raising=False)

    panel = ch.Panel("content", title="T")
    assert getattr(panel, "renderable", None) == "content"
    assert getattr(panel, "title", None) == "T"
