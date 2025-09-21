"""Smarter diagnose tool for hanging or failing pytest tests.

This script runs pytest per test file under a tests directory, but only for
files that look like real test modules (filenames starting with ``test_``).
For any file that fails or times out it will enumerate test node ids and run
each test function individually to pinpoint the failing or hanging node.

The script uses ``sys.executable -m pytest`` to ensure the same Python
interpreter is used as the environment running the script (typically the
project virtualenv).

Example
-------
python tools/smarter_diagnose_test_hangs.py --tests-dir tests --timeout 30 \
    --out tools/smarter_diagnose_results.json
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def list_test_files(tests_dir: Path) -> List[Path]:
    """Return sorted list of files under ``tests_dir`` whose names start with
    ``test_``.

    Parameters
    ----------
    tests_dir : Path
        Directory to search for test files.

    Returns
    -------
    list[Path]
        Sorted list of matching test file paths.
    """
    return sorted([p for p in tests_dir.rglob("test_*.py") if p.name != "conftest.py"])


def run_pytest_target(target: str, timeout: int) -> Tuple[int, str, str]:
    """Run pytest for a given target using the invoking Python interpreter.

    Parameters
    ----------
    target : str
        Pytest target, either a file path or a node id (``path::test_fn``).
    timeout : int
        Per-target timeout in seconds.

    Returns
    -------
    tuple[int, str, str]
        Return code, stdout and stderr (trimmed by the caller if desired).
    """

    def _to_text(v: object) -> str:
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8", errors="backslashreplace")
            except Exception:
                return str(v)
        return str(v) if v is not None else ""

    try:
        # Ensure the invoked pytest process uses the same per-test timeout
        # as this driver by exporting the PYTEST_TEST_TIMEOUT environment
        # variable. This keeps conftest's alarm handler and the subprocess
        # deadline in sync.
        env = dict(**dict(os.environ)) if "os" in globals() else None
        if env is not None:
            env.update({"PYTEST_TEST_TIMEOUT": str(timeout)})
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", target, "-q"],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, _to_text(proc.stdout), _to_text(proc.stderr)
    except subprocess.TimeoutExpired as exc:
        out = _to_text(getattr(exc, "output", "") or "")
        err = _to_text(getattr(exc, "stderr", "") or "")
        return -1, out, err
    except Exception as exc:  # pragma: no cover - defensive
        return -2, "", _to_text(exc)


def parse_test_nodeids(file_path: Path) -> List[str]:
    """Return a list of pytest nodeids defined in *file_path*.

    The function looks for top-level test functions and test methods inside
    test classes and returns fully-qualified node ids.
    """
    text = file_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    nodeids: List[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            nodeids.append(f"{file_path}::{node.name}")
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name.startswith("test_"):
                    nodeids.append(f"{file_path}::{node.name}::{sub.name}")
    return nodeids


def analyze_output_snippets(text: str) -> Dict[str, object]:
    """Heuristic analysis of pytest output that may indicate interactive hangs
    or resource problems.

    Returns a dictionary with detected patterns, whether lines repeat, a small
    preview of lines and a memory/kill hint if present.
    """
    patterns = [
        "Select language",
        "Choose an option",
        "Invalid choice",
        "Select program",
        "input()",
        "getpass.getpass",
        "Choose an option (1 or 2)",
        "KeyboardInterrupt",
    ]
    found = [p for p in patterns if p in text]
    lines = [l for l in text.splitlines() if l.strip()]
    repeats = any(lines.count(l) > 10 for l in set(lines)) if lines else False
    mem_issue = any(
        k in text
        for k in ("MemoryError", "Killed", "OOM", "OutOfMemory", "out of memory")
    )
    return {
        "patterns": found,
        "repeated_lines": repeats,
        "memory_issue": mem_issue,
        "preview": lines[:40],
    }


def diagnose(tests_dir: Path, timeout: int, out: Path) -> int:
    """Run per-file pytest diagnoses and write a JSON report.

    Parameters
    ----------
    tests_dir : Path
        Directory containing tests to diagnose.
    timeout : int
        Per-target timeout in seconds.
    out : Path
        Output JSON path for the report.

    Returns
    -------
    int
        Exit code: 0 if no problems found, 1 otherwise.
    """
    files = list_test_files(tests_dir)
    # Ensure the output file is cleared before we start so repeated runs
    # don't accumulate or accidentally append to an existing report.
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
    except Exception:
        # Non-fatal: continue even if we cannot remove the old file.
        pass
    report: Dict[str, object] = {"files": {}, "summary": {}}
    any_problem = False
    for f in files:
        key = str(f)
        print("Running:", key)
        rc, out_str, err_str = run_pytest_target(key, timeout)
        if rc == 0:
            status = "PASS"
        elif rc == -1:
            status = "TIMEOUT"
        elif rc == 5:
            # pytest exit code 5 means "no tests collected"; treat as SKIP
            status = "SKIPPED_NO_TESTS"
        else:
            status = "FAIL"

        entry = {
            "status": status,
            "rc": rc,
            "stdout": out_str[:2000],
            "stderr": err_str[:2000],
        }
        report["files"][key] = entry
        if status not in ("PASS", "SKIPPED_NO_TESTS"):
            any_problem = True
            nodeids = parse_test_nodeids(f)
            entry["items"] = []
            for node in nodeids:
                print("  Running node:", node)
                rc2, out2, err2 = run_pytest_target(node, timeout)
                stat2 = (
                    "PASS"
                    if rc2 == 0
                    else (
                        "TIMEOUT" if rc2 == -1 else ("NO_TESTS" if rc2 == 5 else "FAIL")
                    )
                )
                info = {
                    "nodeid": node,
                    "status": stat2,
                    "rc": rc2,
                    "stdout": out2[:2000],
                    "stderr": err2[:2000],
                }
                info.update(analyze_output_snippets((out2 or "") + (err2 or "")))
                entry["items"].append(info)

    report["summary"]["total_files"] = len(files)
    report["summary"]["problem_files"] = sum(
        1
        for v in report["files"].values()
        if v["status"] not in ("PASS", "SKIPPED_NO_TESTS")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote report to", out)
    return 0 if not any_problem else 1


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tests-dir", type=Path, default=Path("tests"))
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument(
        "--out", type=Path, default=Path("tools/smarter_diagnose_results.json")
    )
    args = p.parse_args(argv)
    return diagnose(args.tests_dir, args.timeout, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
