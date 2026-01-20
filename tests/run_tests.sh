#!/bin/bash
# Exit on error, but allow cleanup to run even if tests fail
# Use pipefail to catch errors in pipelines (like tee)
set -e -o pipefail

SERVER_HOST="${NFS_SERVER:-nfs-server}"
MOUNT_POINT="${NFS_MOUNT_POINT:-/mnt/nfs}"
NFS_VERSION="${NFS_VERSION:-4}"
NFS_MOUNT_OPTS="${NFS_MOUNT_OPTS:-vers=${NFS_VERSION},proto=tcp}"
PYTEST_ARGS="${PYTEST_ARGS:--v}"

# Track test exit code
TEST_EXIT_CODE=0

cleanup() {
  # Don't fail on cleanup errors - NFS unmount can be problematic in containers
  set +e
  if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "Unmounting $MOUNT_POINT..."
    # Try regular unmount first, then lazy unmount if that fails
    # Lazy unmount detaches immediately even if files are in use
    umount "$MOUNT_POINT" 2>/dev/null || umount -l "$MOUNT_POINT" 2>/dev/null || true
  fi
  set -e
}

check_nfs_ready() {
  timeout 1 bash -c "cat < /dev/null > /dev/tcp/${SERVER_HOST}/2049" 2>/dev/null
}

trap cleanup EXIT

echo "Waiting for NFS server ($SERVER_HOST) to be reachable..."
until ping -c 1 "$SERVER_HOST" &> /dev/null; do
  echo "waiting for $SERVER_HOST..."
  sleep 1
done

echo "Waiting for NFS service to be ready..."
until check_nfs_ready; do
  echo "NFS port not ready, waiting..."
  sleep 2
done

echo "Mounting NFS share from $SERVER_HOST:/ with options: $NFS_MOUNT_OPTS"
# Retry mount loop
MAX_RETRIES=10
COUNT=0
until mount -t nfs -o "$NFS_MOUNT_OPTS" "$SERVER_HOST":/ "$MOUNT_POINT"; do
  echo "Mount failed, retrying in 2 seconds..."
  sleep 2
  COUNT=$((COUNT+1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "Failed to mount NFS share after $MAX_RETRIES attempts."
    exit 1
  fi
done

echo "Mount successful. Running tests..."
export NFS_MOUNT_POINT="$MOUNT_POINT"

# Report generation setup
REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SYSTEM_TESTED="${NFS_SERVER_TYPE:-nfs-server}"
REPORT_FILE="$REPORT_DIR/${TIMESTAMP}-${SYSTEM_TESTED}.txt"

echo "Generating test report at: $REPORT_FILE"

# Run pytest and capture output to file and stdout
# Temporarily disable exit on error to capture exit code
set +e
# Use PIPESTATUS to capture the actual pytest exit code (not tee's exit code)
# -v: verbose (show each test name)
# -s: show stdout (don't capture)
# -rA: show extra test summary info for all tests
# --durations=0: show durations for all tests (0 means all, not just slowest)
# If PYTEST_ARGS is set, use it; otherwise use the detailed flags
if [ -n "$PYTEST_ARGS" ] && [ "$PYTEST_ARGS" != "-v" ]; then
    pytest $PYTEST_ARGS 2>&1 | tee "$REPORT_FILE"
else
    pytest -v -s -rA --durations=0 2>&1 | tee "$REPORT_FILE"
fi

# Capture the exit code from pytest (first command in the pipe)
TEST_EXIT_CODE=${PIPESTATUS[0]}
set -e

echo "Tests completed with exit code: $TEST_EXIT_CODE"
exit $TEST_EXIT_CODE
