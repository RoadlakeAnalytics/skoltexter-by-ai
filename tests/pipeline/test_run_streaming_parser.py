"""Tests for streaming output parsing in ``src.setup.pipeline.run``.

These tests simulate a subprocess that emits different progress formats
and verify that the run helper updates the TUI progress renderable via
the registered updater callback.
"""

from pathlib import Path
import sys


def test_run_program_streaming_parses_and_updates(monkeypatch) -> None:
    """Streaming output with percent, fraction and done patterns updates progress.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching Popen and updater hooks.

    Returns
    -------
    None
    """
    recorded = []

    # To avoid circular imports during module import, install a fake
    # orchestrator module temporarily and import the run module after.
    fake_orch = type(sys)("src.setup.pipeline.orchestrator")
    fake_orch._TUI_UPDATER = None
    fake_orch._PROGRESS_RENDERABLE = None
    fake_orch._compose_and_update = lambda: None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", fake_orch)
    import importlib

    runmod = importlib.import_module("src.setup.pipeline.run")

    # Ensure updater on orchestrator is captured
    try:
        import src.setup.pipeline.orchestrator as orch
    except Exception:
        orch = None

    if orch is not None:
        monkeypatch.setattr(
            orch, "_TUI_UPDATER", lambda obj: recorded.append(obj), raising=False
        )
    # Also set a local updater on the run module to ensure it is invoked
    # even if the orchestrator module used by the run implementation is
    # not the same object we patched above.
    # Ensure the run module object has a local updater attribute patched
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.run", runmod)
    monkeypatch.setattr(
        runmod, "_TUI_UPDATER", lambda obj: recorded.append(obj), raising=False
    )

    # Fake process that yields lines resembling progress output
    class FakeProc:
        def __init__(self, lines):
            self.stdout = iter(lines)

        def wait(self):
            return 0

    lines = [
        "10%| some text\n",
        "1/4 processed\n",
        "AI Processing completed: 4\n",
    ]

    monkeypatch.setattr(
        runmod, "get_python_executable", lambda: "python", raising=False
    )
    monkeypatch.setattr(
        runmod.subprocess, "Popen", lambda *a, **k: FakeProc(lines), raising=False
    )

    ok = runmod.run_program("program_2", Path("src/program_2.py"), stream_output=True)
    assert ok is True
    assert recorded, "Updater should have been invoked with progress renderable"
