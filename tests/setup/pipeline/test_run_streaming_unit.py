"""Unit tests for streaming output parsing in ``src.setup.pipeline.run``.

These tests exercise the progressive parsing of percent, fraction and
completion lines and ensure UI updaters are invoked.
"""

from pathlib import Path

import src.setup.pipeline.run as run_mod


def test_run_program_streaming_parses_progress_and_calls_updaters(monkeypatch):
    """Ensure streaming output drives the progress renderer and updaters.

    We provide a fake subprocess.Popen implementation with an iterable
    ``stdout`` that yields a sequence of lines matching the expected
    regexes used by the parser. The test asserts that both the
    orchestrator compose/update hook and the updater callback are
    invoked.
    """
    captured = []
    composed = []

    def _updater(renderable):
        captured.append(renderable)

    def _compose():
        composed.append(True)

    # Attach test doubles onto the imported orchestrator object used by
    # the run module.
    monkeypatch.setattr(run_mod._orch, "_TUI_UPDATER", _updater, raising=False)
    monkeypatch.setattr(run_mod._orch, "_compose_and_update", _compose, raising=False)

    class FakeProc:
        def __init__(self, lines):
            # Provide an iterator over lines as file-like stdout
            self.stdout = iter(line + "\n" for line in lines)

        def wait(self):
            return 0

    lines = ["10%|", "1/4", "AI Processing completed: 4"]

    # Monkeypatch the Popen used by the run module
    monkeypatch.setattr(
        run_mod.subprocess, "Popen", lambda *a, **k: FakeProc(lines), raising=False
    )

    ok = run_mod.run_program("program_2", Path("src/program_2.py"), stream_output=True)
    assert ok is True
    assert captured, "Updater should have been called with a renderable"
    assert composed, "Compose/update hook should have been invoked"
