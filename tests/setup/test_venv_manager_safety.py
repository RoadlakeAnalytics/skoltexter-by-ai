"""Regression tests ensuring venv removal is guarded during test runs.

These tests verify the additional safety checks in
``src.setup.venv_manager`` that prevent accidental deletion of the
repository's canonical virtual environment when running under pytest.

"""

from pathlib import Path
import types
import subprocess

from src import config as cfg
import src.setup.venv_manager as vm


class _UI:
    """Lightweight UI adapter used for testing manager branches.

    The adapter provides the minimal attributes exercised by
    :func:`src.setup.venv_manager.manage_virtual_environment`.
    """

    def __init__(self, responses):
        self._ = lambda k: k
        self._seq = iter(responses)
        self.ui_has_rich = lambda: False
        self.logger = types.SimpleNamespace(error=lambda *a, **k: None, warning=lambda *a, **k: None)
        # Use the real subprocess module but allow tests to patch check_call
        self.subprocess = subprocess
        self.venv = types.SimpleNamespace(create=lambda *a, **k: None)
        self.os = __import__("os")
        self.shutil = __import__("shutil")
        # ui helpers used by the manager
        self.ui_info = lambda *a, **k: None
        self.rprint = lambda *a, **k: None
        self.sys = __import__("sys")

    def ask_text(self, prompt, default="y"):
        return next(self._seq)


def test_do_not_remove_project_venv_under_pytest(monkeypatch, tmp_path: Path):
    """Do not remove the project's VENV_DIR when running under pytest.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture used to set environment and patch functions.
    tmp_path : pathlib.Path
        Temporary filesystem path used to host a fake project venv.

    Returns
    -------
    None
        The test asserts that ``safe_rmtree`` is not invoked for the
        canonical project venv when ``PYTEST_CURRENT_TEST`` is present.
    """
    # Arrange: point the concrete config value at a temporary venv inside tmp_path
    proj_venv = tmp_path / "venv_project"
    proj_venv.mkdir()
    monkeypatch.setattr(cfg, "VENV_DIR", proj_venv, raising=True)

    # Ensure code believes we're running under pytest and answer prompts 'y','y'
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    ui = _UI(["y", "y"])  # proceed and confirm recreate

    called = {}

    # Patch the destructive helper to record invocations if any
    monkeypatch.setattr("src.setup.fs_utils.safe_rmtree", lambda p: called.setdefault("invoked", True), raising=True)
    # Prevent actual subprocess calls (pip install etc.) during the test
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: None)

    # Act
    vm.manage_virtual_environment(cfg.PROJECT_ROOT, cfg.VENV_DIR, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui)

    # Assert: safe_rmtree must not have been called for the canonical project venv
    assert called.get("invoked", False) is False
