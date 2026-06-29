#!/bin/bash
# Standalone test runner for testing against an existing NFS server
#
# Usage: ./standalone_test.sh [host[:/export-path]]
#   host              mount host:/ (default export)
#   host:/export      mount a specific export path
#
# Environment:
#   NFS_SERVER        server host, or host:/export if no argument is given
#   NFS_EXPORT        export path when NFS_SERVER is host-only (default: /)
#   NFS_MOUNT_POINT   local mount point (default: /tmp/nfs_test_mount)
#   NFS_VERSION       NFS protocol version (default: 4)
#   NFS_MOUNT_OPTS    mount options (default: vers=$NFS_VERSION,proto=tcp)
#   PYTEST            pytest executable (default: auto-detect .venv/bin/pytest)
#
# NOTE: Requires NFS client tools and root/privileged access for mounting
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

is_root() {
  [[ "$(id -u)" -eq 0 ]]
}

print_sudo_hint() {
  local quoted_args=""
  local arg
  for arg in "$@"; do
    quoted_args+=" $(printf '%q' "$arg")"
  done

  echo "" >&2
  echo "Error: mounting NFS requires root privileges." >&2
  echo "Re-run with sudo, for example:" >&2
  echo "  sudo -E env PATH=\"\$PATH\"$quoted_args" >&2
  echo "" >&2
  echo "If you use a virtualenv for pytest, -E keeps PATH so sudo can find it." >&2
  echo "The script also auto-detects $REPO_ROOT/.venv/bin/pytest when present." >&2
}

resolve_pytest() {
  if [[ -n "${PYTEST:-}" ]]; then
    if [[ -x "$PYTEST" ]] || command -v "$PYTEST" >/dev/null 2>&1; then
      echo "$PYTEST"
      return 0
    fi
    echo "Error: PYTEST is set but not executable: $PYTEST" >&2
    return 1
  fi

  if [[ -x "$REPO_ROOT/.venv/bin/pytest" ]]; then
    echo "$REPO_ROOT/.venv/bin/pytest"
    return 0
  fi

  if command -v pytest >/dev/null 2>&1; then
    command -v pytest
    return 0
  fi

  if command -v python3 >/dev/null 2>&1 && python3 -m pytest --version >/dev/null 2>&1; then
    echo "python3 -m pytest"
    return 0
  fi

  echo "Error: pytest not found." >&2
  echo "Install test dependencies in a virtualenv:" >&2
  echo "  cd $REPO_ROOT" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/pip install -r tests/requirements.txt" >&2
  echo "" >&2
  echo "Then re-run this script (sudo is fine; .venv pytest will be auto-detected)." >&2
  return 1
}

run_pytest() {
  local pytest_cmd="$1"
  shift
  if [[ "$pytest_cmd" == "python3 -m pytest" ]]; then
    python3 -m pytest "$@"
  else
    "$pytest_cmd" "$@"
  fi
}

list_server_exports() {
  if ! command -v showmount >/dev/null 2>&1; then
    echo "Note: showmount not found (install nfs-common). Skipping export discovery." >&2
    return 1
  fi

  echo "Querying NFS exports on $SERVER_HOST..."
  local showmount_output showmount_status
  if showmount_output="$(showmount -e "$SERVER_HOST" 2>&1)"; then
    echo "$showmount_output"
    AVAILABLE_EXPORTS=()
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      [[ "$line" == Export\ list\ for* ]] && continue
      AVAILABLE_EXPORTS+=("${line%% *}")
    done <<< "$showmount_output"
    return 0
  fi

  showmount_status=$?
  echo "Could not list exports from $SERVER_HOST (showmount exit $showmount_status)." >&2
  echo "$showmount_output" >&2
  echo "Continuing without export validation." >&2
  return 1
}

validate_export_path() {
  [[ "${#AVAILABLE_EXPORTS[@]}" -eq 0 ]] && return 0

  local export_path
  for export_path in "${AVAILABLE_EXPORTS[@]}"; do
    if [[ "$export_path" == "$NFS_EXPORT" ]]; then
      return 0
    fi
  done

  echo "" >&2
  echo "Warning: export $NFS_EXPORT was not found in the server's export list." >&2
  echo "Available exports:" >&2
  for export_path in "${AVAILABLE_EXPORTS[@]}"; do
    echo "  - $export_path" >&2
  done

  local first_export="${AVAILABLE_EXPORTS[0]}"
  if [[ -n "$first_export" ]]; then
    echo "" >&2
    echo "Try:" >&2
    echo "  sudo -E env PATH=\"\$PATH\" $0 ${SERVER_HOST}:${first_export}" >&2
  fi
  echo "" >&2
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage 0
fi

SERVER_SPEC="${1:-${NFS_SERVER:-}}"
if [[ -z "$SERVER_SPEC" ]]; then
  echo "Error: NFS server not specified." >&2
  echo "Provide host[:/export] as an argument or set NFS_SERVER." >&2
  usage 1
fi

if [[ "$SERVER_SPEC" == *:* ]]; then
  SERVER_HOST="${SERVER_SPEC%%:*}"
  NFS_EXPORT="${NFS_EXPORT:-${SERVER_SPEC#*:}}"
else
  SERVER_HOST="$SERVER_SPEC"
  NFS_EXPORT="${NFS_EXPORT:-/}"
fi

if [[ "$NFS_EXPORT" != /* ]]; then
  NFS_EXPORT="/${NFS_EXPORT}"
fi

NFS_SOURCE="${SERVER_HOST}:${NFS_EXPORT}"
MOUNT_POINT="${NFS_MOUNT_POINT:-/tmp/nfs_test_mount}"
NFS_VERSION="${NFS_VERSION:-4}"
NFS_MOUNT_OPTS="${NFS_MOUNT_OPTS:-vers=${NFS_VERSION},proto=tcp}"
AVAILABLE_EXPORTS=()
if [[ $# -gt 0 ]]; then
  INVOCATION_ARGS=("$@")
else
  INVOCATION_ARGS=("${SERVER_HOST}:${NFS_EXPORT}")
fi

list_server_exports || true
validate_export_path

if ! is_root; then
  echo "Note: not running as root. NFS mount will likely fail without sudo." >&2
fi

cleanup() {
  if mountpoint -q "$MOUNT_POINT"; then
    umount "$MOUNT_POINT" || true
  fi
}

trap cleanup EXIT

mkdir -p "$MOUNT_POINT"
echo "Mounting NFS share $NFS_SOURCE with options: $NFS_MOUNT_OPTS"

MAX_RETRIES=10
COUNT=0
while true; do
  MOUNT_ERR=""
  if MOUNT_ERR="$(mount -t nfs -o "$NFS_MOUNT_OPTS" "$NFS_SOURCE" "$MOUNT_POINT" 2>&1)"; then
    break
  fi

  echo "$MOUNT_ERR" >&2

  if ! is_root; then
    print_sudo_hint "$0" "${INVOCATION_ARGS[@]}"
    exit 1
  fi

  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
    echo "Failed to mount NFS share after $MAX_RETRIES attempts." >&2
    if [[ "${#AVAILABLE_EXPORTS[@]}" -gt 0 ]]; then
      echo "Server exports were:" >&2
      for export_path in "${AVAILABLE_EXPORTS[@]}"; do
        echo "  - $export_path" >&2
      done
    fi
    echo "Try a different NFS_VERSION or NFS_MOUNT_OPTS if the export path is correct." >&2
    exit 1
  fi

  echo "Mount failed, retrying in 2 seconds..."
  sleep 2
done

echo "Mount successful. Running tests..."
export NFS_MOUNT_POINT="$MOUNT_POINT"
export NFS_SERVER="$SERVER_HOST"
export NFS_EXPORT
export NFS_SERVER_TYPE="${NFS_SERVER_TYPE:-standalone}"

PYTEST_CMD="$(resolve_pytest)"
echo "Running tests with: $PYTEST_CMD"

cd "$SCRIPT_DIR"
run_pytest "$PYTEST_CMD" -v
