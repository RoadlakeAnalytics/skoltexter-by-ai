"""Unit tests for `src.setup.pipeline.run.run_program` streaming and non-streaming.
"""

import subprocess
import sys as _sys
import types
import importlib
from types import SimpleNamespace
from pathlib import Path


def _import_run_with_stub():
    """Import the run module with a temporary orchestrator stub to avoid circular imports.

    Returns a tuple `(runmod, stub)` where `runmod` is the imported module and
    `stub` is the ModuleType instance that was used as the orchestrator during import.
    After the import the original orchestrator module is restored in sys.modules so
    other tests are unaffected; `runmod._orch` will still point to the stub.
    """
    orig = _sys.modules.get("src.setup.pipeline.orchestrator")
    stub = types.ModuleType("src.setup.pipeline.orchestrator")
    _sys.modules["src.setup.pipeline.orchestrator"] = stub
    try:
        runmod = importlib.import_module("src.setup.pipeline.run")
    finally:
        if orig is None:
            # restore by removing the temporary stub
            del _sys.modules["src.setup.pipeline.orchestrator"]
        else:
            _sys.modules["src.setup.pipeline.orchestrator"] = orig
    return runmod, stub


def test_run_program_non_stream(monkeypatch, tmp_path: Path):
    runmod, stub = _import_run_with_stub()
    monkeypatch.setattr(runmod, "get_python_executable", lambda: "/usr/bin/python")

    class R:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R())
    ok = runmod.run_program(
        "program_1", Path("src/program1_generate_markdowns.py"), stream_output=False
    )
    assert ok is True


def test_run_program_streaming(monkeypatch):
    runmod, stub = _import_run_with_stub()
    monkeypatch.setattr(runmod, "get_python_executable", lambda: "/usr/bin/python")

    # Prepare a fake Popen that yields lines
    class FakeProc:
        def __init__(self, *a, **k):
            self.stdout = iter(
                ["1/3\n", "AI Processing completed: 1\n"]
            )  # lines to be read

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", FakeProc)

    # Hook TUI updater to capture progress updates
    captured = {}

    def updater(x):
        captured.setdefault("u", []).append(x)

    # Set updater on orchestrator module used by run_program
    # Ensure runmod references the stub orchestrator and set updater
    runmod._orch = stub
    monkeypatch.setattr(stub, "_TUI_UPDATER", updater, raising=False)
    # Ensure the stub exposes the compose helper and a progress slot
    monkeypatch.setattr(stub, "_compose_and_update", lambda: None, raising=False)
    monkeypatch.setattr(stub, "_PROGRESS_RENDERABLE", None, raising=False)

    ok = runmod.run_program(
        "program_2", Path("src/program2_ai_processor.py"), stream_output=True
    )
    assert ok is True
    assert "u" in captured
