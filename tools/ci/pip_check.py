"""Wrapper for `pip check` that prefers the project's venv.

This script attempts to locate a local virtual environment in one of the
conventional locations (`venv/` or `.venv/`) and run `pip check` using that
environment's Python interpreter. If no venv is present, it falls back to the
current interpreter. This helps pre-commit run dependency checks against the
intended environment rather than the system Python, reducing false positives
when the developer has a properly provisioned venv.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def find_venv_python() -> str | None:
    """Return the path to a venv's Python executable if present.

    The function checks `venv/` and `.venv/` directories relative to the
    repository root. If one exists and contains a `bin/python` executable,
    its path is returned. Otherwise ``None`` is returned.
    """
    root = Path(__file__).resolve().parents[2]
    for name in ("venv", ".venv"):
        candidate = root / name / "bin" / "python"
        if candidate.exists():
            return str(candidate)
    return None


def main() -> int:
    """Run pip check in the preferred Python environment.

    Returns
    -------
    int
        Exit code from the `pip check` invocation.
    """
    python_exe = find_venv_python() or sys.executable
    pip = shutil.which("pip", path=str(Path(python_exe).parent))
    if not pip:
        # Fall back to invoking `python -m pip check` which is reliable.
        cmd = [python_exe, "-m", "pip", "check"]
    else:
        cmd = [pip, "check"]

    print(f"[pip-check] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
