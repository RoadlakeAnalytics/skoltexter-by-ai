#!/usr/bin/env bash
set -euo pipefail

# Simple, reusable Harden Runner verification script.
#
# This script performs a lightweight connectivity check against one or more
# endpoints. If the quick checks succeed the script exits 0. If any endpoint
# fails the script runs a set of verbose diagnostics (DNS resolution, curl -Iv,
# network stack info) and exits non-zero. The intent is to only produce noisy
# logs when a verification failure occurs.

TRIES=3
DELAY=2
CURL_TIMEOUT=8
DISALLOWED="https://example.com"

usage() {
  cat <<USAGE
Usage: $0 [--tries N] [--delay N] [--timeout N] [endpoint ...]

If no endpoints are provided the default endpoints
https://api.github.com https://raw.githubusercontent.com https://codeload.github.com
are used.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tries)
      TRIES="$2"
      shift 2
      ;;
    --delay)
      DELAY="$2"
      shift 2
      ;;
    --timeout)
      CURL_TIMEOUT="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [ $# -eq 0 ]; then
  ENDPOINTS=(
    "https://api.github.com"
    "https://raw.githubusercontent.com"
    "https://codeload.github.com"
  )
else
  ENDPOINTS=("$@")
fi

failures=()

for u in "${ENDPOINTS[@]}"; do
  ok=0
  i=1
  while [ $i -le "$TRIES" ]; do
    if curl -sS --max-time "$CURL_TIMEOUT" -I "$u" >/dev/null 2>&1; then
      ok=1
      break
    fi
    echo "WARN: cannot reach $u (attempt $i/$TRIES), sleeping $DELAY" >&2
    sleep "$DELAY"
    i=$((i + 1))
  done
  if [ "$ok" -ne 1 ]; then
    failures+=("$u")
  fi
done

if [ ${#failures[@]} -eq 0 ]; then
  # Quick sanity check that clearly-disallowed host is unreachable.
  if curl -sS --max-time "$CURL_TIMEOUT" -I "$DISALLOWED" >/dev/null 2>&1; then
    echo "ERROR: disallowed host reachable (policy not applied)" >&2
    exit 1
  fi
  echo "OK: Harden runner verification passed"
  exit 0
fi

echo "ERROR: Harden runner verification failed for: ${failures[*]}" >&2
echo "Collecting diagnostics for failed endpoints..." >&2

command -v python3 >/dev/null 2>&1 || { echo "warning: python3 not available, DNS diagnostics limited" >&2; }
command -v getent >/dev/null 2>&1 || true

for u in "${failures[@]}"; do
  host="${u#*://}"
  host="${host%%/*}"
  echo "===== DIAGNOSTICS for $u ====="

  echo "--- /etc/resolv.conf ---"
  if [ -r /etc/resolv.conf ]; then
    sed -n '1,200p' /etc/resolv.conf || true
  else
    echo "(no /etc/resolv.conf)"
  fi

  echo "--- getent hosts $host ---"
  getent hosts "$host" 2>&1 || true

  if command -v python3 >/dev/null 2>&1; then
    echo "--- python3 socket.getaddrinfo($host, 443) ---"
    python3 - <<PY || true
import socket
host = "$host"
try:
    infos = socket.getaddrinfo(host, 443)
    for i in infos:
        print(i)
except Exception as e:
    print('getaddrinfo failed:', e)
PY
  fi

  echo "--- curl -Iv $u ---"
  curl -Iv --max-time $((CURL_TIMEOUT * 2)) "$u" 2>&1 | sed 's/^/    /' || true

  if command -v ip >/dev/null 2>&1; then
    echo "--- ip -4 route ---"
    ip -4 route 2>&1 | sed 's/^/    /' || true
    echo "--- ip -6 route ---"
    ip -6 route 2>&1 | sed 's/^/    /' || true
    echo "--- ip addr ---"
    ip addr 2>&1 | sed 's/^/    /' || true
  else
    echo "(ip command not found)"
  fi

  if command -v ss >/dev/null 2>&1; then
    echo "--- ss -tn ---"
    ss -tn 2>&1 | sed 's/^/    /' || true
  fi

  echo "----- end diagnostics for $u -----"
done

exit 1

