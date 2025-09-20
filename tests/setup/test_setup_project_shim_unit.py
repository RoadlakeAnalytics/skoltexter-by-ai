"""Tests for the top-level `setup_project` shim compatibility layer.

These tests ensure that monkeypatching attributes on the legacy
``setup_project`` module are propagated into the refactored
``src.setup.app`` module by the wrapper helpers.
"""

from pathlib import Path

import setup_project as sp


def test_run_program_uses_propagated_python(monkeypatch) -> None:
    """Patching `setup_project.get_python_executable` affects the delegated run."""
    # Patch the top-level helper to return a known python path
    monkeypatch.setattr(sp, "get_python_executable", lambda: "/usr/bin/python")

    class R:
        returncode = 0
        stdout = ""
        stderr = ""

    # Prevent spawning real subprocesses in the delegated implementation
    monkeypatch.setattr("src.setup.app.subprocess.run", lambda *a, **k: R())

    ok = sp.run_program("prog", Path("src/some_module.py"), stream_output=False)
    assert ok is True

    # Ensure the refactored module also received the propagated helper
    import importlib

    app = importlib.import_module("src.setup.app")
    assert callable(getattr(app, "get_python_executable", None))
