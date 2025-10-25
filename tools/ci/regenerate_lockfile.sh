#!/usr/bin/env bash
# Regenerate a pip-compile lockfile for the project's requirements.
#
# This script is intended to be run on a developer machine that has
# network access and the desired Python interpreter available. It does not
# attempt to install system dependencies or run inside Docker — the project
# maintainers requested plain, repository-local tooling.
#
# Usage:
#   bash tools/ci/regenerate_lockfile.sh [--python python3.12] [--req requirements.txt] [--out lockfiles/requirements.lock-3.12]
#
# Notes:
# - Ensure `pip-tools` is installed into the desired Python environment
#   before running this script (e.g. `python3.12 -m pip install pip-tools`).
# - The script will create the output directory if it does not exist.

set -euo pipefail

PYTHON="python3.12"
REQ_FILE="requirements.txt"
OUT_FILE="lockfiles/requirements.lock-3.12"

usage() {
  cat <<USAGE
Usage: $0 [--python PYTHON_EXEC] [--req REQUIREMENTS_FILE] [--out OUTPUT_LOCKFILE]

Examples:
  bash $0 --python python3.12 --req requirements.txt --out lockfiles/requirements.lock-3.12

This script requires the `pip-compile` command (from pip-tools) to be
available in your PATH for the chosen Python interpreter.
USAGE
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --python)
      PYTHON="$2"; shift 2;;
    --req)
      REQ_FILE="$2"; shift 2;;
    --out)
      OUT_FILE="$2"; shift 2;;
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

if [ ! -f "$REQ_FILE" ]; then
  echo "ERROR: requirements file not found: $REQ_FILE" >&2
  exit 4
fi

if ! command -v pip-compile >/dev/null 2>&1; then
  echo "ERROR: 'pip-compile' not found in PATH. Install pip-tools into the desired Python environment:" >&2
  echo "  $PYTHON -m pip install pip-tools" >&2
  exit 5
fi

mkdir -p "$(dirname "$OUT_FILE")"

echo "Regenerating lockfile: $OUT_FILE (from $REQ_FILE using $PYTHON)"

# Use pip-compile with the project's recommended flags to generate a
# hash-locked file suitable for offline installs.
pip-compile --allow-unsafe --generate-hashes --no-emit-index-url --output-file="$OUT_FILE" "$REQ_FILE"

echo "Lockfile generated: $OUT_FILE"
echo "Please review and commit the new lockfile if the changes are intentional."

