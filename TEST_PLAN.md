# NFS Container Testing Plan

## Overview
This document outlines the plan for testing NFS (Network File System) using Docker containers and Python. The goal is to verify NFS functionality, reliability, and performance in a containerized environment.

## Architecture

The testing infrastructure will consist of two main components running as Docker containers:

1.  **NFS Server Container**: Exports a directory using NFSv4.
2.  **NFS Client/Test Container**: Mounts the exported directory and runs Python-based tests.

We will use `docker-compose` to orchestrate these containers.

## Components

### 1. NFS Server
- **Base Image**: Alpine or Debian based.
- **Software**: `nfs-kernel-server` (requires privileged mode) or `nfs-ganesha` (user-space, usually preferred for containers but can be complex). For simplicity and standard compliance testing, we will aim for a kernel-server setup with `privileged: true`.
- **Configuration**: Export `/data` with RW access.

### 2. NFS Client (Test Runner)
- **Base Image**: Python 3.9+ (Slim).
- **Software**: `nfs-common`, `pytest`.
- **Mount Point**: `/mnt/nfs_share`.
- **Role**: Waits for the server to be ready, mounts the share, and executes pytest suites.

## Test Strategy

The tests will be written in Python using `pytest`.

### Test Categories

1.  **Lifecycle Tests**
    - Verify mount success.
    - Verify unmount (optional/cleanup).

2.  **Basic I/O Operations**
    - File creation (`open`, `touch`).
    - Data writing (`write`).
    - Data reading (`read`) and verification.
    - File deletion (`unlink`).
    - Directory operations (`mkdir`, `rmdir`).

3.  **Attributes & Metadata**
    - Permission preservation (`chmod`, `chown`).
    - Timestamps (`stat`).

4.  **Concurrency (Advanced)**
    - Multiple threads/processes writing to different files.
    - File locking (`fcntl.flock`) behavior over NFS.

## Implementation Steps

1.  **Infrastructure Setup**:
    - Create `nfs-server/Dockerfile` and `exports` config.
    - Create `tests/Dockerfile` with Python and NFS client tools.
    - Create `docker-compose.yml` to link them.

2.  **Test Development**:
    - `tests/conftest.py`: Fixtures for setup/teardown (creating temp dirs on share).
    - `tests/test_basic_io.py`: Basic CRUD operations.
    - `tests/test_permissions.py`: Permission checks.

3.  **Execution**:
    - Run `docker-compose up --build --abort-on-container-exit`.

## Directory Structure

```
.
├── docker-compose.yml
├── nfs-server/
│   ├── Dockerfile
│   └── exports
├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── conftest.py
│   └── test_nfs_ops.py
└── TEST_PLAN.md
```
