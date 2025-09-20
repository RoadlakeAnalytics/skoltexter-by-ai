"""Additional tests for prompts and console helpers to exercise TUI+questionary branches."""

import sys
import types
import builtins

import src.setup.ui.prompts as prom
import src.setup.console_helpers as ch


def test_ask_text_tui_updater(monkeypatch):
    # Install a fake orchestrator module so the prompts adapter sees the
    # expected TUI state regardless of prior test pollution.
    import importlib as _il
    import types as _types

    called = {}

    def prompt_updater(v):
        called['v'] = v

    orch = _types.ModuleType('src.setup.pipeline.orchestrator')
    orch._TUI_MODE = True
    orch._TUI_UPDATER = lambda x: None
    orch._TUI_PROMPT_UPDATER = prompt_updater
    monkeypatch.setitem(sys.modules, 'src.setup.pipeline.orchestrator', orch)
    pkg = _il.import_module('src.setup.pipeline')
    setattr(pkg, 'orchestrator', orch)

    # Ensure pytest internal env var is not present so getpass branch is used
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    import getpass, builtins
    monkeypatch.setattr(getpass, 'getpass', lambda prompt='': 'secret')
    monkeypatch.setattr(builtins, 'input', lambda prompt='': 'secret')
    # Run
    val = prom.ask_text('p')
    assert val == 'secret'
    # The prompt updater should have been called with a Panel-like object
    assert 'v' in called


def test_questionary_fallback_on_exception(monkeypatch):
    # Simulate questionary present but raising inside ask()
    monkeypatch.setattr(ch, '_HAS_Q', True)

    class Q:
        @staticmethod
        def text(prompt, default=''):
            class A:
                def ask(self):
                    raise RuntimeError('boom')

            return A()

    monkeypatch.setattr(ch, 'questionary', Q)
    # Fallback to input
    monkeypatch.setattr(builtins, 'input', lambda prompt='': 'fallback')
    assert prom.ask_text('p') == 'fallback'


def test_ui_has_rich_dynamic(monkeypatch):
    # Ensure ui_has_rich returns False when rich not importable
    monkeypatch.setitem(sys.modules, 'rich', None)
    # For tests we can directly assert boolean based on _RICH_CONSOLE
    monkeypatch.setattr(ch, '_RICH_CONSOLE', None)
    assert ch.ui_has_rich() is False
    # When console present, it should return True
    monkeypatch.setattr(ch, '_RICH_CONSOLE', object())
    # Provide an importable dummy rich package for the dynamic check
    monkeypatch.setitem(sys.modules, 'rich', types.ModuleType('rich'))
    assert ch.ui_has_rich() is True
