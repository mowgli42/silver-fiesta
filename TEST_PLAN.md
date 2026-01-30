# NFS Container Testing Plan

## Overview
This document outlines the implementation and testing strategy for NFS (Network File System) using Docker containers and Python. The goal is to verify NFS functionality, reliability, and performance in a containerized environment.

## Status: ✅ IMPLEMENTED

All planned features have been implemented. The tool is ready for testing NFS servers and generating detailed reports.

## Architecture

The testing infrastructure consists of two main components running as Docker containers:

1.  **NFS Server Container**: Exports a directory using NFSv4.
2.  **NFS Client/Test Container**: Mounts the exported directory and runs Python-based tests.

We use `docker-compose` to orchestrate these containers.

## Components

### 1. NFS Server (Default: Lightweight)

**Default Implementation (Lightweight Server)**:
- **Image**: `erichough/nfs-server` (pre-built, no build required)
- **Configuration**: Exports `/data` with `fsid=0` for root mounting
- **Advantages**: Fast startup, simple configuration, well-maintained
- **Requirements**: NFS kernel modules on host, privileged mode

**Optional Implementation (Kernel Server)**:
- **Base Image**: Alpine Linux
- **Software**: `nfs-utils` (kernel-based NFS server)
- **Configuration**: Export `/data` with RW access via `/etc/exports`
- **Advantages**: Full-featured, production-like, more control
- **Requirements**: NFS kernel modules on host, privileged mode, build time
- **Usage**: Use `--profile kernel` to enable

### 2. NFS Client (Test Runner)
- **Base Image**: Python 3.9+ (Slim Debian)
- **Software**: `nfs-common`, `pytest`, `iputils-ping`
- **Mount Point**: `/mnt/nfs` (configurable via `NFS_MOUNT_POINT`)
- **Role**: 
  - Waits for server to be reachable (ping)
  - Waits for NFS service on port 2049
  - Mounts the NFS share with retry logic
  - Executes pytest test suites
  - Generates detailed test reports
  - Handles cleanup (unmount) gracefully

## Test Strategy

The tests are written in Python using `pytest` with comprehensive coverage.

### Test Categories (✅ Implemented)

1.  **Basic I/O Operations** (`test_basic_io.py`)
    - ✅ File creation, writing, and reading
    - ✅ File appending
    - ✅ Directory operations (create, remove, nested)
    - ✅ Large file I/O (1MB tested)

2.  **Advanced Features** (`test_advanced.py`)
    - ✅ Permission changes (`chmod`) - may be bypassed as root
    - ✅ File locking (`fcntl.flock`) - requires lockd support

3.  **Concurrency** (`test_concurrent.py`)
    - ✅ Multi-process concurrent writes to different files

4.  **Metadata** (`test_metadata.py`)
    - ✅ Timestamp updates (`mtime`)
    - ✅ Timestamp setting (`utime`)

5.  **Performance** (`test_performance.py`)
    - ✅ Throughput and latency tests (enabled by default)

6.  **Data Integrity** (`test_data_integrity.py`)
    - ✅ CRC32 verification across multiple sizes and patterns (parametrized)

7.  **Off-Nominal Testing** (`test_off_nominal_*.py`)
    - ✅ Network faults (latency, loss)
    - ✅ NFS misconfigurations (read-only, bad path, root_squash)
    - ✅ Server faults (restart detection)
    - ✅ Resource faults (disk full, inode exhaustion)

### Test Counts (Approximate)

- Basic I/O: 4 tests
- Advanced: 2 tests
- Concurrency: 1 test
- Metadata: 2 tests
- Performance: 4 tests (parametrized)
- Data Integrity: 40 tests (8 sizes × 5 patterns)
- Off-Nominal: 6 tests
- **Total**: ~64 test cases

### Test Execution & Reporting

- **Automatic Report Generation**: Test reports are saved to `tests/reports/` directory with timestamps
- **Report Types**: Text, HTML, JSON, summary, performance, and diagnosis reports
- **Test Execution Tracking**: Real-time display of the currently running test
- **Debug Logging**: Debug logs included in full reports, filtered from summaries
- **Exit Codes**: Properly propagated for CI/CD integration
- **Test Isolation**: Each test gets its own temporary directory on the NFS share

## Implementation Status

### ✅ Completed

1.  **Infrastructure Setup**:
    - ✅ `nfs-server/Dockerfile` and `exports` config (kernel server)
    - ✅ `nfs-server-lightweight/` configuration (default server)
    - ✅ `tests/Dockerfile` with Python and NFS client tools
    - ✅ `docker-compose.yml` with profiles for server selection
    - ✅ `Makefile` for convenient test execution

2.  **Test Development**:
    - ✅ `tests/conftest.py`: Fixtures for setup/teardown
    - ✅ `tests/test_basic_io.py`: Basic CRUD operations (4 tests)
    - ✅ `tests/test_advanced.py`: Permissions and locking (2 tests)
    - ✅ `tests/test_concurrent.py`: Concurrent access (1 test)
    - ✅ `tests/test_metadata.py`: Timestamps (2 tests)
    - ✅ `tests/test_performance.py`: Performance tests (4 tests, enabled by default)
    - ✅ `tests/test_data_integrity.py`: Data integrity tests (parametrized)
    - ✅ `tests/test_off_nominal_network.py`: Network fault tests
    - ✅ `tests/test_off_nominal_nfs.py`: NFS misconfig tests
    - ✅ `tests/test_off_nominal_server.py`: Server fault tests
    - ✅ `tests/test_off_nominal_resource.py`: Resource fault tests
    - ✅ `tests/run_tests.sh`: Automated test runner with health checks and reporting
    - ✅ `tests/generate_performance_report.py`: Performance report generation
    - ✅ `tests/diagnose_failures.py`: Failure diagnosis for off-nominal runs
    - ✅ `tests/standalone_test.sh`: Standalone testing script

3.  **Execution**:
    - ✅ Default: `make test` or `docker-compose --profile default up --build --abort-on-container-exit`
    - ✅ Kernel server: `make test-kernel` or `docker-compose --profile kernel up --build --abort-on-container-exit`
    - ✅ Verbose logging: `make test-verbose` or `NFS_VERBOSE=true ...`
    - ✅ Standalone: `./tests/standalone_test.sh <server-host>`

## Directory Structure

```
.
├── docker-compose.yml          # Orchestration (default: lightweight server)
├── Makefile                    # Convenience targets
├── .env.example                # Configuration template
├── pytest.ini                  # Pytest markers configuration
├── faults/                     # Fault injection profiles and scripts
│   ├── apply_netem.sh
│   ├── host_netem.sh
│   ├── host_iptables.sh
│   ├── network_loss_10.yaml
│   ├── network_latency_200.yaml
│   ├── network_blackhole.yaml
│   ├── nfs_ro_export.yaml
│   ├── nfs_badpath.yaml
│   ├── nfs_root_squash.yaml
│   ├── exports_ro
│   ├── exports_badpath
│   └── exports_root_squash
├── nfs-server/                 # Kernel-based server (optional)
│   ├── Dockerfile
│   ├── exports                 # NFS export configuration
│   └── start.sh                # Server startup script
├── nfs-server-lightweight/      # Lightweight server overrides (optional)
│   └── docker-compose.override.yml
├── tests/                      # Test runner and test suites
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── conftest.py             # Pytest fixtures
│   ├── run_tests.sh            # Main test runner script
│   ├── standalone_test.sh      # Standalone testing script
│   ├── test_basic_io.py        # Basic I/O tests (4 tests)
│   ├── test_advanced.py        # Permissions & locking (2 tests)
│   ├── test_concurrent.py      # Concurrent access (1 test)
│   ├── test_metadata.py        # Timestamps (2 tests)
│   ├── test_performance.py     # Performance tests (4 tests)
│   ├── test_data_integrity.py  # Data integrity tests (parametrized)
│   ├── test_off_nominal_network.py
│   ├── test_off_nominal_nfs.py
│   ├── test_off_nominal_server.py
│   ├── test_off_nominal_resource.py
│   ├── generate_performance_report.py
│   └── diagnose_failures.py
├── tests/reports/              # Generated test reports (created at runtime)
├── README.md                   # User documentation
└── TEST_PLAN.md                # This file
```

## Usage

### Quick Start (Default - Lightweight Server)

```bash
# Load NFS kernel modules (required)
sudo modprobe nfs nfsd

# Run tests (default uses lightweight server)
make test

# Or with docker-compose directly
docker-compose --profile default up --build --abort-on-container-exit
```

### Using Kernel Server

```bash
# Run with kernel-based server
make test-kernel

# Or with docker-compose
docker-compose --profile kernel up --build --abort-on-container-exit
```

### Verbose NFS Server Logging

```bash
# Enable verbose server logging (kernel recommended)
make test-verbose

# Or with docker-compose
NFS_VERBOSE=true docker-compose --profile kernel up --build --abort-on-container-exit
```

### Standalone Testing

```bash
# Test against an existing NFS server
./tests/standalone_test.sh <nfs-server-host>
```

## Off-Nominal Coverage Matrix

| Fault Type | Expected Detection | Signal |
|---|---|---|
| Packet loss | Mount timeout or I/O errors | Timeout / EIO |
| Latency | Slow test duration | Duration threshold |
| Mid-transfer disconnect | Partial writes/IO errors | EIO / timeout mid-test |
| Read-only export | Write fails | PermissionError |
| Wrong export | Mount fails | No such file |
| Version mismatch | Mount fails | NFS version error |
| Server restart | Stale file handle | ESTALE |
| Disk full | Write fails | ENOSPC |
| Inode exhaustion | File create fails | ENOSPC/EDQUOT |

## Test Reports

Test reports are automatically generated in the `tests/reports/` directory with the format:
- `YYYY-MM-DD_HH-MM-SS-<server-type>.txt`
- `YYYY-MM-DD_HH-MM-SS-<server-type>.html`
- `YYYY-MM-DD_HH-MM-SS-<server-type>.json`
- `YYYY-MM-DD_HH-MM-SS-<server-type>-summary.txt`
- `YYYY-MM-DD_HH-MM-SS-<server-type>-performance.txt`
- `YYYY-MM-DD_HH-MM-SS-<server-type>-diagnosis.txt`

Reports include:
- Full test output (including test execution tracking and debug logs)
- Test durations for all tests
- Detailed test summary (debug lines filtered)
- Performance metrics and analysis
- Off-nominal diagnosis for fault scenarios
- Exit codes for CI/CD integration

## Known Limitations

- **Kernel Modules**: Both servers require NFS kernel modules on the Docker host
- **Root Permissions**: Tests running as root may bypass permission checks
- **File Locking**: Requires `lockd`/`rpc.statd` - may not be available on all servers
- **Performance Tests**: Enabled by default with standard file sizes (1MB, 5MB, 10MB)
- **Verbose Logging**: Adds noise to logs and may impact performance slightly

## Future Enhancements

- Additional test coverage for very large files, extended attributes, symlinks
- Network partition testing scenarios
- Server load testing
- Automated performance benchmarking
