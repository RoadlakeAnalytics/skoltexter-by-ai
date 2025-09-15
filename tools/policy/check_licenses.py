"""License allowlist check using pip-licenses output with normalization.

This script runs ``pip-licenses`` and validates that only permissive licenses
are used. It normalizes common license string variants to SPDX-like identifiers,
handles mixed expressions (e.g., "Apache-2.0 AND MIT"), and applies
package-specific overrides for packages that report unclear or missing metadata.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Iterable

# Permissive SPDX identifiers we allow
ALLOWED = {
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSD",  # some tools report the generic text
    "Apache-2.0",
    "ISC",
    "MPL-2.0",
    "PSF-2.0",
    "Unlicense",
}

# Package-specific overrides to correct messy/unknown license strings
PKG_OVERRIDES: dict[str, str] = {
    # Previously UNKNOWN in CI
    "CacheControl": "Apache-2.0",
    "attrs": "MIT",
    "click": "BSD-3-Clause",
    "jsonschema": "MIT",
    "jsonschema-specifications": "MIT",
    "mypy_extensions": "MIT",
    "pytest-asyncio": "Apache-2.0",
    "referencing": "MIT",
    "rpds-py": "MIT",
    "types-python-dateutil": "Apache-2.0 AND MIT",
    "typing_extensions": "PSF-2.0",
    "urllib3": "MIT",
    # Known permissive packages with varying reported strings
    "Jinja2": "BSD-3-Clause",
    "MarkupSafe": "BSD-3-Clause",
    "Pygments": "BSD-3-Clause",
    "idna": "BSD-3-Clause",
    "lxml": "BSD-3-Clause",
    "pathspec": "MPL-2.0",
    "tqdm": "MIT",
    "python-dateutil": "BSD-3-Clause OR Apache-2.0",
}

# Map common textual variants to SPDX-like identifiers
MAP_TO_SPDX: dict[str, str] = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",  # conservative mapping
    "Apache Software License": "Apache-2.0",
    "Apache 2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "The Unlicense (Unlicense)": "Unlicense",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
    "PSF": "PSF-2.0",
    "PSF-2.0": "PSF-2.0",
    "ISC License (ISCL)": "ISC",
}

# Disallow strong copyleft licenses
DISALLOWED_RE = re.compile(r"\bGPL\b|LGPL|AGPL", re.IGNORECASE)


def normalize(license_str: str) -> list[str]:
    """Normalize a license string into a list of SPDX-like identifiers.

    Handles combined expressions like "Apache-2.0 AND MIT" or
    semicolon-separated variants such as "BSD License;MIT License".

    Parameters
    ----------
    license_str : str
        Raw license string from pip-licenses.

    Returns
    -------
    list[str]
        A list of normalized license identifiers (best-effort).
    """
    if not license_str:
        return []

    s = license_str.strip()
    s = s.replace(";", " AND ")  # harmonize delimiters
    parts = re.split(r"\s+(?:AND|OR|,)\s+", s, flags=re.IGNORECASE)
    out: list[str] = []
    for p in parts:
        p2 = MAP_TO_SPDX.get(p.strip(), p.strip())
        out.append(p2)
    return out


def is_permissive(licenses: Iterable[str]) -> bool:
    """Determine whether a set of licenses is permissive.

    A set is considered permissive when at least one identifier belongs to the
    allowlist and none match the disallowed GPL/AGPL/LGPL patterns.

    Parameters
    ----------
    licenses : Iterable[str]
        Normalized license identifiers to evaluate.

    Returns
    -------
    bool
        ``True`` if the set is permissive and free from copyleft patterns,
        otherwise ``False``.
    """
    saw_allowed = False
    for lic in licenses:
        if DISALLOWED_RE.search(lic):
            return False
        if lic in ALLOWED:
            saw_allowed = True
    return saw_allowed


def get_pip_licenses() -> list[dict]:
    """Return pip-licenses data as a JSON-parsed list of dictionaries.

    Returns
    -------
    list[dict]
        The parsed JSON output from ``pip-licenses``.

    Raises
    ------
    subprocess.CalledProcessError
        If the ``pip-licenses`` subprocess fails.
    """
    cmd = [
        "pip-licenses",
        "--format=json",
        "--with-authors",
        "--with-urls",
        "--with-license-file",
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(res.stdout or "[]")


def main() -> int:
    """Run pip-licenses, normalize results, and enforce the allowlist policy.

    The command prints a concise summary of any violations and exits with a
    non-zero status when disallowed or unknown licenses are detected.

    Returns
    -------
    int
        ``0`` when all dependencies conform to policy, otherwise ``1``.
    """
    try:
        data = get_pip_licenses()
    except Exception as exc:  # pragma: no cover - tool/runtime environment issue
        print(f"[license-check] Failed to run pip-licenses: {exc}", file=sys.stderr)
        return 2

    bad: list[tuple[str, str]] = []
    for row in data:
        pkg = row.get("Name") or row.get("Package") or "<unknown>"
        lic_raw = (row.get("License") or "").strip()
        # Skip placeholder meta-packages some environments inject
        if pkg == "pre-commit-placeholder-package":
            continue

        # Apply package-level overrides when available
        if pkg in PKG_OVERRIDES:
            lic_raw = PKG_OVERRIDES[pkg]

        normed = normalize(lic_raw)
        if not normed or not is_permissive(normed):
            bad.append((pkg, lic_raw))

    if bad:
        print(
            "[license-check] Disallowed or unknown licenses detected:", file=sys.stderr
        )
        for pkg, lic in sorted(bad, key=lambda x: x[0].lower()):
            print(f"  - {pkg}: {lic}", file=sys.stderr)
        return 1

    print("[license-check] OK - only permissive licenses detected.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
