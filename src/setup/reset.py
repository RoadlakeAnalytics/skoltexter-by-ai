"""Reset helpers: delete generated output and logs.

Shim-free reset logic using UI helpers and configuration constants.
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
    """Resolve and return key project paths used by reset helpers.

    Returns
    -------
    tuple[Path, Path]
        ``(project_root, log_dir)`` where both are Path objects extracted
        from the project configuration.
    """
    project_root = _config.PROJECT_ROOT
    log_dir = _config.LOG_DIR
    return project_root, log_dir


logger = logging.getLogger("setup_project.reset")


def _gather_generated_paths() -> list[Path]:
    """Gather all generated files that would be deleted by a reset.

    This helper searches configured generated-data directories and returns
    a flat list of files (not directories) that exist.

    Returns
    -------
    list[Path]
        List of file Paths that are considered generated artefacts.
    """
    project_root, log_dir = _resolve_project_paths()
    dirs_to_check = [
        project_root / "data" / "generated_markdown_from_csv",
        project_root / "data" / "ai_processed_markdown",
        project_root / "data" / "ai_raw_responses",
        project_root / "data" / "generated_descriptions",
        project_root / "output",
        log_dir,
    ]
    files_found: list[Path] = []
    for dir_path in dirs_to_check:
        if dir_path.exists():
            files_found.extend([p for p in dir_path.rglob("*") if p.is_file()])
    return files_found


def reset_project() -> None:
    """Reset generated project artifacts and logs.

    This function identifies generated data and output directories and
    removes their contents after user confirmation.
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
