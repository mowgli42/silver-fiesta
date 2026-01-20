import os
import time
import pytest


@pytest.mark.performance
def test_large_file_throughput(test_dir):
    """Basic throughput sanity check (skipped unless PERF_TESTS=1).
    
    NOTE: This is a minimal performance test. Does not test:
    - Actual throughput benchmarks (no minimum thresholds)
    - Different file sizes
    - Sequential vs random I/O patterns
    - Network latency impact
    - Server load scenarios
    
    To enable: Set PERF_TESTS=1 environment variable.
    """
    if os.environ.get("PERF_TESTS") != "1":
        pytest.skip("Performance tests disabled. Set PERF_TESTS=1 to enable.")

    file_path = os.path.join(test_dir, "throughput.bin")
    size = 5 * 1024 * 1024
    data = os.urandom(size)

    start = time.time()
    with open(file_path, "wb") as f:
        f.write(data)
    write_duration = time.time() - start

    start = time.time()
    with open(file_path, "rb") as f:
        read_data = f.read()
    read_duration = time.time() - start

    assert read_data == data
    assert write_duration >= 0
    assert read_duration >= 0

