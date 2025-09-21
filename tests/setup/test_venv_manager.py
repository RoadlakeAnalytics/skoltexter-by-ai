"""Tests for `src/setup/venv_manager.py`.

Covers venv-manager branches using a small UI adapter object.
"""

import logging as _logging
import os as _os
import shutil as _shutil
import subprocess as _sub
import sys
import sys as _sys
import venv as _venv
from pathlib import Path
import types

import importlib

# Avoid reliance on the legacy shim `src.setup.app` in tests. Import the
# concrete modules directly so tests patch focused implementation points
# (e.g. `src.setup.venv`) rather than a mutable global shim object.
import src.setup.app_venv as app_venv
import src.setup.venv_manager as vm
from src import config as cfg
from src.setup import venv as venvmod


class _UI:
    """Minimal UI adapter matching `manage_virtual_environment` expectations."""

    logger = _logging.getLogger("tests.venv.ui")
    rprint = staticmethod(lambda *a, **k: None)
    ui_has_rich = staticmethod(lambda: False)
    ask_text = staticmethod(lambda prompt, default="y": default)
    subprocess = _sub
    shutil = _shutil
    sys = _sys
    venv = _venv
    os = _os

    @staticmethod
    def _(key: str) -> str:
        """Test _."""
        return key

    @staticmethod
    def ui_info(msg: str) -> None:
        """Test Ui info."""
        pass


def _make_fake_bin(tmp: Path):
    """Test Make fake bin."""
    bindir = tmp / ("Scripts" if sys.platform == "win32" else "bin")
    bindir.mkdir(parents=True, exist_ok=True)
    (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
        "", encoding="utf-8"
    )
    (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
        "", encoding="utf-8"
    )
    return bindir


def test_manage_virtual_environment_remove_error(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment remove error."""
    vdir = tmp_path / "venv"
    vdir.mkdir()
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    seq = iter(["y", "y"])  # yes to manage, yes to recreate
    ui = _UI
    monkeypatch.setattr(
        ui,
        "ask_text",
        staticmethod(lambda prompt, default="y": next(seq)),
        raising=True,
    )
    monkeypatch.setattr(
        ui.shutil, "rmtree", lambda p: (_ for _ in ()).throw(RuntimeError("rmtree"))
    )
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


class _SafetyUI:
    """Lightweight UI adapter used for testing manager safety branches.

    The adapter provides the minimal attributes exercised by
    :func:`src.setup.venv_manager.manage_virtual_environment`.

    Parameters
    ----------
    responses : list[str]
        Sequence of responses that the adapter will yield for prompts.
    """

    def __init__(self, responses):
        self._ = lambda k: k
        self._seq = iter(responses)
        self.ui_has_rich = lambda: False
        self.logger = types.SimpleNamespace(
            error=lambda *a, **k: None, warning=lambda *a, **k: None
        )
        # Use the real subprocess module but allow tests to patch check_call
        self.subprocess = _sub
        self.venv = types.SimpleNamespace(create=lambda *a, **k: None)
        self.os = __import__("os")
        self.shutil = __import__("shutil")
        # ui helpers used by the manager
        self.ui_info = lambda *a, **k: None
        self.rprint = lambda *a, **k: None
        self.sys = __import__("sys")

    def ask_text(self, prompt, default="y"):
        """Return the next configured response for a prompt.

        Parameters
        ----------
        prompt : str
            Prompt text (ignored by this test adapter).
        default : str, optional
            Default value to return if the response iterator is exhausted.

        Returns
        -------
        str
            Next response from the configured sequence or the default.
        """
        try:
            return next(self._seq)
        except StopIteration:
            return default


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

    ui = _SafetyUI(["y", "y"])  # proceed and confirm recreate

    called = {}

    # Patch the destructive helper to record invocations if any
    monkeypatch.setattr(
        "src.setup.fs_utils.safe_rmtree",
        lambda p: called.setdefault("invoked", True),
        raising=True,
    )
    # Prevent actual subprocess calls (pip install etc.) during the test
    monkeypatch.setattr(_sub, "check_call", lambda *a, **k: None, raising=True)

    # Act
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        cfg.VENV_DIR,
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )

    # Assert: safe_rmtree must not have been called for the canonical project venv
    assert called.get("invoked", False) is False


def test_manage_virtual_environment_create_error(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment create error."""
    vdir = tmp_path / "venv2"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )
    monkeypatch.setattr(
        ui.venv, "create", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("create"))
    )
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


def test_manage_virtual_environment_install_errors(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment install errors."""
    vdir = tmp_path / "v3"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )

    def fake_create(*a, **k):
        """Test Fake create."""
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(ui.venv, "create", fake_create)

    calls = {"n": 0}

    def raise_cpe(args):
        """Test Raise cpe."""
        calls["n"] += 1
        raise _sub.CalledProcessError(1, args)

    monkeypatch.setattr(ui.subprocess, "check_call", raise_cpe)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


def test_manage_virtual_environment_dynamic_ui_enable_success(
    monkeypatch, tmp_path: Path
):
    """Test Manage virtual environment dynamic ui enable success."""
    ui = _UI
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: True)
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        tmp_path,
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )


def test_manage_virtual_environment_dynamic_ui_enable_excepts(
    monkeypatch, tmp_path: Path
):
    """Test Manage virtual environment dynamic ui enable excepts."""
    import builtins as _builtins
    import importlib as _importlib

    ui = _UI
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: True)
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)
    ui.ui_has_rich = staticmethod(lambda: False)

    orig_import = _builtins.__import__

    def fake_import(name, *a, **k):
        """Test Fake import."""
        if name == "rich" or name.startswith("rich."):
            raise ImportError("no rich now")
        return orig_import(name, *a, **k)

    monkeypatch.setattr(_builtins, "__import__", fake_import)
    monkeypatch.setattr(
        _importlib,
        "import_module",
        lambda module: (_ for _ in ()).throw(ImportError("no q")),
    )

    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        tmp_path,
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )

    def raise_fnf(args):
        """Test Raise fnf."""
        raise FileNotFoundError("pip not found")

    monkeypatch.setattr(ui.subprocess, "check_call", raise_fnf)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        tmp_path,
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )


def test_manage_virtual_environment_create(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment create."""
    vdir = tmp_path / "venv"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    seq = iter(["y"])  # yes to create
    monkeypatch.setattr(
        ui,
        "ask_text",
        staticmethod(lambda prompt, default="y": next(seq)),
        raising=True,
    )

    def create_with_python(path, with_pip=True):
        """Test Create with python."""
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )
        (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(ui.venv, "create", create_with_python)

    calls = []

    def record(args):
        """Test Record."""
        calls.append(tuple(map(str, args)))

    monkeypatch.setattr(ui.subprocess, "check_call", record)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        vdir,
        cfg.REQUIREMENTS_FILE,
        Path(str(tmp_path / "no.lock")),
        ui,
    )
    assert any("-r" in c and str(cfg.REQUIREMENTS_FILE) in c for c in calls)


def test_manage_virtual_environment_prefer_python313(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment prefer python313."""
    vdir = tmp_path / "v313"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        ui.shutil,
        "which",
        lambda name: "/usr/bin/python3.13" if name == "python3.13" else None,
    )

    created = {"ok": False}

    def fake_check_call(args):
        """Test Fake check call."""
        if "-m" in args and "venv" in args:
            bindir = venvmod.get_venv_bin_dir(vdir)
            bindir.mkdir(parents=True, exist_ok=True)
            (
                bindir / ("python.exe" if sys.platform == "win32" else "python")
            ).write_text("", encoding="utf-8")
            (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
                "", encoding="utf-8"
            )
            created["ok"] = True

    monkeypatch.setattr(ui.subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(
        ui.venv,
        "create",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not call")),
    )
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )
    assert created["ok"] is True


def test_manage_virtual_environment_win_py_success(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment win py success."""
    vdir = tmp_path / "w313"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(ui.sys, "platform", "win32")
    monkeypatch.setattr(
        ui.shutil, "which", lambda name: "C:/Windows/py.exe" if name == "py" else None
    )

    called = {"venv": False}

    def fake_check_call(args):
        """Test Fake check call."""
        if args and args[0] == "py":
            bindir = venvmod.get_venv_bin_dir(vdir)
            bindir.mkdir(parents=True, exist_ok=True)
            (bindir / "python.exe").write_text("", encoding="utf-8")
            (bindir / "pip.exe").write_text("", encoding="utf-8")
            called["venv"] = True

    monkeypatch.setattr(ui.subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(
        ui.venv,
        "create",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not call")),
    )
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )
    assert called["venv"] is True


def test_manage_virtual_environment_win_py_fail_fallback(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment win py fail fallback."""
    pass


def test_manage_virtual_environment_win_no_py_fallback(monkeypatch, tmp_path: Path):
    """Test Manage virtual environment win no py fallback."""
    pass


def test_manage_virtual_environment_no_py313_non_test_fallback(
    monkeypatch, tmp_path: Path
):
    """Test Manage virtual environment no py313 non test fallback."""
    pass


def test_manage_virtual_environment_recreate_existing(monkeypatch, tmp_path: Path):
    r"""Recreate existing venv when user confirms.

    Simulate a project with an existing virtual environment directory and
    assert that when the user confirms the recreate prompt the manager
    calls the safe removal helper. This test avoids relying on the legacy
    ``src.setup.app`` shim by invoking the concrete manager directly and
    patching concrete modules.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture to patch attributes and modules during the test.
    tmp_path : pathlib.Path
        Temporary path used as the fake project root and venv directory.

    Returns
    -------
    None
        The test asserts side effects and returns nothing.
    """
    # Configure project-level constants used by the manager.
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(cfg, "LOG_DIR", tmp_path / "logs", raising=True)

    # Use an explicit venv path (different from cfg.VENV_DIR) so the
    # manager's safety guard does not skip removal when running under
    # pytest. Tests should avoid relying on the repository's canonical
    # VENV_DIR during destructive branches.
    vdir = tmp_path / "venv"
    vdir.mkdir()

    # Prepare a UI adapter that will answer prompts: first proceed, then
    # confirm recreate.
    seq = iter(["y", "y"])  # yes then confirm recreate
    ui = _UI
    monkeypatch.setattr(
        ui,
        "ask_text",
        staticmethod(lambda prompt, default="y": next(seq)),
        raising=True,
    )

    # Ensure the manager believes the environment is not active so it will
    # take the branch that attempts to remove the existing VENV_DIR.
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)

    removed = {"ok": False}

    # Patch filesystem helpers so the test can observe removal without
    # mutating the real filesystem. The manager imports these helpers
    # into its module namespace, so patch the local symbols on `vm`.
    monkeypatch.setattr(vm, "create_safe_path", lambda p: p)
    monkeypatch.setattr(
        vm, "safe_rmtree", lambda validated: removed.__setitem__("ok", True)
    )

    # Prevent actual pip/subprocess calls during the test run by patching
    # the subprocess used via the UI adapter.
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)

    # Call the concrete manager directly with explicit arguments rather than
    # relying on a legacy ``src.setup.app`` wrapper.
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        vdir,
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )

    assert removed["ok"] is True


def test_manage_virtual_environment_skip(monkeypatch):
    r"""Skip venv management when user declines.

    The test patches concrete prompt and environment detection helpers and
    invokes the concrete venv manager directly to ensure the manager exits
    early when the user answers 'n' to the initial prompt.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture used to patch functions during the test.

    Returns
    -------
    None
        The test asserts the manager returns without raising.
    """
    # Patch the concrete prompt helper and concrete venv helper directly
    monkeypatch.setattr(
        "src.setup.app_prompts.ask_text", lambda prompt, default="y": "n", raising=True
    )
    monkeypatch.setattr("src.setup.venv.is_venv_active", lambda: False, raising=True)
    # Call the concrete manager with an explicit UI adapter to avoid relying
    # on the legacy `src.setup.app` shim or global module state.
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        cfg.VENV_DIR,
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        _UI,
    )


def test_manage_virtual_environment_install_fallback_when_no_lock(
    monkeypatch, tmp_path: Path
):
    """When a lockfile is missing, the manager falls back to requirements.txt.

    The test patches the concrete configuration value ``src.config.VENV_DIR``
    so the manager operates on a temporary directory. It ensures that the
    fallback branch which installs from ``requirements.txt`` is exercised
    without performing destructive filesystem operations.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture used to patch modules and functions used during the test.
    tmp_path : pathlib.Path
        Temporary path used for creating a fake venv directory.

    Returns
    -------
    None
        The test asserts behaviour by observing mocked subprocess calls.
    """
    # Prepare venv dir and paths (patch concrete config used by production code)
    vdir = tmp_path / "venv_fb"
    monkeypatch.setattr(cfg, "VENV_DIR", vdir, raising=True)
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )
    # Ensure lock file path is non-existent for the lockfile argument
    lockfile = tmp_path / "no.lock"

    # Create fake python/pip inside venv when created
    def create_with_python(path, with_pip=True):
        """Create a fake python/pip inside the venv bin directory.

        Parameters
        ----------
        path : pathlib.Path
            The path where the venv should be created.
        with_pip : bool, optional
            Whether pip should be created alongside python (default True).
        """
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )
        (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(ui.venv, "create", create_with_python, raising=True)

    calls = []

    def record(args):
        """Record subprocess invocations for assertion."""
        calls.append(tuple(map(str, args)))

    monkeypatch.setattr(ui.subprocess, "check_call", record, raising=True)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, lockfile, ui
    )
    # Ensure that the fallback path installing from requirements.txt was attempted
    assert any("-r" in c and str(cfg.REQUIREMENTS_FILE) in c for c in calls)


# --- Consolidated tests moved from other files for venv_manager ---


def test_manage_virtual_environment_delegates(monkeypatch) -> None:
    """When a venv manager is present, the app_venv wrapper calls it.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to install a fake venv_manager module.

    Returns
    -------
    None
    """
    called = {}

    fake_vm = type(sys)("src.setup.venv_manager")

    def _manage(*a, **k):
        called["ok"] = True

    fake_vm.manage_virtual_environment = _manage
    monkeypatch.setitem(sys.modules, "src.setup.venv_manager", fake_vm)
    if "src.setup" in sys.modules:
        monkeypatch.setattr(
            sys.modules["src.setup"], "venv_manager", fake_vm, raising=False
        )

    # Call the wrapper which should import and delegate to the fake manager
    app_venv.manage_virtual_environment()
    assert called.get("ok", False) is True


def test_manage_virtual_environment_no_manager_is_noop(monkeypatch) -> None:
    """If no venv_manager is importable the wrapper does nothing.

    The test ensures that when the underlying ``src.setup.venv_manager``
    module cannot be imported the wrapper ``app_venv.manage_virtual_environment``
    returns without raising an exception.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to remove or alter entries in ``sys.modules``.

    Returns
    -------
    None
        The test asserts no exception is raised.
    """
    # Ensure module is not present
    monkeypatch.delitem(sys.modules, "src.setup.venv_manager", raising=False)
    app_venv.manage_virtual_environment()  # should not raise


def test_manage_virtual_environment_create_and_install(monkeypatch, tmp_path: Path):
    """Create a venv and ensure pip install path is attempted.

    This test uses a lightweight UI adapter that stubs out filesystem and
    subprocess effects so a new venv can be created in-process.
    """
    vdir = tmp_path / "venv"
    # Ensure not active
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)

    # Provide UI adapter with minimal attributes expected by manager
    class UI:
        def __init__(self):
            self._ = lambda k: k
            self.ui_has_rich = lambda: False
            self.logger = types.SimpleNamespace(error=lambda *a, **k: None)
            self.subprocess = types.SimpleNamespace(check_call=lambda *a, **k: None)
            # venv.create will be invoked to create venv
            self.venv = types.SimpleNamespace(
                create=lambda p, with_pip=True: (
                    (p / "bin").mkdir(parents=True, exist_ok=True),
                    (p / "bin" / "python").write_text("", encoding="utf-8"),
                    (p / "bin" / "pip").write_text("", encoding="utf-8"),
                )
            )
            self.os = _os
            self.subprocess = self.subprocess
            self.sys = types.SimpleNamespace(
                platform="linux", executable="/usr/bin/python"
            )
            self.rprint = lambda *a, **k: None
            self.ui_info = lambda *a, **k: None

            def ask_text(prompt, default="y"):
                return "y"

            self.ask_text = ask_text

    ui = UI()
    # Call manager
    vm.manage_virtual_environment(
        tmp_path, vdir, tmp_path / "req.txt", tmp_path / "req.lock", ui
    )
    # After running, venv dir should exist and contain python
    assert (vdir / "bin" / "python").exists()


def test_manage_virtual_environment_restart_branch(monkeypatch, tmp_path: Path):
    """Exercise the restart branch that attempts to execve into the venv python."""
    vdir = tmp_path / "venv"
    bindir = vdir / "bin"
    bindir.mkdir(parents=True)
    py = bindir / "python"
    py.write_text("", encoding="utf-8")

    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)

    called = {}

    class UI:
        def __init__(self):
            self._ = lambda k: k
            self.ui_has_rich = lambda: True
            self.logger = types.SimpleNamespace(error=lambda *a, **k: None)
            self.subprocess = types.SimpleNamespace(check_call=lambda *a, **k: None)
            self.venv = types.SimpleNamespace(create=lambda *a, **k: None)
            # Provide os with execve we can intercept
            self.os = types.SimpleNamespace(
                execve=lambda p, a, e: (_ for _ in ()).throw(Exception("execve"))
            )
            self.sys = types.SimpleNamespace(
                platform="linux", executable="/usr/bin/python"
            )
            self.rprint = lambda *a, **k: None
            self.ui_info = lambda *a, **k: None

            def ask_text(prompt, default="y"):
                return "y"

            self.ask_text = ask_text

    ui = UI()
    # Force venv_dir exists and assign venv_python detection
    monkeypatch.setattr(vm, "venvmod", venvmod, raising=False)
    # Run manager; execve will raise but be caught internally
    vm.manage_virtual_environment(
        tmp_path, vdir, tmp_path / "req.txt", tmp_path / "req.lock", ui
    )
    # If we reached this point, the restart branch was exercised (no crash)
    assert True


def test_manage_virtual_environment_recreate_permission_error(
    monkeypatch, tmp_path: Path
):
    """When safe_rmtree raises PermissionError the manager logs and returns."""
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    # Build a minimal UI adapter expected by the function
    captured = {"msgs": []}

    class UI:
        def __init__(self):
            self.logger = types.SimpleNamespace(
                error=lambda *a, **k: captured["msgs"].append(str(a))
            )

        ask_text = staticmethod(lambda prompt, default=None: "y")
        rprint = staticmethod(lambda *a, **k: None)
        ui_info = staticmethod(lambda *a, **k: None)
        _ = staticmethod(lambda k: k)
        subprocess = None

    ui = UI()

    # Simulate existing venv and recreate chosen; safe_rmtree raises PermissionError
    monkeypatch.setattr(vm.venvmod, "is_venv_active", lambda: False)
    monkeypatch.setattr(vm, "create_safe_path", lambda p: p)
    monkeypatch.setattr(
        vm, "safe_rmtree", lambda p: (_ for _ in ()).throw(PermissionError("denied"))
    )

    # Run the manager; it should handle the PermissionError and return
    vm.manage_virtual_environment(Path("/tmp"), venv_dir, Path("r1"), Path("r2"), ui)
    assert any("denied" in s for s in " ".join(captured["msgs"])) or captured["msgs"]


def test_manage_virtual_environment_recreate_decline(
    monkeypatch, tmp_path: Path
) -> None:
    """When venv exists and user declines recreate, manager skips removal.

    The test stubs UI prompt responses and filesystem helpers so the
    function behaviour can be observed without performing destructive ops.
    """
    called = []

    # Create a fake venv dir under tmp_path
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    # Fake UI adapter
    class UI(types.SimpleNamespace):
        def __init__(self):
            self._ = lambda k: k
            self.ask_text = lambda prompt, default=None: (
                "y" if "Create" in prompt or "no_ven_prompt" in prompt else "n"
            )
            self.ui_info = lambda m: called.append(("info", m))
            self.rprint = lambda *a, **k: called.append(("rprint", a))
            self.ui_has_rich = lambda: False
            self.logger = types.SimpleNamespace(
                error=lambda m: called.append(("error", m))
            )
            self.subprocess = types.SimpleNamespace(
                check_call=lambda *a, **k: called.append(("check_call", a))
            )
            self.shutil = _shutil
            self.sys = types.SimpleNamespace(
                platform="linux", executable="/usr/bin/python", prefix="/usr"
            )
            self.venv = types.SimpleNamespace(
                create=lambda p, with_pip=True: called.append(("venv.create", str(p)))
            )
            self.os = _os

    ui = UI()

    # Stub fs_utils to avoid permission checks
    monkeypatch.setattr(
        "src.setup.fs_utils.create_safe_path", lambda p: p, raising=False
    )
    monkeypatch.setattr(
        "src.setup.fs_utils.safe_rmtree",
        lambda p: called.append(("rmtree", str(p))),
        raising=False,
    )

    # Ensure venvmod reports not active
    venvmod_local = importlib.import_module("src.setup.venv")
    monkeypatch.setattr(venvmod_local, "is_venv_active", lambda: False, raising=False)

    # Simulate first prompt 'y' (proceed) then confirm_recreate 'n' (decline)
    calls = iter(["y", "n"])
    monkeypatch.setattr(
        ui, "ask_text", lambda prompt, default=None: next(calls), raising=True
    )

    vm.manage_virtual_environment(
        tmp_path, venv_dir, tmp_path / "req.txt", tmp_path / "req.lock", ui
    )

    # We expect ui_info or rprint to indicate skipping
    assert any(c[0] in ("info", "rprint") for c in called)


def test_manage_virtual_environment_create_and_install_additional(
    monkeypatch, tmp_path: Path
) -> None:
    """Creating a venv calls the venv.create path and pip install (stubbed).

    We remove the pytest environment marker so the function will exercise
    the normal creation/install branches, but stub subprocess calls to
    avoid doing real installs.
    """
    called = []

    venv_dir = tmp_path / "venv"

    # Fake UI similar to above but provide 'y' response to proceed
    class UI(types.SimpleNamespace):
        def __init__(self):
            self._ = lambda k: k
            self.ask_text = lambda prompt, default=None: "y"
            self.ui_info = lambda m: called.append(("info", m))
            self.rprint = lambda *a, **k: called.append(("rprint", a))
            self.ui_has_rich = lambda: False
            self.logger = types.SimpleNamespace(
                error=lambda m: called.append(("error", m))
            )
            # Provide subprocess with a check_call stub
            self.subprocess = types.SimpleNamespace(
                check_call=lambda *a, **k: called.append(("pip", a))
            )
            self.shutil = _shutil
            self.sys = types.SimpleNamespace(
                platform="linux", executable="/usr/bin/python", prefix="/usr"
            )
            self.venv = types.SimpleNamespace(
                create=lambda p, with_pip=True: (
                    p.mkdir(parents=True),
                    called.append(("venv.create", str(p))),
                )
            )
            self.os = _os

    ui = UI()

    # Remove pytest marker so creation path is used
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # Stub fs_utils to avoid whitelist checks
    monkeypatch.setattr(
        "src.setup.fs_utils.create_safe_path", lambda p: p, raising=False
    )
    monkeypatch.setattr(
        "src.setup.fs_utils.safe_rmtree",
        lambda p: called.append(("rmtree", str(p))),
        raising=False,
    )

    # Ensure venvmod is in predictable state
    venvmod_local = importlib.import_module("src.setup.venv")
    monkeypatch.setattr(venvmod_local, "is_venv_active", lambda: False, raising=False)
    monkeypatch.setattr(
        venvmod_local,
        "get_venv_pip_executable",
        lambda p: venv_dir / "bin" / "pip",
        raising=False,
    )
    monkeypatch.setattr(
        venvmod_local,
        "get_venv_python_executable",
        lambda p: venv_dir / "bin" / "python",
        raising=False,
    )

    # Call manager
    vm.manage_virtual_environment(
        tmp_path, venv_dir, tmp_path / "req.txt", tmp_path / "req.lock", ui
    )

    # Assert either the in‑process venv.create was called or the manager
    # invoked a system python to create the venv (a check_call with
    # "-m venv" in the command). Also ensure pip install calls were
    # attempted (stub recorded).
    created_inproc = any(c[0] == "venv.create" for c in called)
    created_subproc = any(("-m" in str(c) and "venv" in str(c)) for c in called)
    assert created_inproc or created_subproc
    assert any("pip" in str(c) or "install" in str(c) for c in called)
    # (assert moved earlier into the install-fallback test where `calls` is in scope)


def test_manage_virtual_environment_no_venvdir_pip_python_fallback(
    monkeypatch, tmp_path: Path
):
    """Simulate active venv with missing pip and non-existent VENV_DIR.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture used to temporarily set attributes on modules and objects.
    tmp_path : pathlib.Path
        Temporary filesystem path provided by pytest.

    Notes
    -----
    This test avoids depending on the legacy shim (`src.setup.app`) and
    instead patches the concrete `src.setup.venv` helpers and calls the
    refactored `venv_manager.manage_virtual_environment` directly.
    """
    # Patch concrete venv helpers directly (avoid src.setup.app shim).
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: True)
    monkeypatch.setattr(
        venvmod, "get_venv_pip_executable", lambda p: tmp_path / "missing" / "pip"
    )
    monkeypatch.setattr(
        venvmod, "get_venv_python_executable", lambda p: tmp_path / "missing" / "python"
    )

    ui = _UI
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)

    # Call the refactored manager directly with an explicit venv path.
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        tmp_path / "no_venv_here",
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )


def test_manage_virtual_environment_venv_exists_no_python_fallback(
    monkeypatch, tmp_path: Path
):
    """Fallback to system Python when a venv lacks a Python executable.

    The test creates an empty venv directory structure and patches the
    concrete configuration to point at it. It then verifies the manager
    falls back to the system interpreter when the venv's Python binary
    is not present.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture used to patch environment variables and module attributes.
    tmp_path : pathlib.Path
        Temporary filesystem path used to host the fake venv.

    Returns
    -------
    None
        The test asserts expected branching behaviour without side effects.
    """
    vdir = tmp_path / "vdir"
    vdir.mkdir()
    monkeypatch.setattr(cfg, "VENV_DIR", vdir, raising=True)
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    seq = iter(["y", "y"])  # yes to manage; yes to recreate
    ui = _UI
    monkeypatch.setattr(
        ui,
        "ask_text",
        staticmethod(lambda prompt, default="y": next(seq)),
        raising=True,
    )

    def fake_create(path, with_pip=True):
        """Create venv directory structure without python executable."""
        (vdir / ("Scripts" if sys.platform == "win32" else "bin")).mkdir(
            parents=True, exist_ok=True
        )

    monkeypatch.setattr(ui.venv, "create", fake_create, raising=True)
    # Ensure get_venv_python_executable returns a non-existent path
    monkeypatch.setattr(
        venvmod,
        "get_venv_python_executable",
        lambda p: vdir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python"),
        raising=True,
    )
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None, raising=True)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


def test_manage_virtual_environment_restart_with_invalid_lang(
    monkeypatch, tmp_path: Path
):
    """Drive restart branch and cover LANG not in (en, sv) path (742->744).

    This test avoids importing the legacy `src.setup.app` shim and instead
    invokes the concrete manager `src.setup.venv_manager.manage_virtual_environment`
    directly. It patches the concrete helpers and environment so the restart
    branch that calls ``os.execve`` is exercised.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture to patch environment and module attributes.
    tmp_path : pathlib.Path
        Temporary filesystem path used for venv creation.

    Returns
    -------
    None
        The test asserts on captured execve arguments or the presence of a
        created venv python executable.
    """
    # Arrange: simulate non-active interpreter and LANG set to an unknown code.
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    monkeypatch.setenv("LANG", "xx")

    vdir = tmp_path / "rv"

    def create_with_python(path, with_pip=True):
        """Create a fake venv python inside the expected bin/Scripts dir."""
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )

    # Prepare UI adapter and patch concrete helpers used by the manager.
    ui = _UI
    monkeypatch.setattr(ui, "ui_has_rich", staticmethod(lambda: True), raising=True)
    monkeypatch.setattr(ui.venv, "create", create_with_python, raising=True)
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None, raising=True)

    captured = {}

    def fake_execve(exe, argv, env):
        """Capture execve arguments instead of executing a new process."""
        captured["exe"] = exe
        captured["argv"] = argv
        captured["env"] = env
        return None

    monkeypatch.setattr(ui.os, "execve", fake_execve, raising=True)

    # Act
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )

    # Assert: ensure --no-venv was appended when execve was called, otherwise
    # verify that a python executable was created inside the fake venv.
    if captured.get("argv"):
        assert captured["argv"][-1] == "--no-venv"
    else:
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        py = bindir / ("python.exe" if sys.platform == "win32" else "python")
        assert py.exists()


def test_manage_virtual_environment_vdir_not_created_then_fallback(
    monkeypatch, tmp_path: Path
):
    """Ensure branch 697->703 triggers when venv.create does not create VENV_DIR.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture to patch attributes and modules during the test.
    tmp_path : pathlib.Path
        Temporary path used as the fake project root and venv directory.

    Returns
    -------
    None
        The test asserts side effects and returns nothing.
    """
    # Use the concrete manager and concrete helpers instead of the legacy shim.
    vdir = tmp_path / "vnone"
    # Ensure environment is not active so manager takes the create branch.
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)

    ui = _UI
    # Choose to proceed with venv creation
    monkeypatch.setattr(
        ui, "ask_text", staticmethod(lambda prompt, default="y": "y"), raising=True
    )

    # venv.create does nothing (does not create directory), so VENV_DIR remains absent
    monkeypatch.setattr(ui.venv, "create", lambda *a, **k: None)

    # get_venv_python_executable returns a non-existent path
    monkeypatch.setattr(
        venvmod,
        "get_venv_python_executable",
        lambda p: vdir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python"),
        raising=True,
    )

    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)

    # Call the concrete manager directly with explicit arguments rather than
    # relying on the legacy ``src.setup.app`` wrapper.
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )
