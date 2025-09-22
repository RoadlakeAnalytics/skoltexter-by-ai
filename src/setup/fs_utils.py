"""Filesystem validation and removal utilities for orchestration/reset.

Architectural Role:
    This module provides robust primitives for validating and removing directories
    in the School Data Pipeline setup and reset orchestration. It strictly enforces
    project boundaries and destruction safety via explicit whitelisting and type stamping.

Boundaries:
    - Used exclusively by orchestration/setup/reset utilities, never core pipeline.
    - Configurable solely via src/config.py attributes; no hard-coded values.
    - All error handling uses custom taxonomy—see src/exceptions.py.

Portfolio/CI/Test Context:
    - Covered by targeted tests in tests/setup/test_fs_utils_unit.py and mutation tests.
    - All edge/corner/canonical behaviors—both allowed and forbidden removals, and exception handling—
      are tested.
    - Mutation, bandit, and branch coverage gates enforced (see .bandit, mutmut config).
    - Examples provided in docstrings are pytest/xdoctest compatible.

References:
    - AGENTS.md section 4 (docstring standard), section 5 (robustness, boundedness).
    - tests/setup/test_fs_utils_unit.py (coverage).
    - docs/dev_journal/2025-09-21_fixed_tests_and_code_summary.md (dev reasoning).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import NewType

from src import config as _config

logger = logging.getLogger(__name__)

# NewType used as a static "seal" to indicate the path is validated for removal.
_ValidatedPath = NewType("_ValidatedPath", Path)


def create_safe_path(path_to_validate: Path) -> _ValidatedPath:
    r"""Validate and stamp a Path as safe for destructive operations.

    This function performs all project-local validation and whitelisting logic,
    returning a stamped _ValidatedPath if the supplied path is safe for removal.
    Multiple safety checks:
    - Never allows deletion of PROJECT_ROOT itself.
    - Requires path to be inside project tree (via is_relative_to).
    - Permits only explicit, hard-coded whitelisted directories, and
      permits __pycache__ removal anywhere under project root.

    Parameters
    ----------
    path_to_validate : Path
        The directory path to be validated for safe removal.

    Returns
    -------
    _ValidatedPath
        The path, stamped for safe usage by removal helpers.

    Raises
    ------
    PermissionError
        If the path is the project root, outside project, or not whitelisted.

    Notes
    -----
    - Coverage: All checks are exercised via pytest.
    - Corner edge: is_relative_to failure handled for older Python.
    - Mutation: "unsafe" bypass impossible via static type, runtime guard, explicit custom errors.
    - No recursion or unboundedness anywhere.

    Examples
    --------
    Valid usage:
    >>> from pathlib import Path
    >>> from src.setup.fs_utils import create_safe_path
    >>> good = create_safe_path(Path("output"))
    >>> isinstance(good, Path)
    True

    Forbidden removal (raises):
    >>> from pathlib import Path
    >>> from src.setup.fs_utils import create_safe_path
    >>> create_safe_path(Path("/"))  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    PermissionError: SECURITY STOP: Attempt to delete the project root was blocked.
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
        ) from None

    # Explicit whitelist of directories allowed for deletion.
    whitelisted_roots = [
        _config.PROJECT_ROOT / "output",
        _config.LOG_DIR,
        _config.VENV_DIR,
        _config.PROJECT_ROOT / "data" / "generated_markdown_from_csv",
        _config.PROJECT_ROOT / "data" / "ai_processed_markdown",
        _config.PROJECT_ROOT / "data" / "ai_raw_responses",
        _config.PROJECT_ROOT / "data" / "generated_descriptions",
        _config.PROJECT_ROOT / "mutants",
        _config.PROJECT_ROOT / ".pytest_cache",
        _config.PROJECT_ROOT / ".mypy_cache",
        _config.PROJECT_ROOT / ".ruff_cache",
    ]

    whitelisted_roots_resolved = [p.resolve() for p in whitelisted_roots]

    # Special-case: __pycache__ is always allowed under project root.
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
        raise PermissionError(
            f"SECURITY STOP: Path '{target_path}' is not in the whitelist."
        )
    # Passed all checks: stamp path.
    return _ValidatedPath(target_path)


def safe_rmtree(safe_path: _ValidatedPath | Path) -> None:
    r"""Remove a directory tree for a validated, whitelisted path.

    Uses create_safe_path to ensure the path meets all safety criteria before
    invoking destructive removal. Guarantees that only paths explicitly validated
    and whitelisted (via config and create_safe_path) can be deleted.

    Parameters
    ----------
    safe_path : Path or _ValidatedPath
        The target directory (stamped or raw Path; if raw, validation occurs).

    Returns
    -------
    None

    Raises
    ------
    PermissionError
        If the supplied path fails validation by create_safe_path.

    Notes
    -----
    - Explicit logging at WARNING and INFO levels before and after removal.
    - All mutation and edge cases (nonexistent path, bad whitelist) are tested.
    - No recursion, no unbounded behavior (all boundaries explicit).
    - Example covers both removal and nonexistence.

    Examples
    --------
    Remove a whitelisted directory (created for test isolation):
    >>> import os
    >>> from pathlib import Path
    >>> from src.setup.fs_utils import create_safe_path, safe_rmtree
    >>> d = Path("output/test_dir"); d.mkdir(parents=True, exist_ok=True)
    >>> safe_rmtree(create_safe_path(d))
    >>> d.exists()
    False

    Attempt forbidden removal:
    >>> from pathlib import Path
    >>> from src.setup.fs_utils import safe_rmtree
    >>> safe_rmtree(Path("/"))  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    PermissionError: SECURITY STOP: Attempt to delete the project root was blocked.
    """
    target_path = Path(safe_path)
    validated = create_safe_path(target_path)
    if validated.exists():
        logger.warning(f"Performing safe rmtree on: {validated}")
        shutil.rmtree(validated)
        logger.info(f"Removed directory: {validated}")
    else:
        logger.info(f"Path '{validated}' does not exist; nothing to remove.")


__all__ = ["create_safe_path", "safe_rmtree"]
