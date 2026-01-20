#!/bin/bash
set -e

SERVER_HOST="nfs-server"
MOUNT_POINT="/mnt/nfs"

echo "Waiting for NFS server ($SERVER_HOST) to be reachable..."
until ping -c 1 "$SERVER_HOST" &> /dev/null; do
  echo "waiting for $SERVER_HOST..."
  sleep 1
done

echo "Mounting NFS share from $SERVER_HOST:/"
# Retry mount loop
MAX_RETRIES=10
COUNT=0
until mount -t nfs -o vers=4,nolock,proto=tcp "$SERVER_HOST":/ "$MOUNT_POINT"; do
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
pytest -v

echo "Tests completed."
