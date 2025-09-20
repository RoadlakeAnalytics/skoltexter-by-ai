"""Additional orchestrator tests to cover compose/update and step logic.

These tests exercise the TUI compose/update logic and the step runner
branches (success, failure, skip, invalid) without launching subprocesses.
"""

from pathlib import Path
import types

import src.setup.pipeline.orchestrator as orch


def test_compose_and_update_calls_updater(monkeypatch):
    """When both status and progress renderables are present the updater is called."""
    called = {}

    def upd(obj):
        called['obj'] = obj

    # Set TUI mode and attach updater
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", upd, raising=False)

    # Provide simple renderables
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", "S", raising=False)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", "P", raising=False)

    orch._compose_and_update()
    assert 'obj' in called
    # The composed object should expose .items for inspection
    assert hasattr(called['obj'], 'items')


def test_set_tui_mode_restore(monkeypatch):
    """set_tui_mode should toggle TUI flags and the returned restore should revert them."""
    prev = (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER)

    def right(v):
        pass

    rest = orch.set_tui_mode(right, None)
    assert orch._TUI_MODE is True
    # restore
    rest()
    assert (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER) == prev


def test_run_pipeline_step_branches(monkeypatch):
    """Exercise the success, failure, skip and invalid branches of a step."""
    # success path
    monkeypatch.setattr(orch, 'ask_text', lambda p, default='y': 'y', raising=False)
    monkeypatch.setattr(orch, 'run_program', lambda name, path, stream_output=False: True, raising=False)
    calls = {}
    monkeypatch.setattr(orch, 'ui_success', lambda m: calls.setdefault('succ', m), raising=False)
    ok = orch._run_pipeline_step('prompt', 'program_1', Path('p.py'), 'fail', 'ok')
    assert ok is True
    assert 'succ' in calls

    # failure path (run_program returns False)
    monkeypatch.setattr(orch, 'ask_text', lambda p, default='y': 'y', raising=False)
    monkeypatch.setattr(orch, 'run_program', lambda name, path, stream_output=False: False, raising=False)
    calls = {}
    monkeypatch.setattr(orch, 'ui_warning', lambda m: calls.setdefault('warn', m), raising=False)
    ok2 = orch._run_pipeline_step('prompt', 'program_1', Path('p.py'), 'fail', 'ok')
    assert ok2 is False
    assert 'warn' in calls

    # skip branch
    monkeypatch.setattr(orch, 'ask_text', lambda p, default='y': 's', raising=False)
    calls = {}
    monkeypatch.setattr(orch, 'ui_info', lambda m: calls.setdefault('info', m), raising=False)
    ok3 = orch._run_pipeline_step('prompt', 'program_1', Path('p.py'), 'fail', 'ok', skip_message='skip_msg')
    assert ok3 is True
    assert 'info' in calls

    # invalid input branch
    monkeypatch.setattr(orch, 'ask_text', lambda p, default='y': 'x', raising=False)
    calls = {}
    monkeypatch.setattr(orch, 'ui_warning', lambda m: calls.setdefault('warn2', m), raising=False)
    ok4 = orch._run_pipeline_step('prompt', 'program_1', Path('p.py'), 'fail', 'ok')
    assert ok4 is False
    assert 'warn2' in calls


def test_run_pipeline_by_name_calls_runners(monkeypatch):
    """run_pipeline_by_name should dispatch to the appropriate handlers."""
    # program_1 -> run_markdown
    monkeypatch.setattr(orch, 'run_markdown', lambda: True, raising=False)
    assert orch.run_pipeline_by_name('program_1') is True

    # program_2 -> ai_processor_main (should not raise)
    monkeypatch.setattr(orch, 'ai_processor_main', lambda: None, raising=False)
    assert orch.run_pipeline_by_name('program_2') is True

    # program_3 -> run_website
    monkeypatch.setattr(orch, 'run_website', lambda: True, raising=False)
    assert orch.run_pipeline_by_name('program_3') is True

