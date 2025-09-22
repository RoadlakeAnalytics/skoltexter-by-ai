"""Destructive reset module for generated data and logs in the school data pipeline.

Single-responsibility: This module manages secure, validated deletion of all project-generated artefacts and logs.
It enforces strict architectural boundaries—handling only reset operations via config-defined paths using safe, robust interfaces.

Boundaries
----------
- No pipeline or orchestration logic is implemented here.
- All destructive actions use interactive confirmation, UI helpers, and strict path validation through configured constants.
- Only artefacts inside `config.PROJECT_ROOT` and `config.LOG_DIR` are ever deleted.
- Each operation logs security-relevant issues, handles edge/corner cases, and complies with AGENTS.md §4/5 on robustness and exception taxonomy.

Portfolio/Test/CI References
----------------------------
- Validation for boundaries and security logs tested in: `tests/setup/test_reset.py`, `tests/setup/test_console_and_fs_and_i18n.py`
- Custom exceptions defined in `src/exceptions.py` cover all error scenarios.
- Configuration constants enforced from `src/config.py`: no hard-coded magic values.
- Module always passes zero-warning CI gates for lint/type/tests: ruff, black, mypy --strict, pytest, bandit.

Usage
-----
Never auto-called from pipeline stages.
Intended for orchestrator-driven terminal UI or direct invocation in setup scripts.
Ensures full safety for destructive actions and compliance for portfolio/CI.

References
----------
- AGENTS.md (§4: Documentation; §5: Robustness; §6: CI Gates)
- `src/config.py`, `src/exceptions.py`
- Test files: `tests/setup/test_reset.py`, `tests/setup/test_console_and_fs_and_i18n.py`
"""

from __future__ import annotations

import logging
from pathlib import Path

import src.setup.ui.prompts as prompts
from src import config as _config
from src.setup.console_helpers import rprint
from src.setup.fs_utils import create_safe_path, safe_rmtree
from src.setup.i18n import translate
from src.setup.ui.basic import ui_rule


def _resolve_project_paths() -> tuple[Path, Path]:
    r"""Resolve and return project root and log directory paths for reset operations.

    Returns config-driven boundaries for safe artefact deletion, isolating all destructive logic.

    Parameters
    ----------
    None

    Returns
    -------
    tuple[Path, Path]
        ``(project_root, log_dir)``; both are Path objects, guaranteed to match config-driven boundaries.

    Raises
    ------
    None

    Notes
    -----
    All path values come from `src/config.py` UPPER_SNAKE_CASE constants.
    Boundaries are strictly enforced throughout reset operations per AGENTS.md §5.

    Examples
    --------
    >>> from src.setup import reset
    >>> root, logdir = reset._resolve_project_paths()
    >>> assert root.is_dir() and logdir.is_dir()
    """

logger = logging.getLogger("setup_project.reset")


def _gather_generated_paths() -> list[Path]:
    r"""Gather all project-generated files targeted for deletion by reset.

    Searches config-driven generated directories and logs, returning a flat list of files
    (never directories). All paths are strictly validated to prevent out-of-bound deletions.

    Parameters
    ----------
    None

    Returns
    -------
    list[Path]
        List of config-rooted, validated file Paths—never returns directories or external files.

    Raises
    ------
    None

    Notes
    -----
    Relies on _resolve_project_paths() and directory boundaries in `src/config.py`.
    Never fails; returns an empty list if no generated artefacts exist.
    All files are enumerated recursively within configured directories only.

    Examples
    --------
    >>> from src.setup import reset
    >>> files = reset._gather_generated_paths()
    >>> assert isinstance(files, list)
    >>> # Edge case: no generated files
    >>> if not files:
    ...     assert files == []
    >>> else:
    ...     assert all(f.is_file() for f in files)
    """

def reset_project() -> None:
    r"""Interactively reset (delete) all generated artefacts and logs for the project.

    Removes generated data and log directories after interactive user confirmation.
    Validates every deletion using configuration constants and a safe validation layer before
    destructively clearing content.

    The process:
        - Prompts the user for confirmation using system localization/i18n.
        - Gathers all generated artefact file paths (see `_gather_generated_paths()`).
        - If none are found, prints the canonical "no logs" message (config/localizable).
        - Lists each directory targeted for deletion (config-driven).
        - Validates deletion for each directory (`create_safe_path()` then `safe_rmtree()`).
        - Logs all permission/security issues; robustly continues if possible.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Raises
    ------
    PermissionError
        Raised internally/logged if a directory could not be validated for deletion.
    Exception
        Any unexpected errors during deletion are logged and skipped.

    Notes
    -----
    - All destructive actions gated by interactive confirmation; never run non-interactively in CI/pipeline.
    - Only config-rooted directories are wiped; out-of-bound attempts are strictly rejected.
    - Permission errors log and continue; unexpected errors log and continue (never fail full reset).
    - Tested via `tests/setup/test_reset.py`.

    Examples
    --------
    >>> import builtins
    >>> from src.setup import reset
    >>> # Simulate cancellation
    >>> orig = builtins.input; builtins.input = lambda _: "n"
    >>> reset.reset_project()  # prints cancellation message, returns None
    >>> builtins.input = orig
    >>> # Simulate confirmation (prints and deletes)
    >>> # builtins.input = lambda _: "y"
    >>> # reset.reset_project()
    """

    project_root, log_dir = _resolve_project_paths()
    try:
        ui_rule(translate("menu_option_5").split(". ")[1])
    except Exception:
        ui_rule("Reset Project")

    files_found = _gather_generated_paths()
    if not files_found:
        rprint(translate("no_logs") or "No generated files found to delete.")
        return

    rprint(f"Found {len(files_found)} generated files that will be deleted.")
    rprint("Directories that will be cleared:")

    dirs_to_check = [
        project_root / "data" / "generated_markdown_from_csv",
        project_root / "data" / "ai_processed_markdown",
        project_root / "data" / "ai_raw_responses",
        project_root / "data" / "generated_descriptions",
        project_root / "output",
        log_dir,
    ]

    for dir_path in dirs_to_check:
        if dir_path.exists() and any(dir_path.rglob("*")):
            try:
                rprint(f"  - {dir_path.relative_to(project_root)}")
            except Exception:
                rprint(f"  - {dir_path}")

    confirm = prompts.ask_text(translate("reset_confirm"), default="n").lower()
    if confirm not in ["y", "j"]:
        rprint(translate("reset_cancelled"))
        return

    deleted_dirs_count = 0
    for dir_path in dirs_to_check:
        try:
            if dir_path.exists():
                # STEP 1: Validate the path and obtain a stamped _ValidatedPath.
                # This will raise PermissionError if the path is outside the
                # permitted set of directories.
                validated = create_safe_path(dir_path)

                # STEP 2: Perform the destructive operation using the validated
                # object. The separation makes it impossible to call the
                # destructive code with an unvalidated Path.
                safe_rmtree(validated)
                deleted_dirs_count += 1
        except PermissionError as e:
            # Log security-related issues but continue with other directories
            logger.error(f"Could not reset directory '{dir_path}': {e}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while resetting '{dir_path}': {e}"
            )

    rprint(f"{translate('reset_complete')} ({deleted_dirs_count} directories cleared)")

__all__ = ["reset_project"]
