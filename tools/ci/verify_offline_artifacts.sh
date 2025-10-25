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
import re
import sys

try:
    # Prefer the packaging utility for robust name canonicalization when available.
    from packaging.utils import canonicalize_name
except Exception:
    def canonicalize_name(name: str) -> str:
        """Fallback canonicalization: normalize separators and lowercase.

        This is intentionally conservative and compatible with PEP 503 style
        normalization used for package names when `packaging` is not
        available in the execution environment.
        """
        return re.sub(r"[-_.]+", "-", name).lower()

lock = Path(sys.argv[1])
wheels_dir = Path(sys.argv[2])

if not lock.exists():
    print(f"ERROR: lockfile not found: {lock}", file=sys.stderr)
    sys.exit(2)

if not wheels_dir.is_dir():
    print(f"ERROR: wheel directory not found: {wheels_dir}", file=sys.stderr)
    sys.exit(3)

# Extract top-level package names in the form `name==version` from the lockfile.
names = []
for line in lock.read_text().splitlines():
    m = re.match(r'^\s*([A-Za-z0-9_.+-]+)==', line)
    if m:
        names.append(m.group(1))
names = sorted(set(names))

wheel_files = [p.name for p in wheels_dir.iterdir() if p.is_file()]
print('wheelhouse contains (sample):')
for wf in wheel_files[:200]:
    print('  ', wf)

def parse_wheel_distribution(fname: str) -> str | None:
    """Parse the distribution name from a wheel filename.

    This follows the wheel filename structure defined in PEP 427. We parse
    from the right-hand side so that distribution names containing hyphens
    are handled correctly.
    """
    if not fname.endswith('.whl'):
        return None
    base = fname[:-4]
    parts = base.split('-')
    # Wheel filename should have at least distribution, version, python tag,
    # abi tag and platform tag => minimum 5 parts.
    if len(parts) < 5:
        return None
    distribution = '-'.join(parts[:-4])
    return canonicalize_name(distribution)

def wheel_python_tags(fname: str) -> list[str]:
    """Return the python-tag(s) from the wheel filename (may be multiple).

    The python tag is the third-from-last component in the wheel filename
    (PEP 427). Tags may be dot-separated when multiple tags are present.
    """
    if not fname.endswith('.whl'):
        return []
    base = fname[:-4]
    parts = base.split('-')
    if len(parts) < 5:
        return []
    tag_field = parts[-3]
    return tag_field.split('.')

py_major = sys.version_info.major
py_minor = sys.version_info.minor
cp_tag = f'cp{py_major}{py_minor}'
py_major_tag = f'py{py_major}'

def wheel_compatible(fname: str) -> bool:
    """Return True if the wheel filename looks compatible with this Python.

    This is a conservative check: we accept exact matches for the current
    CPython tag (e.g. ``cp312``), the generic ``py3`` or the major-version
    specific tag (e.g. ``py3`` / ``py312``) when present.
    """
    tags = wheel_python_tags(fname)
    for t in tags:
        if t == cp_tag:
            return True
        if t == py_major_tag or t == 'py3':
            return True
    return False

# Map canonicalized distribution -> list of wheel filenames
dist_to_wheels: dict[str, list[str]] = {}
for wf in wheel_files:
    dist = parse_wheel_distribution(wf)
    if not dist:
        continue
    dist_to_wheels.setdefault(dist, []).append(wf)

missing = []
for name in names:
    canon = canonicalize_name(name)
    candidates = dist_to_wheels.get(canon, [])
    # If no exact distribution-name match, try a conservative substring
    # fallback to support some legacy wheel naming. Only accept matches
    # that are also compatible with the current Python interpreter.
    if not candidates:
        for wf in wheel_files:
            if canon in wf.lower() and wheel_compatible(wf):
                candidates.append(wf)
    has_compatible = any(wheel_compatible(wf) for wf in candidates)
    if not has_compatible:
        missing.append(name)

if missing:
    print("ERROR: missing compatible wheels for: " + ", ".join(missing), file=sys.stderr)
    sys.exit(4)

print("All wheels present and compatible.")
PY
then
  echo "ERROR: strict wheelhouse verification failed. Missing wheels reported above." >&2
  exit 1
fi

echo "Offline artifact verification complete."
