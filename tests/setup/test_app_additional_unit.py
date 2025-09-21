"""Additional unit tests for :mod:`src.setup.app`.

These tests exercise several thin wrapper helpers such as CLI parsing,
virtualenv path helpers and the subprocess runner. They are written to be
deterministic and avoid spawning real subprocesses by monkeypatching the
relevant functions.
"""

import argparse
import os
import subprocess
from pathlib import Path

import types
from types import ModuleType

# Use a compact `app` namespace that exposes the small set of helpers
# this test file relies on from the refactored modules. We register a
# real module object in ``sys.modules['src.setup.app']`` so tests that
# rely on module semantics (reloads, monkeypatching) behave
# deterministically.
import src.setup.app_venv as _app_venv
import src.setup.app_runner as _app_runner

_app_ns = types.SimpleNamespace(
    parse_cli_args=_app_runner.parse_cli_args,
    get_venv_bin_dir=_app_venv.get_venv_bin_dir,
    get_venv_python_executable=_app_venv.get_venv_python_executable,
    get_venv_pip_executable=_app_venv.get_venv_pip_executable,
    get_python_executable=_app_venv.get_python_executable,
    run_program=_app_venv.run_program,
    # Expose a sys proxy for platform tests
    sys=__import__("sys"),
)

app = _app_ns
import sys as _sys
_sys.modules["src.setup.app"] = app


def test_parse_cli_args_defaults() -> None:
    """Parse default CLI args when no argv is provided.

    The parser should return an argparse.Namespace with expected defaults.
    """
    ns = app.parse_cli_args([])
    assert isinstance(ns, argparse.Namespace)
    assert getattr(ns, "lang") in ("en", "sv")
    assert getattr(ns, "no_venv") is False


# Venv-related tests migrated to `tests/setup/test_app_venv.py`.
# The concrete helpers are exercised there and removed from this file.
