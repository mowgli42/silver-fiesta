#!/bin/bash
set -e

# Verbose mode configuration
NFS_VERBOSE="${NFS_VERBOSE:-false}"
NFS_LOG_LEVEL="${NFS_LOG_LEVEL:-INFO}"

# Start rpcbind if it's not running
rpcbind

# Export the file systems
exportfs -r

# Start NFS daemons
rpc.statd

# Start nfsd - run in background
# Note: Alpine's nfs-utils supports NFSv4 by default
# Add verbose flag if enabled
if [ "$NFS_VERBOSE" = "true" ] || [ "$NFS_LOG_LEVEL" = "DEBUG" ]; then
    echo "Starting NFS server in verbose mode..."
    echo "Verbose logging will show: file operations, client connections, protocol details"
    # Enable kernel NFS debugging (requires sysctl)
    # Note: Some debug options require kernel support
    rpc.nfsd -V 4 -d 8 2>&1 | tee -a /var/log/nfs-verbose.log &
    NFSD_PID=$!
    echo "NFS daemon started with verbose logging (PID: $NFSD_PID)"
else
    rpc.nfsd
fi

# Start mountd in foreground to keep container running
# Add verbose flag if enabled
if [ "$NFS_VERBOSE" = "true" ] || [ "$NFS_LOG_LEVEL" = "DEBUG" ]; then
    rpc.mountd --foreground -d all  # -d all = debug all operations
else
    rpc.mountd --foreground
fi
MOUNTD_PID=$!

# Basic readiness check for NFSv4
# NOTE: This is a simple readiness check. Does not verify:
# - All required RPC services are running
# - Exports are properly configured
# - Network connectivity from clients
if command -v rpcinfo >/dev/null 2>&1; then
  for i in $(seq 1 10); do
    if rpcinfo -t localhost nfs 4 >/dev/null 2>&1; then
      if [ "$NFS_VERBOSE" = "true" ] || [ "$NFS_LOG_LEVEL" = "DEBUG" ]; then
        echo "NFS server is ready (verbose mode enabled)."
        echo "Monitoring NFS operations..."
      else
        echo "NFS server is ready."
      fi
      break
    fi
    echo "Waiting for NFS server to be ready..."
    sleep 1
  done
fi

# In verbose mode, also enable exportfs monitoring and activity tracking
if [ "$NFS_VERBOSE" = "true" ] || [ "$NFS_LOG_LEVEL" = "DEBUG" ]; then
    echo "Verbose logging enabled. NFS operations will be logged."
    echo "To view detailed logs, check container logs: docker logs nfs-server"
    echo ""
    echo "Monitoring NFS activity..."
    # Create a log file for verbose output
    mkdir -p /var/log
    touch /var/log/nfs-verbose.log
    # Show current exports in verbose mode
    echo "Current NFS exports:"
    exportfs -v
    echo ""
    # Enable RPC debugging if available
    if command -v rpcdebug >/dev/null 2>&1; then
        echo "Enabling RPC debugging..."
        rpcdebug -m nfsd -s all 2>/dev/null || echo "Note: RPC debugging may require additional privileges"
    fi
fi

wait "$MOUNTD_PID"
