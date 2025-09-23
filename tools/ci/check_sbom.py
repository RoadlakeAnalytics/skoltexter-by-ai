"""SBOM generation and optional comparison.

This tool generates a temporary Software Bill of Materials (CycloneDX JSON)
from ``requirements.lock`` using ``cyclonedx_py``. When a tracked
``sbom.json`` is present in the repository, the script compares the generated
SBOM with the tracked file. When no tracked SBOM exists, the script treats
successful generation as a pass and skips comparison. The tool is suitable
for use in automation such as pre-commit hooks or CI pipelines.

Usage
-----
Run from the repository root or via pre-commit:

    python tools/ci/check_sbom.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    """Generate a temporary SBOM and optionally compare with a tracked file.

    The function always attempts SBOM generation from ``requirements.lock``.
    If a tracked ``sbom.json`` is present, the generated document is parsed and
    compared to the tracked one. A mismatch results in a non-zero exit code
    to signal failure to the caller. When no tracked SBOM is present,
    comparison is skipped and the check passes provided generation succeeded.

    Returns
    -------
    int
        ``0`` on success (generation succeeded and comparison passed or was
        skipped), otherwise ``1`` on failure.
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

        # If there is no tracked SBOM in the repository, do not enforce a diff.
        # We only validate that generation succeeds. CI publishes SBOM as an artifact.
        if not tracked.exists():
            print(
                "[sbom-check] No tracked SBOM found; skipping diff. CI publishes artifact."
            )
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
