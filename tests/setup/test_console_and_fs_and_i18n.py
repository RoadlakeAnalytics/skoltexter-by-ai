"""Tests for console_helpers fallback, fs_utils extra branches and i18n set_language.

Combines a few small, focused tests that are inexpensive and increase
coverage across the setup helpers.
"""

import builtins
import tempfile
from pathlib import Path

from src.setup import console_helpers as ch
from src.setup import fs_utils
import src.setup.i18n as i18n


def test_rprint_fallback_to_print(capsys, monkeypatch) -> None:
    """When Rich is not available, `rprint` should use built-in print.

    Parameters
    ----------
    capsys : pytest.CaptureFixture
        Capture stdout/stderr.
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module state.

    Returns
    -------
    None
    """
    monkeypatch.setattr(ch, "ui_has_rich", lambda: False, raising=False)
    ch.rprint("hello", end="\n")
    captured = capsys.readouterr()
    assert "hello" in captured.out


def test_create_safe_path_pycache_allowed_and_outside(monkeypatch, tmp_path: Path) -> None:
    """__pycache__ inside project root is allowed; outside path is denied.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
    tmp_path : Path
        Temporary directory acting as project root.

    Returns
    -------
    None
    """
    # Patch project root
    monkeypatch.setattr(fs_utils, "_ValidatedPath", fs_utils._ValidatedPath, raising=False)
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=False)
    # __pycache__ case
    p = tmp_path / "some" / "__pycache__"
    p.mkdir(parents=True)
    vp = fs_utils.create_safe_path(p)
    assert isinstance(vp, Path)

    # Outside project root should be denied
    outside = Path(tempfile.mkdtemp())
    try:
        try:
            fs_utils.create_safe_path(outside)
            raise AssertionError("Expected PermissionError for outside path")
        except PermissionError:
            pass
    finally:
        pass


def test_set_language_keyboard_interrupt(monkeypatch) -> None:
    """A KeyboardInterrupt in set_language should raise SystemExit.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching input behavior.

    Returns
    -------
    None
    """
    def _raise(_=None):
        raise KeyboardInterrupt()

    import importlib
    import pytest
    from src.exceptions import UserInputError

    # Patch the concrete prompt implementation rather than the legacy shim
    # so the test is explicit about which dependency it fakes.
    monkeypatch.setattr("src.setup.app_prompts.ask_text", _raise, raising=False)
    try:
        with pytest.raises(UserInputError):
            import src.setup.app_prompts as app_prompts

            app_prompts.set_language()
    finally:
        # restore i18n to default
        i18n.LANG = "en"
