#!/bin/bash
set -e

# Start rpcbind if it's not running
rpcbind

# Export the file systems
exportfs -r

# Start NFS daemons
rpc.statd
rpc.nfsd --debug 8 -N 2 -N 3
rpc.mountd --debug all --no-nfs-version 2 --no-nfs-version 3 --foreground
