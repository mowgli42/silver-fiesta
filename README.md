# NFS Container Testing Suite

This repository contains a test suite for verifying NFS functionality using Docker containers and Python `pytest`.

## Structure

- **nfs-server/**: Docker environment for the NFS server.
- **tests/**: Docker environment for the test runner (NFS client) and Python test scripts.
- **docker-compose.yml**: Orchestration to run server and tests together.

## Prerequisites

- Docker
- Docker Compose
- NFS kernel modules loaded on the host (required for both server implementations)

### Loading NFS Kernel Modules

Both NFS server implementations require the NFS kernel modules to be loaded on the Docker host. Load them with:

```bash
sudo modprobe nfs nfsd
```

To make this persistent across reboots, add to `/etc/modules-load.d/nfs.conf`:

```
nfs
nfsd
```

## Running the Tests

To run the full test suite, simply execute:

```bash
docker-compose up --build --abort-on-container-exit
```

You can also use the convenience targets:

```bash
make test
make test-kernel
make test-lightweight
```

### Server Options

You can choose between multiple NFS server implementations using Compose profiles.

```bash
# Kernel-based server (default)
docker-compose --profile kernel up --build --abort-on-container-exit

# Lightweight pre-built server
NFS_SERVER=nfs-server-lightweight NFS_SERVER_TYPE=lightweight \
  docker-compose --profile lightweight up --build --abort-on-container-exit
```

Environment variables supported by the test runner:

- `NFS_SERVER` (default: `nfs-server`)
- `NFS_SERVER_TYPE` (default: `kernel`)
- `NFS_VERSION` (default: `4`)
- `NFS_MOUNT_POINT` (default: `/mnt/nfs`)
- `NFS_MOUNT_OPTS` (default: `vers=4,proto=tcp`)
- `PERF_TESTS` (set to `1` to enable performance tests)

### Standalone Testing

To run the tests against an existing NFS server (outside Docker Compose):

```bash
./tests/standalone_test.sh <nfs-server-host>
```

This command will:
1. Build the NFS server and Client images.
2. Start the NFS server.
3. Start the Test Client (which waits for the server).
4. Mount the NFS share.
5. Run the `pytest` suite.
6. Exit with the exit code of the test runner.

## Test Coverage

- ✅ Basic File I/O (Read/Write/Append)
- ✅ Directory Operations
- ✅ Large File Handling (1MB tested)
- ⚠️ Permissions (tested, but root in containers may bypass)
- ⚠️ File Locking (tested, may be skipped if lockd unavailable)
- ✅ Concurrent Access (multi-process)
- ✅ Metadata (timestamps)
- ⚠️ Performance (optional, requires PERF_TESTS=1)

## Implementation Status

### ✅ Completed Features

- **Kernel-based NFS Server**: Alpine-based server with full NFSv4 support
- **Lightweight NFS Server**: Pre-built `erichough/nfs-server` integration
- **Test Runner**: Automated mounting, health checks, and test execution
- **Test Suite**: 10 test cases covering basic I/O, permissions, locking, concurrency, and metadata
- **Docker Compose Profiles**: Easy switching between server implementations
- **Makefile**: Convenience targets for common operations
- **Standalone Testing**: Script for testing against external NFS servers

### ⚠️ Known Limitations

- **Kernel Modules Required**: Both server implementations require NFS kernel modules on the host
- **Root Permissions**: Tests running as root may bypass permission checks
- **File Locking**: Requires `lockd`/`rpc.statd` - may not be available on all servers
- **Cleanup Issues**: NFS unmount in containers can sometimes fail (handled gracefully)
- **Performance Tests**: Disabled by default (set `PERF_TESTS=1` to enable)

### 📝 Untested Areas

The following areas are documented in code comments but not fully tested:

- Very large files (>100MB)
- Chunked/streaming I/O patterns
- Concurrent writes to the same file
- Thread-based concurrency (only process-based tested)
- Network partition scenarios
- Timestamp precision/accuracy across NFS versions
- Future/very old timestamps
- Extended attributes (xattr)
- Symbolic links and hard links
- Server load scenarios

## Troubleshooting

### Stuck Containers

If containers get stuck (especially during cleanup), you can force remove them:

```bash
docker rm -f test-runner nfs-server-lightweight nfs-server
make clean
```

### Network Errors

If you see "network not found" errors, clean up Docker resources:

```bash
docker-compose down -v --remove-orphans
docker network prune -f
```
