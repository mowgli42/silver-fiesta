#!/bin/bash
set -e

# Start rpcbind if it's not running
rpcbind

# Export the file systems
exportfs -r

# Start NFS daemons
rpc.statd

# Start nfsd - run in background
# Note: Alpine's nfs-utils supports NFSv4 by default
rpc.nfsd

# Start mountd in foreground to keep container running
rpc.mountd --foreground
MOUNTD_PID=$!

# Basic readiness check for NFSv4
# NOTE: This is a simple readiness check. Does not verify:
# - All required RPC services are running
# - Exports are properly configured
# - Network connectivity from clients
if command -v rpcinfo >/dev/null 2>&1; then
  for i in $(seq 1 10); do
    if rpcinfo -t localhost nfs 4 >/dev/null 2>&1; then
      echo "NFS server is ready."
      break
    fi
    echo "Waiting for NFS server to be ready..."
    sleep 1
  done
fi

wait "$MOUNTD_PID"
