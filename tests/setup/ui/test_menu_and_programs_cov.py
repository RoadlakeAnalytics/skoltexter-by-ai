"""Tests that exercise menu and program UI branches to improve coverage.

They avoid interactive loops by providing deterministic responses via
monkeypatching and by supplying lightweight fake layout objects for the
rich dashboard paths.
"""

from types import SimpleNamespace
from pathlib import Path
import types

import src.setup.ui.menu as menu
import src.setup.ui.programs as programs


def test_ui_items_variants(monkeypatch):
    # Case when translate returns strings with ': '
    monkeypatch.setattr(menu, 'translate', lambda k: 'X: label')
    items = menu._ui_items()
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in items)

    # Case when translate returns strings without ': '
    monkeypatch.setattr(menu, 'translate', lambda k: 'Label only')
    items = menu._ui_items()
    assert all(len(v) > 0 for _, v in items)


def test_manage_env_calls_manager(monkeypatch):
    called = {}

    def fake_manage(project_root, venv_dir, req_file, req_lock, UI):
        called['ok'] = True

    monkeypatch.setattr(menu, 'manage_virtual_environment', fake_manage)
    menu._manage_env()
    assert called.get('ok') is True


def test_main_menu_plain_exit(monkeypatch):
    # Ensure the loop exits immediately when choosing '6'
    monkeypatch.setattr(menu, 'ui_rule', lambda *a, **k: None)
    monkeypatch.setattr(menu, 'ui_menu', lambda *a, **k: None)
    monkeypatch.setattr(menu, 'ask_text', lambda *a, **k: '6')
    # Patch actions to avoid side effects
    monkeypatch.setattr(menu, 'view_program_descriptions', lambda: None)
    monkeypatch.setattr(menu, 'run_processing_pipeline', lambda *a, **k: None)
    monkeypatch.setattr(menu, 'view_logs', lambda: None)
    monkeypatch.setattr(menu, 'reset_project', lambda: None)
    # Should return without looping forever
    menu._main_menu_plain()


def test_main_menu_rich_dashboard_flow(monkeypatch):
    # Provide a fake layout with a content slot that records updates
    class Slot:
        def __init__(self):
            self.last = None

        def update(self, v):
            self.last = v

    class Layout(dict):
        def __init__(self):
            super().__init__()
            self['content'] = Slot()

    fake_layout = Layout()

    monkeypatch.setattr(menu, 'build_dashboard_layout', lambda *a, **k: fake_layout)

    # sequence of choices: manage_env, view_program_descriptions, run, view_logs, reset, exit
    seq = iter(['1', '2', '3', '4', '5', '6'])
    monkeypatch.setattr(menu, 'ask_text', lambda *a, **k: next(seq))
    # Patch actions that would otherwise be heavy
    monkeypatch.setattr(menu, '_manage_env', lambda: None)
    monkeypatch.setattr(menu, 'view_program_descriptions', lambda: None)
    monkeypatch.setattr(menu, 'run_processing_pipeline', lambda content_updater=None: content_updater('ran') if content_updater else None)
    monkeypatch.setattr(menu, 'view_logs', lambda: None)
    monkeypatch.setattr(menu, 'reset_project', lambda: None)

    menu._main_menu_rich_dashboard()
    # After running, the layout content should have been updated at least once
    assert fake_layout['content'].last is not None


def test_get_program_descriptions_and_view_plain(monkeypatch, capsys):
    # Force simple translations
    monkeypatch.setattr(programs, 'translate', lambda k: f"T:{k}")
    # Provide a single choice then exit
    monkeypatch.setattr(programs, 'ask_text', lambda *a, **k: '0')
    monkeypatch.setattr(programs, 'ui_rule', lambda *a, **k: None)
    monkeypatch.setattr(programs, 'ui_menu', lambda *a, **k: None)
    programs.view_program_descriptions()
    # No exceptions and function returns
    captured = capsys.readouterr()
    assert captured is not None

