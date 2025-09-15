"""Cleanup utility to remove mutation and cache directories before checks.

Removes the following directories if present at the project root:
- ``mutants`` (leftover from mutation testing)
- ``.pytest_cache``
- ``.mypy_cache``
- ``.ruff_cache``
and recursively removes any ``__pycache__`` directories under the repository.

This script is idempotent and best-effort: failures are ignored so that it
doesn't block quality gates.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _safe_rmtree(path: Path) -> None:
    """Remove a directory tree if it exists, ignoring errors.

    Parameters
    ----------
    path : Path
        Directory to remove.
    """
    # Do not perform deletions unless an explicit CI environment variable
    # is present. This avoids accidental deletion when running locally.
    if not os.environ.get("CI_CLEANUP_ALLOWED"):
        return
    try:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def main() -> int:
    """Perform cache cleanup and return 0 regardless of failures.

    Returns
    -------
    int
        Always returns ``0`` to avoid blocking pre-commit/CI.
    """
    root = Path(__file__).resolve().parents[2]
    for name in ("mutants", ".pytest_cache", ".mypy_cache", ".ruff_cache"):
        _safe_rmtree(root / name)

    # Remove all __pycache__ dirs except inside .git or venvs
    for dirpath, dirnames, _filenames in os.walk(root):
        # Prune VCS and venvs
        base = os.path.basename(dirpath)
        if base in {".git", "venv", ".venv"}:
            dirnames[:] = []  # don't descend further
            continue
        if os.path.basename(dirpath) == "__pycache__":
            _safe_rmtree(Path(dirpath))
            # Do not descend into removed directory
            dirnames[:] = []
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
