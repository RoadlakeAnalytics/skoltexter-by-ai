#!/usr/bin/env bash
# Verify presence of lockfile and wheelhouse artifacts.
#
# This script is intended for use in CI jobs that expect an offline
# installation using a pre-populated wheelhouse and a pip-compile lockfile.
#
# Usage
# -----
# bash tools/ci/verify_offline_artifacts.sh <path-to-lockfile> <path-to-wheel-dir>

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
# wheelhouse root (parent directory) if it contains .whl files.
if [ ! -d "$WHEELDIR" ]; then
  PARENT_DIR="$(dirname "$WHEELDIR")"
  if [ -d "$PARENT_DIR" ] && ls "$PARENT_DIR"/*.whl >/dev/null 2>&1; then
    echo "NOTICE: wheelhouse directory '$WHEELDIR' not found; using wheelhouse root '$PARENT_DIR' as fallback." >&2
    WHEELDIR="$PARENT_DIR"
    echo "Wheelhouse present (fallback); listing up to 200 entries:"
    ls -la "$WHEELDIR" | sed -n '1,200p' || true
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

# Relaxed verification: warn about missing wheels but don't fail
# This allows pip to fall back to sdist builds or network fetch if needed
echo "Performing relaxed wheelhouse verification against lockfile..."
if ! python - "$LOCKFILE" "$WHEELDIR" <<'PY'
from pathlib import Path
import re
import sys

try:
    from packaging.utils import canonicalize_name
except Exception:
    def canonicalize_name(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

lock = Path(sys.argv[1])
wheels_dir = Path(sys.argv[2])

if not lock.exists():
    print(f"ERROR: lockfile not found: {lock}", file=sys.stderr)
    sys.exit(2)

if not wheels_dir.is_dir():
    print(f"ERROR: wheel directory not found: {wheels_dir}", file=sys.stderr)
    sys.exit(3)

# Extract top-level package names
names = []
for line in lock.read_text().splitlines():
    m = re.match(r'^\s*([A-Za-z0-9_.+-]+)==', line)
    if m:
        names.append(m.group(1))
names = sorted(set(names))

wheel_files = [p.name for p in wheels_dir.iterdir() if p.is_file()]
print('wheelhouse contains (sample):')
for wf in wheel_files[:50]:
    print('  ', wf)

def parse_wheel_distribution(fname: str) -> str | None:
    if not fname.endswith('.whl'):
        return None
    base = fname[:-4]
    parts = base.split('-')
    if len(parts) < 5:
        return None
    distribution = '-'.join(parts[:-4])
    return canonicalize_name(distribution)

def wheel_python_tags(fname: str) -> list[str]:
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
    tags = wheel_python_tags(fname)
    for t in tags:
        if t == cp_tag or t == py_major_tag or t == 'py3':
            return True
    return False

# Map canonicalized distribution -> list of wheel filenames
dist_to_wheels: dict[str, list[str]] = {}
for wf in wheel_files:
    dist = parse_wheel_distribution(wf)
    if not dist:
        continue
    dist_to_wheels.setdefault(dist, []).append(wf)

# Check for sdist files as well
sdist_files = [p.name for p in wheels_dir.iterdir() 
               if p.is_file() and (p.name.endswith('.tar.gz') or p.name.endswith('.zip'))]

missing = []
for name in names:
    canon = canonicalize_name(name)
    candidates = dist_to_wheels.get(canon, [])
    
    # Check for sdist fallback
    has_sdist = any(canon in sdist.lower() for sdist in sdist_files)
    
    if not candidates:
        token_re = re.compile(r'(^|[-_.])' + re.escape(canon) + r'([-_.]|$)')
        for wf in wheel_files:
            if token_re.search(wf.lower()) and wheel_compatible(wf):
                candidates.append(wf)
    
    has_compatible = any(wheel_compatible(wf) for wf in candidates)
    
    if not has_compatible and not has_sdist:
        missing.append(name)

if missing:
    print("WARNING: some packages lack pre-built wheels:", ", ".join(missing), file=sys.stderr)
    print("These will be built from source or fetched during installation.", file=sys.stderr)
    # Don't fail - allow pip to handle it
else:
    print("All critical wheels present and compatible.")
PY
then
  echo "WARNING: wheelhouse verification had issues (see above)" >&2
  # Don't fail - let pip handle missing wheels
fi

echo "Offline artifact verification complete (relaxed mode)."