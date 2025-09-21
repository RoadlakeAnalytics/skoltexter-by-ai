#!/usr/bin/env python3
"""Attempt safe migration of tests that inject a ModuleType shim.

This script finds test files that create a ``ModuleType("src.setup.app")``
object and registers it in ``sys.modules``. For files that only use the
local ``app`` namespace it is safe to replace the ModuleType injection
with a simple local ``app = _app_ns``. The script updates the file,
runs pytest for the single file, and reverts the change if the test
fails. This allows batch migration while keeping the repo in a runnable
state.

Usage: run from the repository root in the project venv.
    python tools/migrate_shim_tests.py

"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = PROJECT_ROOT / "tests"


def find_candidate_files() -> List[Path]:
    files: List[Path] = []
    for p in TEST_DIR.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        # Skip files that explicitly import the legacy shim at top-level
        if (
            "import src.setup.app" in text
            or 'importlib.import_module("src.setup.app")' in text
        ):
            continue
        if 'ModuleType("src.setup.app")' in text:
            files.append(p)
    return sorted(files)


def try_migrate_file(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")

    # Heuristic: find the block that defines ModuleType("src.setup.app")
    mstart = text.find("from types import ModuleType")
    if mstart == -1:
        return False
    mend = text.find('_sys.modules["src.setup.app"] = _mod', mstart)
    if mend == -1:
        return False
    # Include the trailing line and possible 'app = _mod'
    mend_line_end = text.find("\n", mend)
    if mend_line_end == -1:
        mend_line_end = mend
    # Try to include an 'app = _mod' line if present immediately after
    tail = text[mend_line_end + 1 : mend_line_end + 200]
    if tail.startswith("\n"):
        tail = tail[1:]
    if tail.startswith("app = _mod"):
        # find end of that line too
        second_end = text.find("\n", mend_line_end + 1)
        if second_end != -1:
            mend_line_end = second_end

    new_text = text[:mstart] + "app = _app_ns\n" + text[mend_line_end + 1 :]

    # Backup original
    orig = text
    p.write_text(new_text, encoding="utf-8")

    # Run pytest for the single file
    print(f"Running pytest for {p} ...")
    res = subprocess.run(["pytest", "-q", str(p)], cwd=PROJECT_ROOT)
    if res.returncode == 0:
        print(f"Migration successful for {p}")
        return True
    else:
        print(f"Migration failed for {p}; reverting")
        p.write_text(orig, encoding="utf-8")
        return False


def main() -> int:
    candidates = find_candidate_files()
    if not candidates:
        print("No candidate files found.")
        return 0
    print(f"Found {len(candidates)} candidates; attempting migration one-by-one.")
    succeeded = []
    failed = []
    for p in candidates:
        ok = try_migrate_file(p)
        if ok:
            succeeded.append(p)
        else:
            failed.append(p)

    print("\nSummary")
    print("Succeeded:")
    for p in succeeded:
        print("  ", p)
    print("Failed:")
    for p in failed:
        print("  ", p)

    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
