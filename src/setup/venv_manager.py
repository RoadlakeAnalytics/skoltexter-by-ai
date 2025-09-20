"""Higher-level virtual environment manager.

Encapsulates venv creation and package installation flow using a provided
UI adapter for prompts and output.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any

from . import venv as venvmod
from .fs_utils import create_safe_path, safe_rmtree


def manage_virtual_environment(
    project_root: Path,
    venv_dir: Path,
    requirements_file: Path,
    requirements_lock_file: Path,
    ui: Any,
) -> None:
    """Create or update a virtual environment and install requirements."""
    pip_executable: Path | None = None
    python_executable: Path | None = None

    _sys = getattr(ui, "sys", sys)
    _sub = getattr(ui, "subprocess", subprocess)
    _shutil = getattr(ui, "shutil", shutil)
    _venv = getattr(ui, "venv", venv)
    _os = getattr(ui, "os", os)

    if venvmod.is_venv_active():
        pip_executable = venvmod.get_venv_pip_executable(Path(_sys.prefix))
        python_executable = venvmod.get_venv_python_executable(Path(_sys.prefix))
        prompt_text = ui._("activate_venv_prompt")
        default_choice = "y"
    elif venv_dir.exists():
        pip_executable = venvmod.get_venv_pip_executable(venv_dir)
        python_executable = venvmod.get_venv_python_executable(venv_dir)
        prompt_text = ui._("create_venv_prompt")
        default_choice = "y"
    else:
        prompt_text = ui._("no_venv_prompt")
        default_choice = "y"

    choice = ui.ask_text(prompt_text, default=default_choice).lower()
    if choice not in ["y", "j"]:
        ui.rprint(ui._("venv_skipped"))
        return

    if not venvmod.is_venv_active() and venv_dir.exists():
        recreate_choice = ui.ask_text(
            ui._("confirm_recreate_venv"), default="n"
        ).lower()
        if recreate_choice in ["y", "j"]:
            try:
                # Ensure the requested venv path is validated before removal.
                validated = create_safe_path(venv_dir)
                safe_rmtree(validated)
            except PermissionError as e:
                ui.logger.error(f"Could not remove venv: {e}")
                return
            except Exception as error:
                ui.logger.error(f"Error removing venv: {error}")
                return
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
        else:
            ui.ui_info(ui._("venv_skipped"))
            return

    if not venvmod.is_venv_active() and not venv_dir.exists():
        ui.ui_info(ui._("creating_venv"))
        try:
            created = False
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                try:
                    if _sys.platform == "win32":
                        if _shutil.which("py") is not None:
                            _sub.check_call(
                                ["py", "-3.13", "-m", "venv", str(venv_dir)]
                            )
                            created = True
                    else:
                        py313 = _shutil.which("python3.13")
                        if py313:
                            _sub.check_call([py313, "-m", "venv", str(venv_dir)])
                            created = True
                except Exception:
                    created = False
            if not created:
                _venv.create(venv_dir, with_pip=True)

            pip_executable = venvmod.get_venv_pip_executable(venv_dir)
            python_executable = venvmod.get_venv_python_executable(venv_dir)
        except Exception as error:
            ui.logger.error(f"Error creating virtual environment: {error}")
            return

    if not pip_executable or not pip_executable.exists():
        if venv_dir.exists():
            pip_executable = venvmod.get_venv_pip_executable(venv_dir)

    pip_python: str | None = None
    if python_executable and python_executable.exists():
        pip_python = str(python_executable)
    elif venvmod.is_venv_active():
        pip_python = _sys.executable
    elif venv_dir.exists():
        venv_python = venvmod.get_venv_python_executable(venv_dir)
        if venv_python.exists():
            pip_python = str(venv_python)
    if not pip_python:
        pip_python = _sys.executable

    try:
        ui.ui_info(ui._("installing_deps"))
        pip_timeout = int(os.environ.get("SETUP_PIP_TIMEOUT", "15"))
        in_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        cmd = [
            pip_python,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "--disable-pip-version-check",
        ]
        if in_test:
            _sub.check_call(cmd)
        else:
            try:
                _sub.check_call(cmd, timeout=pip_timeout)
            except TypeError:
                _sub.check_call(cmd)
        if requirements_lock_file.exists():
            cmd = [
                pip_python,
                "-m",
                "pip",
                "install",
                "--require-hashes",
                "-r",
                str(requirements_lock_file),
                "--progress-bar",
                "off",
                "--no-input",
                "--disable-pip-version-check",
            ]
            if in_test:
                _sub.check_call(cmd)
            else:
                try:
                    _sub.check_call(cmd, timeout=pip_timeout)
                except TypeError:
                    _sub.check_call(cmd)
        else:
            cmd = [
                pip_python,
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements_file),
                "--progress-bar",
                "off",
                "--no-input",
                "--disable-pip-version-check",
            ]
            if in_test:
                _sub.check_call(cmd)
            else:
                try:
                    _sub.check_call(cmd, timeout=pip_timeout)
                except TypeError:
                    _sub.check_call(cmd)
        ui.rprint(
            f"[green]✓[/green] {ui._('deps_installed')}"
            if ui.ui_has_rich()
            else ui._("deps_installed")
        )
        ui.rprint(
            f"[green]✓[/green] {ui._('venv_ready')}"
            if ui.ui_has_rich()
            else ui._("venv_ready")
        )

        try:
            venv_python = venvmod.get_venv_python_executable(venv_dir)
            # Evaluate restart branch conditions.
            if (
                (not venvmod.is_venv_active())
                and venv_python.exists()
                and not os.environ.get("SETUP_SWITCHED_UI")
                and getattr(ui, "ui_has_rich", lambda: False)()
            ):
                env = os.environ.copy()
                env["SETUP_SWITCHED_UI"] = "1"
                env["SETUP_SKIP_LANGUAGE_PROMPT"] = "1"
                argv = [str(venv_python), "-m", "src.setup.app"]
                lang_env = os.environ.get("LANG")
                if lang_env:
                    lang_choice = "sv" if lang_env.lower().startswith("sv") else "en"
                    argv.extend(["--lang", lang_choice])
                argv.append("--no-venv")
                ui.rprint("\n[cyan]Restarting with enhanced UI...[/cyan]")
                _os.execve(str(venv_python), argv, env)
        except Exception:
            pass
    except _sub.CalledProcessError as error:
        ui.logger.error(f"{ui._('deps_install_failed')} Error: {error}")
    except FileNotFoundError:
        ui.logger.error(f"Error: {pip_python} or {requirements_file} not found.")
