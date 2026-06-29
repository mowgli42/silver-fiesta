# NFS Container Testing Suite

This repository contains a test suite for verifying NFS functionality using Docker containers and Python `pytest`.

## Structure

- **nfs-server/**: Docker environment for the NFS server.
- **tests/**: Docker environment for the test runner (NFS client) and Python test scripts.
- **docker-compose.yml**: Orchestration to run server and tests together.

## NFS Export Configuration

Both NFS server implementations export the `/data` directory with `fsid=0`, which allows clients to mount the root `/` and access the exported `/data` directory. This is the standard NFSv4 approach for single-export servers.

- **Kernel server**: Exports `/data` from the container's filesystem
- **Lightweight server**: Exports `/data` from a Docker volume (`nfs-data`)
- **Client mounting**: Mounts `server:/` (root) which maps to the exported `/data` directory

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

To run the full test suite, use one of these methods:

**Recommended - Use Makefile (easiest):**
```bash
make test          # Runs with lightweight server (default, fastest)
make test-kernel   # Use kernel-based server (requires build)
make test-verbose  # Enable verbose NFS server logging (kernel recommended)
```

**Or use Docker Compose directly:**
```bash
# Default: Lightweight server
docker-compose --profile default up --build --abort-on-container-exit

# Optional: Kernel-based server (use --profile kernel)
docker-compose --profile kernel up --build --abort-on-container-exit
```

**Note:** The default configuration uses the lightweight server (pre-built image, faster startup). The kernel server is available as an optional alternative for more full-featured testing.

### Server Options

**Default: Lightweight Server** (recommended for most use cases)
- Pre-built image (`erichough/nfs-server`)
- Fast startup (no build required)
- Simple configuration
- Use: `make test` or `docker-compose --profile default up --build --abort-on-container-exit`

**Optional: Kernel-based Server** (for full-featured testing)
- Custom Alpine-based build
- More control over configuration
- Production-like setup
- Use: `make test-kernel` or `docker-compose --profile kernel up --build --abort-on-container-exit`

Environment variables supported by the test runner:

- `NFS_SERVER` (default: `nfs-server-lightweight`)
- `NFS_SERVER_TYPE` (default: `lightweight`)
- `NFS_VERSION` (default: `4`)
- `NFS_MOUNT_POINT` (default: `/mnt/nfs`)
- `NFS_MOUNT_OPTS` (default: `vers=4,proto=tcp`)

### Verbose Mode / NFS Server Logging

Both NFS servers support verbose logging to track file operations and client activity. **Verbose mode is most effective with the kernel-based server**, which provides detailed operation-level logging.

**Enable verbose mode:**
```bash
# Kernel server (recommended for verbose logging)
NFS_VERBOSE=true docker-compose --profile kernel up --build

# Lightweight server (basic logging via container logs)
NFS_VERBOSE=true docker-compose --profile default up --build

# Or use the Makefile shortcut
make test-verbose
```

**Or use log level:**
```bash
# Enable debug-level logging
NFS_LOG_LEVEL=DEBUG docker-compose --profile kernel up --build
```

**View NFS server logs:**
```bash
# View kernel server logs (follow mode - shows detailed operations)
docker logs -f nfs-server

# View lightweight server logs (follow mode)
docker logs -f nfs-server-lightweight

# View last 100 lines
docker logs --tail 100 nfs-server

# Filter for specific operations
docker logs -f nfs-server | grep -E "(open|read|write|mkdir|rmdir|stat|LOOKUP|GETATTR)"
```

**Verbose mode capabilities:**

**Kernel Server (Full Verbose Support):**
- **File operations**: OPEN, READ, WRITE, CLOSE, CREATE, REMOVE, RENAME
- **Directory operations**: MKDIR, RMDIR, READDIR, LOOKUP
- **Metadata operations**: GETATTR, SETATTR, ACCESS
- **NFS protocol operations**: RPC calls, NFSv4 compound operations, procedure details
- **Client activity**: mount/unmount events, connection tracking
- **Debug output**: Detailed daemon logs with operation parameters

**Lightweight Server (Basic Logging):**
- Server startup and configuration
- Export information
- Basic connection events
- Container-level logging (via Docker logs)

**Note:** 
- Verbose mode is automatically enabled for fault testing scenarios to aid in debugging
- Verbose logging may impact performance slightly due to increased I/O
- For production-like testing, use normal mode (`NFS_VERBOSE=false` or omit the variable)
- Kernel server provides more detailed operation-level logging than the lightweight server
- `PERF_TESTS` (legacy - performance tests now run by default)

### Test Execution Tracking

The test runner prints the currently executing test in real time:

```
================================================================================
Running test: test_basic_io::test_file_create_read_write
================================================================================
... test output ...
[TEST COMPLETE] test_basic_io::test_file_create_read_write: PASSED (0.123s)
```

This helps track progress during long runs and identify the active test if execution hangs.

### Standalone Testing

To run the tests against an existing NFS server (outside Docker Compose):

```bash
# Default export (host:/)
sudo ./tests/standalone_test.sh 192.168.50.51

# Specific export path
sudo ./tests/standalone_test.sh 192.168.50.51:/mnt/Externalssd/NFS-Share

# Or via environment variables
sudo NFS_SERVER=192.168.50.51 NFS_EXPORT=/mnt/Externalssd/NFS-Share ./tests/standalone_test.sh
```

This command will:
1. Mount the NFS share at `NFS_MOUNT_POINT` (default `/tmp/nfs_test_mount`).
2. Run the `pytest` suite against that mount.
3. Unmount and exit with the test runner's exit code.

Mount options can be overridden with `NFS_VERSION` or `NFS_MOUNT_OPTS` (defaults: `vers=4,proto=tcp`).

## Test Coverage

- ✅ Basic File I/O (Read/Write/Append)
- ✅ Directory Operations
- ✅ Large File Handling (1MB tested)
- ✅ Data Integrity (CRC32 verification across multiple sizes and patterns)
- ⚠️ Permissions (tested, but root in containers may bypass)
- ⚠️ File Locking (tested, may be skipped if lockd unavailable)
- ✅ Concurrent Access (multi-process)
- ✅ Metadata (timestamps)
- ✅ Performance & Throughput (write/read throughput, latency measurements; enabled by default)
- ✅ Off-Nominal Testing (network faults, NFS misconfigs, server/resource faults)

**Total: 64+ test cases** covering comprehensive NFS functionality and fault scenarios.

## Implementation Status

### ✅ Completed Features

- **Default: Lightweight NFS Server**: Pre-built `erichough/nfs-server` integration (fast, no build required)
- **Optional: Kernel-based NFS Server**: Alpine-based server with full NFSv4 support (use `--profile kernel`)
- **Test Runner**: Automated mounting, health checks, and test execution with comprehensive reporting
- **Test Suite**: 64+ test cases covering basic I/O, data integrity, permissions, locking, concurrency, metadata, performance, and off-nominal faults
- **Comprehensive Reports**: 
  - **Text Reports**: Detailed test execution with full output
  - **HTML Reports**: Interactive, self-contained HTML reports with test results
  - **JSON Reports**: Machine-readable format for programmatic analysis
  - **Performance Reports**: Detailed throughput and latency metrics
  - **Summary Reports**: Executive summary with key metrics and test counts
- **Diagnosis Reports**: Automated failure analysis for fault scenarios
- **Test Execution Tracking**: Real-time display of running tests via pytest hooks
- **Debug Logging**: Debug logs included in full reports, filtered from summaries
- **Docker Compose**: Default profile for lightweight server (`--profile default`)
- **Makefile**: Convenience targets for common operations
- **Standalone Testing**: Script for testing against external NFS servers

### ⚠️ Known Limitations

- **Kernel Modules Required**: Both server implementations require NFS kernel modules on the host
- **Root Permissions**: Tests running as root may bypass permission checks
- **File Locking**: Requires `lockd`/`rpc.statd` - may not be available on all servers
- **Cleanup Issues**: NFS unmount in containers can sometimes fail (handled gracefully)
- **Performance Tests**: Run by default with standard file sizes (1MB, 5MB, 10MB)
- **Verbose Logging**: Adds noise to logs and may impact performance slightly

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

If you see "network not found" errors (e.g., `network ... not found`), this is usually due to Docker's internal state being inconsistent. Clean up Docker resources:

```bash
# Clean up everything
make clean

# Or manually:
docker-compose down -v --remove-orphans
docker network prune -f
docker rm -f $(docker ps -aq --filter "name=test-runner") $(docker ps -aq --filter "name=nfs-server") 2>/dev/null || true
```

Then try running the tests again.

## Off-Nominal Testing (Fault Injection)

The test suite includes comprehensive fault injection capabilities to verify that failures are properly detected and diagnosed. Fault scenarios are opt-in and do not affect normal test runs.

### Network Fault Scenarios

#### Docker-Native Network Faults (Recommended)

Network faults are injected using `tc netem` in a sidecar container:

**Packet Loss (10%)**
```bash
FAULT_PROFILE=network_loss_10 docker-compose --profile faults up --build --abort-on-container-exit
```
- **Expected**: Degraded throughput, slower test execution, retransmissions
- **Detection**: 
  - `test_network_loss_detection` should PASS (verifies throughput < 200 MB/s)
  - Test execution time increases significantly (e.g., 11+ seconds for 10MB write)
  - Performance tests show reduced throughput
- **Verification**: 
  - Check netem logs: `docker logs netem` should show "qdisc netem ... loss 10%"
  - Check test report: Network loss test should pass, indicating throughput degradation detected
  - Compare performance metrics: Throughput should be noticeably lower than baseline
- **Report**: Look for "Network fault detected" in diagnosis section, throughput metrics in performance report

**High Latency (200ms + jitter)**
```bash
FAULT_PROFILE=network_latency_200 docker-compose --profile faults up --build --abort-on-container-exit
```
- **Expected**: Slow test execution, timeout warnings
- **Detection**: Test durations exceed normal thresholds
- **Report**: Performance deltas show significant slowdown

**Network Blackhole (Port 2049 blocked)**
```bash
FAULT_PROFILE=network_blackhole docker-compose --profile faults up --build --abort-on-container-exit
```
- **Expected**: Mount failures, connection refused errors
- **Detection**: Mount timeout or "Connection refused" errors
- **Report**: Failure diagnosis indicates network connectivity issue

#### Host-Level Network Faults

For testing against existing NFS servers or when Docker-native injection isn't suitable:

```bash
# Apply network fault
sudo faults/host_netem.sh apply network_loss_10

# Run normal tests (fault is active)
make test

# Clear fault
sudo faults/host_netem.sh clear
```

**Available host-level profiles:**
- `network_loss_10` - 10% packet loss
- `network_latency_200` - 200ms latency + 50ms jitter
- `network_blackhole` - Block port 2049

### NFS Misconfiguration Scenarios

Test how the suite handles server misconfigurations:

**Read-Only Export**
```bash
FAULT_PROFILE=nfs_ro_export FAULT_EXPORTS=exports_ro \
  docker-compose --profile faults up --build --abort-on-container-exit
```
- **Expected**: Write operations fail with `PermissionError`
- **Detection**: Tests expecting write access should fail appropriately
- **Report**: Diagnosis indicates "Read-only filesystem" or permission denied

**Invalid Export Path**
```bash
FAULT_PROFILE=nfs_badpath FAULT_EXPORTS=exports_badpath \
  docker-compose --profile faults up --build --abort-on-container-exit
```
- **Expected**: Mount fails with "No such file or directory"
- **Detection**: Mount operation fails before tests run
- **Report**: Failure diagnosis shows export path issue

**Root Squash Enabled**
```bash
FAULT_PROFILE=nfs_root_squash FAULT_EXPORTS=exports_root_squash \
  docker-compose --profile faults up --build --abort-on-container-exit
```
- **Expected**: Permission tests may behave differently
- **Detection**: Permission-related tests may skip or fail
- **Report**: Diagnosis notes root_squash configuration

### Interpreting Fault Test Results

When running fault scenarios, check the reports for:

1. **Fault Profile Information**: Report header shows which fault was active
2. **Expected vs Actual Failures**: Summary shows if failures matched expectations
3. **Failure Diagnosis**: `diagnose_failures.py` provides root cause analysis
4. **Performance Impact**: Compare throughput/latency to baseline runs

**Example Report Output:**
```
==========================================
NFS SERVER PERFORMANCE TEST SUMMARY
==========================================
Fault Profile: network_loss_10
Fault Class: network
Expected Failures: 5-10
Actual Failures: 8
...
----------------------------------------
FAILURE DIAGNOSIS
----------------------------------------
Network Issues Detected:
  - Timeout errors: 3 occurrences
  - I/O errors: 5 occurrences
  - Degraded throughput: 45% below baseline

Suspected Root Cause: Packet loss causing retransmissions
Recommendation: Check network stability, reduce packet loss
```

### Available Fault Profiles

| Profile | Type | Description | Expected Impact |
|---------|------|-------------|-----------------|
| `network_loss_10` | Network | 10% packet loss | Timeouts, I/O errors |
| `network_latency_200` | Network | 200ms latency + jitter | Slow execution |
| `network_blackhole` | Network | Block port 2049 | Mount failures |
| `nfs_ro_export` | NFS Config | Read-only export | Write failures |
| `nfs_badpath` | NFS Config | Invalid export path | Mount failures |
| `nfs_root_squash` | NFS Config | Root squash enabled | Permission issues |

### Running Multiple Fault Scenarios

To test multiple scenarios in sequence:

```bash
# Test network faults
for profile in network_loss_10 network_latency_200 network_blackhole; do
  echo "Testing $profile..."
  FAULT_PROFILE=$profile docker-compose --profile faults up --build --abort-on-container-exit
  docker-compose --profile faults down
done

# Test NFS misconfigs
for profile in nfs_ro_export nfs_badpath nfs_root_squash; do
  echo "Testing $profile..."
  FAULT_PROFILE=$profile FAULT_EXPORTS=exports_${profile#nfs_} \
    docker-compose --profile faults up --build --abort-on-container-exit
  docker-compose --profile faults down
done
```

## Test Reports

After running tests, comprehensive reports are generated in the `tests/reports/` directory:

### Report Files Generated

1. **`<timestamp>-<server-type>.txt`** - Detailed text report with full test output
2. **`<timestamp>-<server-type>.html`** - Interactive HTML report (open in browser)
3. **`<timestamp>-<server-type>.json`** - Machine-readable JSON format
4. **`<timestamp>-<server-type>-summary.txt`** - Executive summary with key metrics
5. **`<timestamp>-<server-type>-performance.txt`** - Detailed performance analysis
6. **`<timestamp>-<server-type>-diagnosis.txt`** - Failure diagnosis for fault scenarios

### Report Contents

- **Complete test list**: Every test that ran with its outcome (PASSED/FAILED/SKIPPED)
- **Performance metrics**: Throughput (MB/s), latency (ms), duration for each test
- **Test durations**: Sorted list showing slowest tests first
- **Summary statistics**: Total tests, pass/fail counts, execution time
- **Performance measurements**: Write/read throughput for different file sizes
- **Data integrity results**: CRC32 verification results for all test patterns
- **Test execution tracking**: Real-time test start/complete lines in full report

The full text report includes debug logs and per-test execution banners. The summary report filters out debug lines for clarity.

### Viewing Reports

```bash
# View HTML report (recommended)
open tests/reports/<timestamp>-<server-type>.html

# View summary
cat tests/reports/<timestamp>-<server-type>-summary.txt

# View performance analysis
cat tests/reports/<timestamp>-<server-type>-performance.txt
```
