"""Tests for `src/setup/pipeline/run.py`."""

import sys
from pathlib import Path

import src.setup.pipeline.orchestrator as orch
import src.setup.pipeline.run as sp
from src.setup.console_helpers import Table


def test_run_program_stream_fail_and_exception(monkeypatch, tmp_path: Path):
    class P:
        def wait(self):
            return 1

    from src.setup import venv as v

    monkeypatch.setattr(v, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp.subprocess, "Popen", lambda *a, **k: P())
    assert sp.run_program("program_1", tmp_path / "x.py", stream_output=True) is False

    monkeypatch.setattr(
        sp.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert sp.run_program("program_2", tmp_path / "x.py", stream_output=False) is False


def test_run_program_stream_and_capture(monkeypatch, tmp_path: Path):
    # Placeholder; covered in orchestrator TUI tests.
    pass




def test_run_program_tui_progress_parsing(monkeypatch, tmp_path: Path):
    """Simulate program_2 subprocess with tqdm-like output and ensure updates."""
    # Enable TUI
    updates: list[object] = []
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=True)
    monkeypatch.setattr(
        sp, "_TUI_UPDATER", lambda obj: updates.append(obj), raising=True
    )
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", Table(), raising=True)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", None, raising=True)

    class FakeStdout:
        def __iter__(self):
            # Emit tqdm-like percent, fraction, and completed summary
            yield " 12%|#####      | 12/100 [00:01<00:08]
"
            yield "55/100 [00:04<00:03]
"
            yield "AI Processing completed: 100
"

    class FakeProc:
        def __init__(self):
            self.stdout = FakeStdout()

        def wait(self):
            return 0

    monkeypatch.setattr(sp.subprocess, "Popen", lambda *a, **k: FakeProc())
    ok = sp.run_program("program_2", tmp_path / "x.py", stream_output=True)
    assert ok is True and updates, "Expected updates during TUI progress parsing"

def test_run_program_tui_progress_done_only(monkeypatch, tmp_path: Path):
    """Cover branch setting total from done line when it was None."""
    updates: list[object] = []
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=True)
    monkeypatch.setattr(
        sp, "_TUI_UPDATER", lambda obj: updates.append(obj), raising=True
    )
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", Table(), raising=True)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", None, raising=True)

    class FakeStdout:
        def __iter__(self):
            yield "AI Processing completed: 10
"

    class FakeProc:
        def __init__(self):
            self.stdout = FakeStdout()

        def wait(self):
            return 0

    monkeypatch.setattr(sp.subprocess, "Popen", lambda *a, **k: FakeProc())
    ok = sp.run_program("program_2", tmp_path / "x.py", stream_output=True)
    assert ok is True

def test_run_program_tui_progress_failure(monkeypatch, tmp_path: Path):
    """Cover failure branch after capturing output (non-zero return code)."""
    updates: list[object] = []
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=True)
    monkeypatch.setattr(
        sp, "_TUI_UPDATER", lambda obj: updates.append(obj), raising=True
    )
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", Table(), raising=True)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", None, raising=True)

    class FakeStdout:
        def __iter__(self):
            yield "noise line
"

    class FakeProc:
        def __init__(self):
            self.stdout = FakeStdout()

        def wait(self):
            return 2

    monkeypatch.setattr(sp.subprocess, "Popen", lambda *a, **k: FakeProc())
    ok = sp.run_program("program_2", tmp_path / "x.py", stream_output=True)
    assert ok is False
