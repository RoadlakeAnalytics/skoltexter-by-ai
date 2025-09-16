"""Filesystem utilities with hardened deletion helpers.

This module centralises safe deletion helpers used by the setup
and reset utilities. It provides two cooperating primitives:

- ``create_safe_path``: validate and "stamp" a Path as acceptable for
  destructive operations (returns a ``_ValidatedPath``).
- ``safe_rmtree``: perform the deletion; it accepts the stamped
  ``_ValidatedPath`` and assumes prior validation.

The intent is to make it impossible to accidentally delete paths outside
the project or delete sensitive directories such as the repository root.
Validation is intentionally strict and conservative.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import NewType

from src import config as _config

logger = logging.getLogger(__name__)


# NewType used as a static "seal" indicating the path has been validated.
# At runtime this is just a Path, but static type checkers (mypy) will
# treat it as a distinct type and prevent accidental misuse.
_ValidatedPath = NewType("_ValidatedPath", Path)


def create_safe_path(path_to_validate: Path) -> _ValidatedPath:
    """Validate a Path and return it wrapped as a ``_ValidatedPath``.

    This is the single place where a ``_ValidatedPath`` may be created.
    The function performs the following checks:

    - Resolves the provided path and the project root and disallows the
      project root itself from being removed.
    - Ensures the path is inside the repository tree.
    - Ensures the path is under a small, explicit whitelist of directories
      that are allowed to be cleared by the reset/cleanup code.

    A ``PermissionError`` is raised for any violation.
    """
    project_root = _config.PROJECT_ROOT.resolve()
    target_path = Path(path_to_validate).resolve()

    # Never allow deleting the repository root itself.
    if target_path == project_root:
        raise PermissionError(
            "SECURITY STOP: Attempt to delete the project root was blocked."
        )

    # Ensure the target is inside the project directory.
    try:
        if not target_path.is_relative_to(project_root):
            raise PermissionError(
                "SECURITY STOP: Attempt to delete a path outside the project was blocked."
            )
    except Exception:
        # is_relative_to may raise on older Python versions; treat as outside.
        raise PermissionError(
            "SECURITY STOP: Attempt to delete a path outside the project was blocked."
        )

    # Strict whitelist of directories that may be cleared by the reset logic.
    whitelisted_roots = [
        _config.PROJECT_ROOT / "output",
        _config.LOG_DIR,
        _config.VENV_DIR,
        _config.PROJECT_ROOT / "data" / "generated_markdown_from_csv",
        _config.PROJECT_ROOT / "data" / "ai_processed_markdown",
        _config.PROJECT_ROOT / "data" / "ai_raw_responses",
        _config.PROJECT_ROOT / "data" / "generated_descriptions",
        # Allow removal of common CI/test caches and mutation testing artifacts
        _config.PROJECT_ROOT / "mutants",
        _config.PROJECT_ROOT / ".pytest_cache",
        _config.PROJECT_ROOT / ".mypy_cache",
        _config.PROJECT_ROOT / ".ruff_cache",
    ]

    whitelisted_roots_resolved = [p.resolve() for p in whitelisted_roots]

    # Special-case: allow deleting __pycache__ directories anywhere under
    # the project root (they are generated artifacts and safe to remove).
    if target_path.name == "__pycache__":
        try:
            if target_path.is_relative_to(project_root):
                return _ValidatedPath(target_path)
        except Exception:
            pass

    is_safe_path = any(
        target_path == safe_root or target_path.is_relative_to(safe_root)
        for safe_root in whitelisted_roots_resolved
    )

    if not is_safe_path:
        raise PermissionError(f"SECURITY STOP: Path '{target_path}' is not in the whitelist.")

    # All checks passed — return the path stamped as validated.
    return _ValidatedPath(target_path)


def safe_rmtree(safe_path: _ValidatedPath | Path) -> None:
    """Remove a directory tree for a previously-validated path.

    The function validates the supplied path using :func:`create_safe_path`
    before performing the destructive operation. This prevents callers from
    unintentionally bypassing the validation step and ensures all removals
    are subject to the same whitelist rules.

    Parameters
    ----------
    safe_path : pathlib.Path or _ValidatedPath
        The path to remove. If a plain ``Path`` is supplied it will be
        validated prior to removal. A ``PermissionError`` is raised for
        disallowed paths.

    Raises
    ------
    PermissionError
        If the provided path is not in the allowed whitelist or is the
        project root.
    """
    target_path = Path(safe_path)

    # Validate the path using the central helper. This makes the operation
    # safe even if callers forget to explicitly call ``create_safe_path``.
    validated = create_safe_path(target_path)

    if validated.exists():
        logger.warning(f"Performing safe rmtree on: {validated}")
        shutil.rmtree(validated)
        logger.info(f"Removed directory: {validated}")
    else:
        logger.info(f"Path '{validated}' does not exist; nothing to remove.")


__all__ = ["create_safe_path", "safe_rmtree"]
