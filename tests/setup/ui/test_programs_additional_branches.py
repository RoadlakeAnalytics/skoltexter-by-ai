"""Extra branch tests for ``src.setup.ui.programs``.

These tests exercise the rich/non-rich display paths, invalid choice
handling and the non-interactive "no logs" branches for the programs
helper functions.

"""

from types import SimpleNamespace
from pathlib import Path

import src.setup.ui.programs as programs


def test_view_program_descriptions_rich_and_invalid(monkeypatch) -> None:
    """Display uses Markdown when rich is available; invalid choices are handled.

    The test stubs out the Markdown constructor (to avoid depending on the
    optional `rich` package) and replaces ``rprint`` with a recorder. It
    verifies that selecting a valid program calls ``rprint`` with a
    Markdown-like object and that an invalid selection results in the
    translated "invalid_choice" being printed.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module attributes.

    Returns
    -------
    None
    """
    printed = []

    def _rprint(obj, *a, **k):
        printed.append(obj)

    # Provide a simple Markdown-like constructor and ensure ui_has_rich
    monkeypatch.setattr(
        programs, "Markdown", lambda s: SimpleNamespace(text=s), raising=False
    )
    monkeypatch.setattr(programs, "rprint", _rprint, raising=False)
    monkeypatch.setattr(programs, "ui_menu", lambda items: None, raising=False)

    # First: valid selection (choose '1' then exit)
    seq = ["1", "0"]
    monkeypatch.setattr(programs, "ask_text", lambda prompt: seq.pop(0), raising=False)
    monkeypatch.setattr(programs, "ui_has_rich", lambda: True, raising=False)
    programs.view_program_descriptions()
    assert any(
        hasattr(x, "text") for x in printed
    ), "Markdown-like object should be printed"

    # Reset and test invalid selection path
    printed.clear()
    seq2 = ["9", "0"]
    monkeypatch.setattr(programs, "ask_text", lambda prompt: seq2.pop(0), raising=False)
    monkeypatch.setattr(programs, "ui_has_rich", lambda: False, raising=False)
    programs.view_program_descriptions()
    # invalid choice should produce the module's translated string
    expected = programs.translate("invalid_choice")
    assert any(isinstance(x, str) and expected in x for x in printed)


def test_view_logs_no_log_files_and_invalid_choice(monkeypatch, tmp_path: Path) -> None:
    """When LOG_DIR has no .log files, output shows 'no logs'; invalid
    selections are reported.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module attributes.
    tmp_path : Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """
    out = []

    def _rprint(obj, *a, **k):
        out.append(obj)

    # Create a directory with a non-log file so log_files list becomes empty
    (tmp_path / "ignore.txt").write_text("nope")
    monkeypatch.setattr(programs, "LOG_DIR", tmp_path, raising=False)
    monkeypatch.setattr(programs, "rprint", _rprint, raising=False)
    # view_logs should detect no log files and print something
    programs.view_logs()
    assert out, "Expected output when no logs are present"

    # Now create a log and choose an invalid item to trigger invalid_choice
    out.clear()
    (tmp_path / "a.log").write_text("content")
    seq = ["x", "0"]
    monkeypatch.setattr(programs, "ask_text", lambda prompt: seq.pop(0), raising=False)
    monkeypatch.setattr(programs, "ui_menu", lambda items: None, raising=False)
    monkeypatch.setattr(programs, "ui_rule", lambda arg: None, raising=False)
    monkeypatch.setattr(programs, "ui_has_rich", lambda: False, raising=False)
    programs.view_logs()
    expected_invalid = programs.translate("invalid_choice")
    assert any(isinstance(x, str) and expected_invalid in x for x in out)
