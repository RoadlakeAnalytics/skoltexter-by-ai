"""Tests for non-streaming branch of run_program in ``src.setup.pipeline.run``.

These unit tests stub subprocess calls to exercise error logging and
return-code handling without launching real processes.
"""

from types import SimpleNamespace
from pathlib import Path
import importlib
import types
import sys


def test_run_program_non_stream_error(monkeypatch):
    """When subprocess returns non-zero the helper should return False.

    Importing the `run` module can participate in a circular import with
    the orchestrator module, so install a lightweight stub for the
    pipeline package/orchestrator before importing the module under test.
    """
    # Install a minimal pipeline/orchestrator stub to avoid circular import
    fake_orch = types.ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = False
    fake_orch._TUI_UPDATER = None
    fake_orch._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", fake_orch)

    run_mod = importlib.import_module("src.setup.pipeline.run")

    # Stub python executable
    monkeypatch.setattr(run_mod, "get_python_executable", lambda: "/usr/bin/python", raising=False)

    # Stub subprocess.run to mimic a failing process
    def fake_run(*a, **k):
        return SimpleNamespace(returncode=1, stdout="out", stderr="err")

    monkeypatch.setattr(run_mod.subprocess, "run", fake_run, raising=False)

    ok = run_mod.run_program("prog", Path("src/prog.py"), stream_output=False)
    assert ok is False
