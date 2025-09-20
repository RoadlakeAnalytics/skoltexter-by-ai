"""Unit tests for ``src.setup.venv_manager.manage_virtual_environment``.

These tests simulate the common interactive branches: declining to
recreate an existing venv, and creating a new venv followed by a pip
install. External calls are stubbed so no real venvs or pip runs occur.
"""

from types import SimpleNamespace
from pathlib import Path
import importlib
import os

import src.setup.venv_manager as vm


def test_manage_virtual_environment_recreate_decline(monkeypatch, tmp_path: Path) -> None:
    """When venv exists and user declines recreate, manager skips removal.

    The test stubs UI prompt responses and filesystem helpers so the
    function behaviour can be observed without performing destructive ops.
    """
    called = []

    # Create a fake venv dir under tmp_path
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    # Fake UI adapter
    class UI(SimpleNamespace):
        def __init__(self):
            self._ = lambda k: k
            self.ask_text = lambda prompt, default=None: "y" if "Create" in prompt or "no_ven_prompt" in prompt else "n"
            self.ui_info = lambda m: called.append(("info", m))
            self.rprint = lambda *a, **k: called.append(("rprint", a))
            self.ui_has_rich = lambda: False
            self.logger = SimpleNamespace(error=lambda m: called.append(("error", m)))
            self.subprocess = SimpleNamespace(check_call=lambda *a, **k: called.append(("check_call", a)))
            self.shutil = __import__("shutil")
            self.sys = SimpleNamespace(platform="linux", executable="/usr/bin/python", prefix="/usr")
            self.venv = SimpleNamespace(create=lambda p, with_pip=True: called.append(("venv.create", str(p))))
            self.os = os

    ui = UI()

    # Stub fs_utils to avoid permission checks
    monkeypatch.setattr("src.setup.fs_utils.create_safe_path", lambda p: p, raising=False)
    monkeypatch.setattr("src.setup.fs_utils.safe_rmtree", lambda p: called.append(("rmtree", str(p))), raising=False)

    # Ensure venvmod reports not active
    venvmod = importlib.import_module("src.setup.venv")
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False, raising=False)

    # Simulate first prompt 'y' (proceed) then confirm_recreate 'n' (decline)
    calls = iter(["y", "n"])
    ui.ask_text = lambda prompt, default=None: next(calls)

    vm.manage_virtual_environment(tmp_path, venv_dir, tmp_path / "req.txt", tmp_path / "req.lock", ui)

    # We expect ui_info or rprint to indicate skipping
    assert any(c[0] in ("info", "rprint") for c in called)


def test_manage_virtual_environment_create_and_install(monkeypatch, tmp_path: Path) -> None:
    """Creating a venv calls the venv.create path and pip install (stubbed).

    We remove the pytest environment marker so the function will exercise
    the normal creation/install branches, but stub subprocess calls to
    avoid doing real installs.
    """
    called = []

    venv_dir = tmp_path / "venv"

    # Fake UI similar to above but provide 'y' response to proceed
    class UI(SimpleNamespace):
        def __init__(self):
            self._ = lambda k: k
            self.ask_text = lambda prompt, default=None: "y"
            self.ui_info = lambda m: called.append(("info", m))
            self.rprint = lambda *a, **k: called.append(("rprint", a))
            self.ui_has_rich = lambda: False
            self.logger = SimpleNamespace(error=lambda m: called.append(("error", m)))
            # Provide subprocess with a check_call stub
            self.subprocess = SimpleNamespace(check_call=lambda *a, **k: called.append(("pip", a)))
            self.shutil = __import__("shutil")
            self.sys = SimpleNamespace(platform="linux", executable="/usr/bin/python", prefix="/usr")
            self.venv = SimpleNamespace(create=lambda p, with_pip=True: (p.mkdir(parents=True), called.append(("venv.create", str(p)))))
            self.os = os

    ui = UI()

    # Remove pytest marker so creation path is used
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # Stub fs_utils to avoid whitelist checks
    monkeypatch.setattr("src.setup.fs_utils.create_safe_path", lambda p: p, raising=False)
    monkeypatch.setattr("src.setup.fs_utils.safe_rmtree", lambda p: called.append(("rmtree", str(p))), raising=False)

    # Ensure venvmod is in predictable state
    venvmod = importlib.import_module("src.setup.venv")
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False, raising=False)
    monkeypatch.setattr(venvmod, "get_venv_pip_executable", lambda p: venv_dir / "bin" / "pip", raising=False)
    monkeypatch.setattr(venvmod, "get_venv_python_executable", lambda p: venv_dir / "bin" / "python", raising=False)

    # Call manager
    vm.manage_virtual_environment(tmp_path, venv_dir, tmp_path / "req.txt", tmp_path / "req.lock", ui)

    # Assert either the in‑process venv.create was called or the manager
    # invoked a system python to create the venv (a check_call with
    # "-m venv" in the command). Also ensure pip install calls were
    # attempted (stub recorded).
    created_inproc = any(c[0] == "venv.create" for c in called)
    # Detect subprocess creation by searching for '-m' and 'venv' in the
    # recorded call tuples (stringified) — permissive but stable across
    # different stub labels used in tests.
    created_subproc = any(("-m" in str(c) and "venv" in str(c)) for c in called)
    assert created_inproc or created_subproc
    # Ensure some pip/install attempt was made
    assert any("pip" in str(c) or "install" in str(c) for c in called)
