"""License allowlist check using pip-licenses output.

Runs `pip-licenses --format=json` and fails if any package license is not in the
allowlist. Prints a compact report of violations.
"""

from __future__ import annotations

import json
import subprocess
import sys

ALLOWED = {
    "MIT",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "Apache-2.0",
    "Apache Software License",
    "ISC",
    "MPL-2.0",
    "Python-2.0",
    "PSF",
    "LGPL-3.0-or-later",
}

IGNORED_PACKAGES = {
    "pre-commit-placeholder-package",
}


def main() -> int:
    """Run pip-licenses and validate licenses against allowlist.

    Returns
    -------
    int
        Exit code where 0 indicates success, 1 indicates disallowed or
        unspecified licenses were found, and 2 indicates a tooling error
        (e.g., running pip-licenses or parsing its JSON output failed).
    """
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "piplicenses",
                "--format=json",
                "--from=mixed",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - hook environment failure
        print(f"[license-check] Failed to run pip-licenses: {exc}", file=sys.stderr)
        return 2

    try:
        data: list[dict[str, str]] = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        print("[license-check] Invalid JSON from pip-licenses", file=sys.stderr)
        return 2

    violations: list[dict[str, str]] = []
    for row in data:
        lic = (row.get("License") or "").strip()
        pkg = row.get("Name") or row.get("Package") or "<unknown>"
        if pkg in IGNORED_PACKAGES:
            continue
        if lic and lic not in ALLOWED:
            violations.append({"package": pkg, "license": lic})
        if not lic:
            violations.append({"package": pkg, "license": "<unspecified>"})

    if violations:
        print("[license-check] Disallowed licenses detected:")
        for v in violations:
            print(f"  - {v['package']}: {v['license']}")
        return 1

    print("[license-check] All package licenses are allowed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
