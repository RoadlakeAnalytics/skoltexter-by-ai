#!/usr/bin/env bash
# Build a wheelhouse (collection of .whl files) for the project's locked requirements.
#
# This script builds wheels using a local Python interpreter and the
# hash-locked `requirements.lock` created by `pip-compile`. It intentionally
# does not use Docker; run it on a developer machine or CI runner that has
# the necessary build toolchain and network access.
#
# Usage:
#   bash tools/ci/build_wheelhouse.sh [--python python3.12] [--lock lockfiles/requirements.lock-3.12] [--wheel-dir wheelhouse/3.12]

set -euo pipefail

PYTHON="python3.12"
LOCKFILE="lockfiles/requirements.lock-3.12"
WHEEL_DIR="wheelhouse/3.12"

# Optional cross-platform download parameters forwarded to `pip download`.
# These are useful when generating a Linux wheelhouse from macOS/Windows by
# instructing pip to fetch wheels for a different platform.
DOWNLOAD_PLATFORM=""
DOWNLOAD_PYTHON_VERSION=""
DOWNLOAD_IMPLEMENTATION=""
DOWNLOAD_ABI=""
DOWNLOAD_ONLY_BINARY=false

usage() {
  cat <<USAGE
Usage: $0 [--python PYTHON_EXEC] [--lock LOCKFILE] [--wheel-dir WHEEL_DIR]

Example:
  bash $0 --python python3.12 --lock lockfiles/requirements.lock-3.12 --wheel-dir wheelhouse/3.12

The script will attempt to ensure `pip` and `wheel` are available in the
specified Python environment. It will then build wheels and run the
strict verification script. If any wheel is missing the verification will
fail and the script will exit non-zero.
USAGE
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --python)
      PYTHON="$2"; shift 2;;
    --lock)
      LOCKFILE="$2"; shift 2;;
    --wheel-dir)
      WHEEL_DIR="$2"; shift 2;;
    --download-platform)
      DOWNLOAD_PLATFORM="$2"; shift 2;;
    --download-python-version)
      DOWNLOAD_PYTHON_VERSION="$2"; shift 2;;
    --download-implementation)
      DOWNLOAD_IMPLEMENTATION="$2"; shift 2;;
    --download-abi)
      DOWNLOAD_ABI="$2"; shift 2;;
    --download-only-binary)
      DOWNLOAD_ONLY_BINARY=true; shift 1;;
    -h|--help)
      usage;;
    *)
      echo "Unknown argument: $1" >&2; usage;;
  esac
done

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: Python executable '$PYTHON' not found in PATH." >&2
  exit 3
fi

if [ ! -f "$LOCKFILE" ]; then
  echo "ERROR: lockfile not found: $LOCKFILE" >&2
  echo "Run: bash tools/ci/regenerate_lockfile.sh --python $PYTHON --out $LOCKFILE" >&2
  exit 4
fi

mkdir -p "$WHEEL_DIR"

echo "Ensuring pip and wheel are available in $PYTHON..."
$PYTHON -m pip install --upgrade pip wheel

echo "Downloading available binary distributions into: $WHEEL_DIR"
# Compose optional download args for cross-platform retrieval.
DOWNLOAD_ARGS=()
if [ -n "$DOWNLOAD_PLATFORM" ]; then
  DOWNLOAD_ARGS+=("--platform" "$DOWNLOAD_PLATFORM")
fi
if [ -n "$DOWNLOAD_PYTHON_VERSION" ]; then
  DOWNLOAD_ARGS+=("--python-version" "$DOWNLOAD_PYTHON_VERSION")
fi
if [ -n "$DOWNLOAD_IMPLEMENTATION" ]; then
  DOWNLOAD_ARGS+=("--implementation" "$DOWNLOAD_IMPLEMENTATION")
fi
if [ -n "$DOWNLOAD_ABI" ]; then
  DOWNLOAD_ARGS+=("--abi" "$DOWNLOAD_ABI")
fi
if [ "$DOWNLOAD_ONLY_BINARY" = true ]; then
  DOWNLOAD_ARGS+=("--only-binary" ":all:")
fi

# Download wheels/sdists (no deps) so that pip can fetch any available wheels
# for the target platform. This helps get manylinux wheels directly from PyPI.
$PYTHON -m pip download --no-deps -r "$LOCKFILE" -d "$WHEEL_DIR" "${DOWNLOAD_ARGS[@]}"

echo "Attempting to build wheels for any packages without binary distributions"
# Build wheels for packages that did not have prebuilt wheels available.
# Use --no-deps to avoid pulling additional packages beyond the lockfile.
$PYTHON -m pip wheel --no-deps -r "$LOCKFILE" -w "$WHEEL_DIR"

echo "Running strict verification"
bash tools/ci/verify_offline_artifacts.sh "$LOCKFILE" "$WHEEL_DIR"

echo "Wheelhouse build succeeded and passed verification. Wheelhouse located at: $WHEEL_DIR"
