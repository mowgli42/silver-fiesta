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
#
# NOTE: Requires NFS client tools and root/privileged access for mounting
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
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
until mount -t nfs -o "$NFS_MOUNT_OPTS" "$NFS_SOURCE" "$MOUNT_POINT"; do
  echo "Mount failed, retrying in 2 seconds..."
  sleep 2
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
    echo "Failed to mount NFS share after $MAX_RETRIES attempts." >&2
    exit 1
  fi
done

echo "Mount successful. Running tests..."
export NFS_MOUNT_POINT="$MOUNT_POINT"
export NFS_SERVER="$SERVER_HOST"
export NFS_EXPORT
export NFS_SERVER_TYPE="${NFS_SERVER_TYPE:-standalone}"

cd "$SCRIPT_DIR"
pytest -v
