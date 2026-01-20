# NFS Container Testing Suite

This repository contains a test suite for verifying NFS functionality using Docker containers and Python `pytest`.

## Structure

- **nfs-server/**: Docker environment for the NFS server.
- **tests/**: Docker environment for the test runner (NFS client) and Python test scripts.
- **docker-compose.yml**: Orchestration to run server and tests together.

## Prerequisites

- Docker
- Docker Compose

## Running the Tests

To run the full test suite, simply execute:

```bash
docker-compose up --build --abort-on-container-exit
```

This command will:
1. Build the NFS server and Client images.
2. Start the NFS server.
3. Start the Test Client (which waits for the server).
4. Mount the NFS share.
5. Run the `pytest` suite.
6. Exit with the exit code of the test runner.

## Test Coverage

- Basic File I/O (Read/Write/Append)
- Directory Operations
- Large File Handling
- Permissions
- File Locking
