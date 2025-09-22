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
    from src.setup.app_runner import run as app_run

    # The refactored `run` takes an argparse.Namespace and performs the
    # interactive flow (or non-interactive if ``--no-venv`` is provided).
    app_run(args)


if __name__ == "__main__":
    entry_point()
