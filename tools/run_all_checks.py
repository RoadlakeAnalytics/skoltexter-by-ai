"""Run full local quality suite: lint, tests, docs, mutation, SAST.

This script orchestrates the project's strict local quality gates to mirror CI.
It runs pre-commit hooks (commit and push stages), executes tests twice with
randomized order and full coverage gating, checks docstring coverage, runs
mutation tests, and triggers Semgrep via the pre-commit hook.

The script exits with a non-zero code on the first failure encountered.

Functions are intentionally small and linear to stay easy to audit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> bool:
    """Run a command and return True on success.

    Parameters
    ----------
    cmd : list[str]
        Command and arguments to execute.

    Returns
    -------
    bool
        ``True`` if the command returns exit code 0, else ``False``.

    Examples
    --------
    >>> _run([sys.executable, '-c', 'print(123)'])  # doctest: +ELLIPSIS
    True
    """
    print(f"[run-all] $ {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode == 0


def run_precommit_all() -> bool:
    """Run pre-commit for all files (commit-stage checks)."""
    return _run(["pre-commit", "run", "--all-files"])  # Formats, lint, bandit, audit


def run_precommit_push_stage() -> bool:
    """Run pre-commit push-stage hooks on all files."""
    return _run(["pre-commit", "run", "--hook-stage", "push", "--all-files"])


def run_tests_with_coverage() -> bool:
    """Run pytest with randomized order (seed=1) and full coverage gating."""
    cmd = [
        "pytest",
        "-q",
        "--maxfail=1",
        "--randomly-seed=1",
        "--cov=src",
        "--cov=setup_project",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=100",
        "tests",
    ]
    return _run(cmd)


def run_tests_seed_2() -> bool:
    """Run pytest again with a different seed to catch order issues."""
    return _run(["pytest", "-q", "--maxfail=1", "--randomly-seed=2", "tests"])


def run_tests_many_random(iterations: int = 100) -> bool:
    """Run pytest repeatedly with different random seeds.

    Parameters
    ----------
    iterations : int, default 100
        Number of distinct random seeds to run. Seeds are chosen deterministically
        as 1..``iterations`` to simplify reproduction.

    Returns
    -------
    bool
        ``True`` if all iterations pass, otherwise ``False``.

    Examples
    --------
    >>> isinstance(run_tests_many_random, object)
    True
    """
    for seed in range(1, iterations + 1):
        print(f"[run-all] Step: pytest (seed={seed})")
        if not _run(
            ["pytest", "-q", "--maxfail=1", f"--randomly-seed={seed}", "tests"]
        ):
            return False
    return True


def run_docstrings_gate() -> bool:
    """Run interrogate to enforce docstring coverage == 100%."""
    return _run(["interrogate", "-v", "--fail-under", "100", "src/"])


def run_mutation_gate() -> bool:
    """Run mutation tests and fail if any survivors remain."""
    exe = [sys.executable, str(Path("tools/ci/mutmut_gate.py"))]
    return _run(exe)


def main(argv: list[str] | None = None) -> int:
    """Run the complete set of local quality checks in sequence.

    Returns
    -------
    int
        Exit code compatible with shells: 0 on success, 1 on first failure.

    Examples
    --------
    >>> callable(main)
    True
    """
    argv = argv or sys.argv[1:]
    extreme = "--extreme" in argv
    if extreme:
        steps = [
            ("pre-commit (all-files)", run_precommit_all),
            ("pytest (seed=1, coverage)", run_tests_with_coverage),
            ("pytest (100 random seeds)", run_tests_many_random),
            ("interrogate (docstrings 100%)", run_docstrings_gate),
            ("mutmut (mutation gate)", run_mutation_gate),
            ("pre-commit (push stage)", run_precommit_push_stage),
        ]
    else:
        steps = [
            ("pre-commit (all-files)", run_precommit_all),
            ("pytest (seed=1, coverage)", run_tests_with_coverage),
            ("pytest (seed=2)", run_tests_seed_2),
            ("interrogate (docstrings 100%)", run_docstrings_gate),
            ("mutmut (mutation gate)", run_mutation_gate),
            ("pre-commit (push stage)", run_precommit_push_stage),
        ]
    for name, fn in steps:
        print(f"[run-all] Step: {name}")
        ok = fn()
        if not ok:
            print(f"[run-all] FAIL: {name}")
            return 1
    print("[run-all] All checks passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
