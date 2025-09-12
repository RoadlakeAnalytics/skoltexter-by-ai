"""Check that the generated SBOM matches the tracked `sbom.json`.

This script generates a temporary SBOM from `requirements.lock` and
compares it to the checked-in `sbom.json`. It exits non-zero in CI to
enforce that the SBOM is kept up-to-date. Locally it prints an
informative message and returns success to avoid pre-commit rewriting
the tracked file during developer runs.

Usage: python tools/ci/check_sbom.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    """Generate and compare a temporary SBOM against tracked `sbom.json`.

    Returns 0 when the SBOM matches or when running locally and a
    mismatch occurred (the user will be instructed how to regenerate and
    commit). Returns non-zero in CI to enforce SBOM updates.
    """
    root = Path(__file__).resolve().parents[2]
    req_lock = root / "requirements.lock"
    tracked = root / "sbom.json"

    if not req_lock.exists():
        print("[sbom-check] requirements.lock not found, skipping SBOM check.")
        return 0

    with tempfile.TemporaryDirectory() as td:
        tmp_out = Path(td) / "sbom.json"
        cmd = [
            sys.executable,
            "-m",
            "cyclonedx_py",
            "requirements",
            "-i",
            str(req_lock),
            "-o",
            str(tmp_out),
            "--output-format",
            "json",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            print("[sbom-check] Failed to generate SBOM:")
            print(exc.stdout or exc.stderr or str(exc))
            # In CI we should fail; locally prefer to inform the user.
            if os.environ.get("CI"):
                return 1
            return 0

        # Read and compare JSON normalized
        try:
            gen = json.loads(tmp_out.read_text(encoding="utf8"))
            tracked_json = json.loads(tracked.read_text(encoding="utf8"))
        except Exception as exc:
            print(f"[sbom-check] Error reading SBOM files: {exc}")
            if os.environ.get("CI"):
                return 1
            return 0

        if gen != tracked_json:
            msg = (
                "[sbom-check] Generated SBOM differs from tracked `sbom.json`.\n"
                "Run the SBOM generator and commit the updated file:\n"
                "  python -m cyclonedx_py requirements -i requirements.lock -o sbom.json --output-format json\n"
            )
            if os.environ.get("CI"):
                print(msg, file=sys.stderr)
                return 1
            else:
                print(msg)
                # Locally do not fail pre-commit to avoid the race where the
                # hook rewrites the tracked file and causes the commit to fail.
                return 0

    print("[sbom-check] SBOM is up-to-date.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
