"""Tests for streaming parsing variants in run_program."""

import importlib
import subprocess
from pathlib import Path


def _import_run_with_stub():
    import sys, types

    orig = sys.modules.get("src.setup.pipeline.orchestrator")
    stub = types.ModuleType("src.setup.pipeline.orchestrator")
    sys.modules["src.setup.pipeline.orchestrator"] = stub
    try:
        runmod = importlib.import_module("src.setup.pipeline.run")
    finally:
        if orig is None:
            del sys.modules["src.setup.pipeline.orchestrator"]
        else:
            sys.modules["src.setup.pipeline.orchestrator"] = orig
    return runmod, stub


def test_stream_parses_percent_and_fraction(monkeypatch):
    runmod, stub = _import_run_with_stub()
    monkeypatch.setattr(runmod, "get_python_executable", lambda: "/usr/bin/python")

    class FakeProc:
        def __init__(self, *a, **k):
            self.stdout = iter(["10%|\n", "2/5\n", "AI Processing completed: 2\n"])  # varied formats

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", FakeProc)
    # minimal stub orchestrator updater
    runmod._orch = stub
    monkeypatch.setattr(stub, "_TUI_UPDATER", lambda v: None, raising=False)
    monkeypatch.setattr(stub, "_compose_and_update", lambda: None, raising=False)
    ok = runmod.run_program("program_2", Path("src/program2_ai_processor.py"), stream_output=True)
    assert ok is True


def test_stream_handles_nonzero_return(monkeypatch):
    runmod, stub = _import_run_with_stub()
    monkeypatch.setattr(runmod, "get_python_executable", lambda: "/usr/bin/python")

    class FakeProc:
        def __init__(self, *a, **k):
            self.stdout = iter(["AI Processing completed: 1\n"])

        def wait(self):
            return 2

    monkeypatch.setattr(subprocess, "Popen", FakeProc)
    runmod._orch = stub
    monkeypatch.setattr(stub, "_TUI_UPDATER", lambda v: None, raising=False)
    monkeypatch.setattr(stub, "_compose_and_update", lambda: None, raising=False)
    ok = runmod.run_program("program_2", Path("src/program2_ai_processor.py"), stream_output=True)
    assert ok is False

