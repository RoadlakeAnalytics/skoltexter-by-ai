#!/usr/bin/env bash
"""Verify presence of lockfile and wheelhouse artifacts.

This script is intended for use in CI jobs that expect an offline
installation using a pre-populated wheelhouse and a pip-compile lockfile.

Usage
-----
bash tools/ci/verify_offline_artifacts.sh <path-to-lockfile> <path-to-wheel-dir>

The script exits with non-zero status if the lockfile is missing. It also
exits with non-zero status if the wheel directory is missing. This enforces
the offline policy for hardened CI jobs: jobs that expect to install from
the wheelhouse must fail fast rather than falling back to networked
installs.
"""

set -euo pipefail

LOCKFILE="${1:-}"
WHEELDIR="${2:-}"

if [ -z "$LOCKFILE" ] || [ -z "$WHEELDIR" ]; then
  echo "Usage: $0 <path-to-lockfile> <path-to-wheel-dir>" >&2
  exit 2
fi

echo "Verifying offline artifacts"
echo "  lockfile: $LOCKFILE"
echo "  wheeldir: $WHEELDIR"

if [ ! -f "$LOCKFILE" ]; then
  echo "ERROR: lockfile not found: $LOCKFILE" >&2
  echo "Contents of lockfiles/ (if any):" >&2
  ls -la "$(dirname "$LOCKFILE")" || true
  exit 1
fi

if [ ! -d "$WHEELDIR" ]; then
  echo "ERROR: wheelhouse not found at: $WHEELDIR" >&2
  echo "Contents of wheelhouse root (if any):" >&2
  ls -la "$(dirname \"$WHEELDIR\")" || true
  echo "Failing because offline installs must be satisfied from the wheelhouse." >&2
  exit 1
else
  echo "Wheelhouse present; listing up to 200 entries:" 
  ls -la "$WHEELDIR" | sed -n '1,200p' || true
  # quick filename check for a common problematic package
  if ! ls "$WHEELDIR"/*aiohappyeyeballs* >/dev/null 2>&1; then
    echo "Note: 'aiohappyeyeballs' not found in the wheelhouse (filename check)." >&2
  fi
fi

echo "Offline artifact verification complete."
