#!/bin/bash
# Standalone test runner for testing against an existing NFS server
# Usage: ./standalone_test.sh <nfs-server-host>
# NOTE: Requires NFS client tools and root/privileged access for mounting
set -e

SERVER_HOST="${1:-${NFS_SERVER:-localhost}}"
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
echo "Mounting NFS share from $SERVER_HOST:/ with options: $NFS_MOUNT_OPTS"
mount -t nfs -o "$NFS_MOUNT_OPTS" "$SERVER_HOST":/ "$MOUNT_POINT"

export NFS_MOUNT_POINT="$MOUNT_POINT"
pytest -v

