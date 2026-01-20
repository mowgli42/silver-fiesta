import os
import multiprocessing


def _write_file(path, data):
    """Helper function for concurrent write test."""
    with open(path, "wb") as f:
        f.write(data)


def test_concurrent_writes(test_dir):
    """Test concurrent writes to different files.
    
    NOTE: Tests multi-process concurrent access. Does not test:
    - Concurrent writes to the same file (would require locking)
    - Thread-based concurrency (uses processes for isolation)
    - Network partition scenarios
    """
    payload = os.urandom(64 * 1024)
    paths = [os.path.join(test_dir, f"concurrent_{i}.bin") for i in range(4)]

    processes = [multiprocessing.Process(target=_write_file, args=(p, payload)) for p in paths]
    for proc in processes:
        proc.start()
    for proc in processes:
        proc.join(timeout=10)
        assert proc.exitcode == 0

    for path in paths:
        assert os.path.exists(path)
        assert os.path.getsize(path) == len(payload)

