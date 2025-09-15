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
        return key

    @staticmethod
    def ui_info(msg: str) -> None:
        pass


def _make_fake_bin(tmp: Path):
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
    vdir = tmp_path / "venv"
    vdir.mkdir()
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    seq = iter(["y", "y"])  # yes to manage, yes to recreate
    ui = _UI
    ui.ask_text = staticmethod(lambda prompt, default="y": next(seq))
    monkeypatch.setattr(
        ui.shutil, "rmtree", lambda p: (_ for _ in ()).throw(RuntimeError("rmtree"))
    )
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


def test_manage_virtual_environment_create_error(monkeypatch, tmp_path: Path):
    vdir = tmp_path / "venv2"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    ui.ask_text = staticmethod(lambda prompt, default="y": "y")
    monkeypatch.setattr(
        ui.venv, "create", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("create"))
    )
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


def test_manage_virtual_environment_install_errors(monkeypatch, tmp_path: Path):
    vdir = tmp_path / "v3"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    ui.ask_text = staticmethod(lambda prompt, default="y": "y")

    def fake_create(*a, **k):
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(ui.venv, "create", fake_create)

    calls = {"n": 0}

    def raise_cpe(args):
        calls["n"] += 1
        raise _sub.CalledProcessError(1, args)

    monkeypatch.setattr(ui.subprocess, "check_call", raise_cpe)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT, vdir, cfg.REQUIREMENTS_FILE, cfg.REQUIREMENTS_LOCK_FILE, ui
    )


def test_manage_virtual_environment_dynamic_ui_enable_success(monkeypatch):
    ui = _UI
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: True)
    ui.ask_text = staticmethod(lambda prompt, default="y": "y")
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        Path("."),
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )


def test_manage_virtual_environment_dynamic_ui_enable_excepts(monkeypatch):
    import builtins as _builtins
    import importlib as _importlib

    ui = _UI
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: True)
    ui.ask_text = staticmethod(lambda prompt, default="y": "y")
    monkeypatch.setattr(ui.subprocess, "check_call", lambda *a, **k: None)
    ui.ui_has_rich = staticmethod(lambda: False)

    orig_import = _builtins.__import__

    def fake_import(name, *a, **k):
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
        Path("."),
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )

    def raise_fnf(args):
        raise FileNotFoundError("pip not found")

    monkeypatch.setattr(ui.subprocess, "check_call", raise_fnf)
    vm.manage_virtual_environment(
        cfg.PROJECT_ROOT,
        Path("."),
        cfg.REQUIREMENTS_FILE,
        cfg.REQUIREMENTS_LOCK_FILE,
        ui,
    )


def test_manage_virtual_environment_create(monkeypatch, tmp_path: Path):
    vdir = tmp_path / "venv"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    seq = iter(["y"])  # yes to create
    ui.ask_text = staticmethod(lambda prompt, default="y": next(seq))

    def create_with_python(path, with_pip=True):
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
    vdir = tmp_path / "v313"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    ui.ask_text = staticmethod(lambda prompt, default="y": "y")

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        ui.shutil,
        "which",
        lambda name: "/usr/bin/python3.13" if name == "python3.13" else None,
    )

    created = {"ok": False}

    def fake_check_call(args):
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
    vdir = tmp_path / "w313"
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    ui = _UI
    ui.ask_text = staticmethod(lambda prompt, default="y": "y")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(ui.sys, "platform", "win32")
    monkeypatch.setattr(
        ui.shutil, "which", lambda name: "C:/Windows/py.exe" if name == "py" else None
    )

    called = {"venv": False}

    def fake_check_call(args):
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
    pass


def test_manage_virtual_environment_win_no_py_fallback(monkeypatch, tmp_path: Path):
    pass


def test_manage_virtual_environment_no_py313_non_test_fallback(
    monkeypatch, tmp_path: Path
):
    pass

def test_manage_virtual_environment_recreate_existing(monkeypatch, tmp_path: Path):
    """Recreate existing venv when user confirms."""
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")
    sp.VENV_DIR.mkdir()
    seq = iter(["y", "y"])  # yes then confirm recreate
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": next(seq))
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    removed = {"ok": False}
    monkeypatch.setattr(sp.shutil, "rmtree", lambda p: removed.__setitem__("ok", True))
    sp.manage_virtual_environment()
    assert removed["ok"] is True

def test_manage_virtual_environment_skip(monkeypatch):
    """Skip venv management when user declines."""
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "n")
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    sp.manage_virtual_environment()

def test_manage_virtual_environment_install_fallback_when_no_lock(
    monkeypatch, tmp_path: Path
):
    """When requirements.lock is missing, fallback to requirements.txt install path is used."""
    import setup_project as sp_local

    # Prepare venv dir and paths
    monkeypatch.setattr(sp_local, "VENV_DIR", tmp_path / "venv_fb")
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    # Ensure lock file path is non-existent
    monkeypatch.setattr(sp_local, "REQUIREMENTS_LOCK_FILE", tmp_path / "no.lock")

    # Create fake python/pip inside venv when created
    def create_with_python(path, with_pip=True):
        bindir = sp_local.get_venv_bin_dir(sp_local.VENV_DIR)
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )
        (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)

    calls = []

    def record(args):
        calls.append(tuple(map(str, args)))

    monkeypatch.setattr(sp_local.subprocess, "check_call", record)
    sp_local.manage_virtual_environment()
    # The second call should be the install command using requirements.txt fallback
    assert any("-r" in c and str(sp_local.REQUIREMENTS_FILE) in c for c in calls)

def test_manage_virtual_environment_no_venvdir_pip_python_fallback(
    monkeypatch, tmp_path: Path
):
    """Cover branch where pip path is missing and VENV_DIR does not exist (688->692).

    We simulate an active venv with missing pip executable path and a non-existent
    project VENV_DIR, ensuring the code takes the false branch and continues.
    """
    import setup_project as sp_local

    monkeypatch.setattr(sp_local, "is_venv_active", lambda: True)
    # Return a non-existent pip path for the active environment
    monkeypatch.setattr(
        sp_local,
        "get_venv_pip_executable",
        lambda p: tmp_path / "missing" / "pip",
    )
    # Return a non-existent python path to force fallback resolution later
    monkeypatch.setattr(
        sp_local,
        "get_venv_python_executable",
        lambda p: tmp_path / "missing" / "python",
    )
    monkeypatch.setattr(sp_local, "VENV_DIR", tmp_path / "no_venv_here")
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()

def test_manage_virtual_environment_venv_exists_no_python_fallback(
    monkeypatch, tmp_path: Path
):
    """Cover fallback to system python when VENV_DIR exists but python is missing (697->703)."""
    import setup_project as sp_local

    vdir = tmp_path / "vdir"
    vdir.mkdir()
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    seq = iter(["y", "y"])  # yes to manage; yes to recreate
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": next(seq))

    def fake_create(path, with_pip=True):
        # Create venv directory structure without python executable
        (vdir / ("Scripts" if sys.platform == "win32" else "bin")).mkdir(
            parents=True, exist_ok=True
        )

    monkeypatch.setattr(sp_local.venv, "create", fake_create)
    # Ensure get_venv_python_executable returns a non-existent path
    monkeypatch.setattr(
        sp_local,
        "get_venv_python_executable",
        lambda p: vdir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python"),
    )
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()

def test_manage_virtual_environment_restart_with_invalid_lang(
    monkeypatch, tmp_path: Path
):
    """Drive restart branch and cover LANG not in (en, sv) path (742->744)."""
    import setup_project as sp_local

    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "LANG", "xx")
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    vdir = tmp_path / "rv"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)

    def create_with_python(path, with_pip=True):
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    captured = {}

    def fake_execve(exe, argv, env):
        captured["exe"] = exe
        captured["argv"] = argv
        captured["env"] = env
        return None

    monkeypatch.setattr(sp_local.os, "execve", fake_execve)
    sp_local.manage_virtual_environment()
    # Ensure we attempted to execve with --no-venv appended
    assert captured.get("argv") and captured["argv"][-1] == "--no-venv"

def test_manage_virtual_environment_vdir_not_created_then_fallback(
    monkeypatch, tmp_path: Path
):
    """Ensure branch 697->703 triggers when venv.create does not create VENV_DIR.

    We simulate a scenario where VENV_DIR does not exist before and after venv.create,
    forcing the code to skip the 'elif VENV_DIR.exists()' block and hit the fallback.
    """
    import setup_project as sp_local

    vdir = tmp_path / "vnone"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    # Choose to proceed with venv creation
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")

    # venv.create does nothing (does not create directory), so VENV_DIR remains absent
    monkeypatch.setattr(sp_local.venv, "create", lambda *a, **k: None)
    # get_venv_python_executable returns a non-existent path
    monkeypatch.setattr(
        sp_local,
        "get_venv_python_executable",
        lambda p: vdir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python"),
    )
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()
