"""Minimal runner for the setup application.

This file is intentionally minimal: its single responsibility is to provide
a tiny entrypoint that delegates execution to the refactored
``src.setup.app`` module. It does not expose the legacy test/API surface.

Usage:
    python setup_project.py [--lang en|sv] [--no-venv]

"""

from __future__ import annotations

import argparse


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line args for the minimal launcher.

    Parameters
    ----------
    argv : list[str] | None
        Optional argv to parse. When ``None`` the real CLI args are used.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with fields ``lang`` and ``no_venv``.
    """
    parser = argparse.ArgumentParser(description="Setup application (minimal launcher)")
    parser.add_argument("--lang", choices=("en", "sv"), default="en")
    parser.add_argument("--no-venv", action="store_true", help="Skip venv setup")
    return parser.parse_args(argv)


def entry_point(argv: list[str] | None = None) -> None:
    """Run the setup application.

    The function imports the canonical runner from ``src.setup.app`` and
    delegates execution. Import is performed inside the function to avoid
    importing the whole application at module import time.
    """
    args = parse_cli_args(argv)
    # Lazy import the refactored application runner and delegate
    from src.setup.app import run as app_run

    # The refactored `run` takes an argparse.Namespace and performs the
    # interactive flow (or non-interactive if ``--no-venv`` is provided).
    app_run(args)


if __name__ == "__main__":
    entry_point()

# Backwards-compatible re-exports for legacy consumers and tests.
# Import inside a try/except so module remains importable even when the
# refactored application package is not available in some test contexts.
try:
    from src.setup.app import (
        get_python_executable,
        get_venv_bin_dir,
        get_venv_python_executable,
        get_venv_pip_executable,
        VENV_DIR,
        is_venv_active,
        run_program,
        manage_virtual_environment,
        ask_text,
        ask_confirm,
        ui_info,
        ui_success,
        ui_warning,
        ui_error,
        ui_menu,
    )
except Exception:
    # If the refactored module isn't importable, leave the names absent but
    # don't raise during import; tests that require the functions will fail
    # later with a clear AttributeError which is preferable to an import-time
    # crash.
    pass


def _propagate_patchable_names_to_app() -> None:
    """Propagate monkeypatched names on this module into `src.setup.app`.

    Tests historically monkeypatch attributes on the top-level
    ``setup_project`` module (for convenience). The refactor moved the
    implementation into ``src.setup.app`` which means those monkeypatches
    would not affect the behaviour used by the implementation. This helper
    copies a small set of well-known names into the implementation module
    immediately before delegation so tests can continue to patch the
    top-level module as they used to.
    """
    try:
        import importlib

        this = importlib.import_module(__name__)
        app = importlib.import_module("src.setup.app")

        # Names that are implemented as lightweight wrappers in this module
        # and must not be propagated back into the implementation (would
        # otherwise cause recursive calls).
        WRAPPER_NAMES = {
            "run_program",
            "manage_virtual_environment",
            "is_venv_active",
            "get_python_executable",
        }

        for name in (
            "ask_text",
            "ask_confirm",
            "get_venv_pip_executable",
            "get_venv_python_executable",
            "get_python_executable",
            "is_venv_active",
            "VENV_DIR",
            "subprocess",
            "venv",
        ):
            # Only propagate when the attribute was explicitly set on this
            # module and differs from the value already present on the
            # implementation module. This avoids overwriting the
            # implementation with our own local wrappers unless the test
            # intentionally patched the top-level name.
            if name in this.__dict__:
                this_val = this.__dict__[name]
                app_val = getattr(app, name, object())
                if this_val is app_val:
                    continue
                # Never propagate our own wrapper functions into the
                # implementation to avoid recursion.
                if (
                    name in WRAPPER_NAMES
                    and getattr(this_val, "__module__", None) == __name__
                ):
                    continue
                setattr(app, name, this_val)

        # Also propagate to the lower-level venv helpers module but only
        # when the top-level attribute has been patched by tests. This is
        # conservative and avoids replacing implementation functions with
        # our own wrappers.
        try:
            venvmod = importlib.import_module("src.setup.venv")
            for name in (
                "is_venv_active",
                "get_venv_python_executable",
                "get_venv_pip_executable",
                "get_python_executable",
            ):
                if name in this.__dict__:
                    this_val = this.__dict__[name]
                    venv_val = getattr(venvmod, name, object())
                    if this_val is venv_val:
                        continue
                    if (
                        name in WRAPPER_NAMES
                        and getattr(this_val, "__module__", None) == __name__
                    ):
                        continue
                    setattr(venvmod, name, this_val)
        except Exception:
            pass
    except Exception:
        # Best-effort; don't raise during import or test setup.
        pass


def run_program(program_name, program_file, stream_output: bool = False) -> bool:
    """Delegate to the refactored ``run_program`` after syncing patched names.

    This wrapper ensures that tests which monkeypatch the top-level
    ``setup_project`` module continue to influence behaviour.
    """
    _propagate_patchable_names_to_app()
    from src.setup.app import run_program as _run

    return _run(program_name, program_file, stream_output=stream_output)


def manage_virtual_environment() -> None:
    """Delegate to the refactored virtualenv manager after syncing names."""
    _propagate_patchable_names_to_app()
    from src.setup.app import manage_virtual_environment as _m

    return _m()


def is_venv_active() -> bool:
    """Delegate venv active check to the refactored module (after sync)."""
    _propagate_patchable_names_to_app()
    from src.setup.app import is_venv_active as _i

    return _i()


def get_python_executable() -> str:
    """Return the system/python executable used by the refactored runner."""
    _propagate_patchable_names_to_app()
    from src.setup.app import get_python_executable as _g

    return _g()
