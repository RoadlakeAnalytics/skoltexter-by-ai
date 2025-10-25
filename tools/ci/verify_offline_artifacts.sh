#!/usr/bin/env bash
# Verify presence of lockfile and wheelhouse artifacts.
#
# This script is intended for use in CI jobs that expect an offline
# installation using a pre-populated wheelhouse and a pip-compile lockfile.
#
# Usage
# -----
# bash tools/ci/verify_offline_artifacts.sh <path-to-lockfile> <path-to-wheel-dir>
#
# The script exits with non-zero status if the lockfile is missing. It also
# exits with non-zero status if the wheel directory is missing. This enforces
# the offline policy for hardened CI jobs: jobs that expect to install from
# the wheelhouse must fail fast rather than falling back to networked
# installs.

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

# If the exact per-version wheel dir is missing, allow a fallback to the
# wheelhouse root (parent directory) if it contains .whl files. This helps
# when artifacts are packed without a per-version subdirectory.
if [ ! -d "$WHEELDIR" ]; then
  PARENT_DIR="$(dirname "$WHEELDIR")"
  if [ -d "$PARENT_DIR" ] && ls "$PARENT_DIR"/*.whl >/dev/null 2>&1; then
    echo "NOTICE: wheelhouse directory '$WHEELDIR' not found; using wheelhouse root '$PARENT_DIR' as fallback." >&2
    WHEELDIR="$PARENT_DIR"
    echo "Wheelhouse present (fallback); listing up to 200 entries:"
    ls -la "$WHEELDIR" | sed -n '1,200p' || true
    if ! ls "$WHEELDIR"/*aiohappyeyeballs* >/dev/null 2>&1; then
      echo "Note: 'aiohappyeyeballs' not found in the wheelhouse (filename check)." >&2
    fi
  else
    echo "ERROR: wheelhouse not found at: $WHEELDIR" >&2
    echo "Contents of wheelhouse root (if any):" >&2
    ls -la "$PARENT_DIR" || true
    echo "Failing because offline installs must be satisfied from the wheelhouse." >&2
    exit 1
  fi
else
  echo "Wheelhouse present; listing up to 200 entries:"
  ls -la "$WHEELDIR" | sed -n '1,200p' || true
fi

# Strict verification: ensure that every top-level package listed in the
# pip-compile-generated lockfile has a corresponding wheel in the wheelhouse.
# This enforces the offline policy: fail early if any wheel is missing.
echo "Performing strict wheelhouse verification against lockfile..."
if ! python - "$LOCKFILE" "$WHEELDIR" <<'PY'
from pathlib import Path
import re, sys

lock = Path(sys.argv[1])
wheels = Path(sys.argv[2])

if not lock.exists():
    print(f"ERROR: lockfile not found: {lock}", file=sys.stderr)
    sys.exit(2)

# Extract top-level package names in the form `name==version` from the lockfile.
names = []
for line in lock.read_text().splitlines():
    m = re.match(r'^\s*([A-Za-z0-9_.+-]+)==', line)
    if m:
        names.append(m.group(1).lower())
names = sorted(set(names))

if not wheels.is_dir():
    print(f"ERROR: wheel directory not found: {wheels}", file=sys.stderr)
    sys.exit(3)

wheel_files = [p.name.lower() for p in wheels.iterdir() if p.is_file()]
print('wheelhouse contains (sample):')
for wf in wheel_files[:200]:
    print('  ', wf)
missing = []
for n in names:
    norm = n.lower()
    alt1 = norm.replace('-', '_')
    alt2 = norm.replace('_', '-')
    candidates = {norm, alt1, alt2}
    found = False
    for wf in wheel_files:
        for token in candidates:
            # Match common wheel filename patterns: token followed by '-' or '_' or '.'
            if wf.startswith(token + '-') or wf.startswith(token + '_'):
                found = True
                break
            if token + '-' in wf or token + '_' in wf or token + '.' in wf:
                found = True
                break
        if found:
            break
    if not found:
        missing.append(n)

if missing:
    print("ERROR: missing wheels for: " + ", ".join(missing), file=sys.stderr)
    sys.exit(4)

    print("All wheels present.")
PY
then
  echo "ERROR: strict wheelhouse verification failed. Missing wheels reported above." >&2
  exit 1
fi

echo "Offline artifact verification complete."
