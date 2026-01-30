import os
import time
import pytest


def _measure_throughput(path, size_mb):
    size = size_mb * 1024 * 1024
    data = os.urandom(size)
    start = time.time()
    with open(path, "wb") as f:
        f.write(data)
        os.fsync(f.fileno())
    write_duration = time.time() - start
    return size / max(write_duration, 0.0001)


@pytest.mark.off_nominal
def test_network_latency_detection(test_dir):
    """Detect high latency fault by checking operation duration."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "network_latency_200":
        pytest.skip("Not a latency fault profile.")

    file_path = os.path.join(test_dir, "latency_probe.bin")
    start = time.time()
    with open(file_path, "wb") as f:
        f.write(b"x" * 1024)
        os.fsync(f.fileno())
    duration = time.time() - start

    # Expect noticeably slower than normal (<10ms), so allow a conservative threshold
    assert duration > 0.05, f"Latency fault not detected; write duration {duration:.4f}s"


@pytest.mark.off_nominal
def test_network_loss_detection(test_dir):
    """Detect loss fault by measuring degraded throughput."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "network_loss_10":
        pytest.skip("Not a loss fault profile.")

    file_path = os.path.join(test_dir, "loss_probe.bin")
    throughput = _measure_throughput(file_path, size_mb=10)
    throughput_mb = throughput / (1024 * 1024)

    # Conservative cap: under loss, throughput should drop below this threshold
    assert throughput_mb < 200, f"Loss fault not detected; throughput {throughput_mb:.2f} MB/s"

