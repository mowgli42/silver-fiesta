import os
import time
import pytest


def format_bytes(bytes_val):
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def format_throughput(bytes_val, duration):
    """Calculate and format throughput."""
    if duration == 0:
        return "N/A"
    throughput = bytes_val / duration
    return f"{format_bytes(throughput)}/s"


@pytest.mark.performance
@pytest.mark.parametrize("size_mb", [1, 5, 10], ids=["1MB", "5MB", "10MB"])
def test_write_throughput(test_dir, size_mb):
    """Measure write throughput for different file sizes.
    
    Reports: Write duration, throughput in MB/s
    """
    file_path = os.path.join(test_dir, f"write_perf_{size_mb}mb.bin")
    size = size_mb * 1024 * 1024
    data = os.urandom(size)

    start = time.time()
    with open(file_path, "wb") as f:
        f.write(data)
        os.fsync(f.fileno())  # Force sync to ensure data is written
    write_duration = time.time() - start

    throughput = format_throughput(size, write_duration)
    
    # Print performance metrics (will be captured in report)
    print(f"\n[PERF] Write {size_mb}MB: {write_duration:.3f}s, Throughput: {throughput}")
    
    assert write_duration >= 0
    assert os.path.getsize(file_path) == size


@pytest.mark.performance
@pytest.mark.parametrize("size_mb", [1, 5, 10], ids=["1MB", "5MB", "10MB"])
def test_read_throughput(test_dir, size_mb):
    """Measure read throughput for different file sizes.
    
    Reports: Read duration, throughput in MB/s
    """
    file_path = os.path.join(test_dir, f"read_perf_{size_mb}mb.bin")
    size = size_mb * 1024 * 1024
    
    # Create test file first
    data = os.urandom(size)
    with open(file_path, "wb") as f:
        f.write(data)
        os.fsync(f.fileno())

    start = time.time()
    with open(file_path, "rb") as f:
        read_data = f.read()
    read_duration = time.time() - start

    throughput = format_throughput(size, read_duration)
    
    # Print performance metrics
    print(f"\n[PERF] Read {size_mb}MB: {read_duration:.3f}s, Throughput: {throughput}")
    
    assert read_data == data
    assert read_duration >= 0


@pytest.mark.performance
def test_sequential_io_throughput(test_dir):
    """Measure sequential I/O throughput (write then read).
    
    Reports: Combined throughput for write+read operations
    """
    file_path = os.path.join(test_dir, "sequential_io.bin")
    size = 10 * 1024 * 1024  # 10MB
    data = os.urandom(size)

    # Write
    write_start = time.time()
    with open(file_path, "wb") as f:
        f.write(data)
        os.fsync(f.fileno())
    write_duration = time.time() - write_start

    # Read
    read_start = time.time()
    with open(file_path, "rb") as f:
        read_data = f.read()
    read_duration = time.time() - read_start

    total_duration = write_duration + read_duration
    total_throughput = format_throughput(size * 2, total_duration)  # 2x for write+read
    
    print(f"\n[PERF] Sequential I/O (10MB):")
    print(f"  Write: {write_duration:.3f}s ({format_throughput(size, write_duration)})")
    print(f"  Read: {read_duration:.3f}s ({format_throughput(size, read_duration)})")
    print(f"  Total: {total_duration:.3f}s ({total_throughput})")
    
    assert read_data == data


@pytest.mark.performance
def test_small_file_latency(test_dir):
    """Measure latency for small file operations.
    
    Reports: Average latency for 1KB file operations
    """
    num_files = 100
    file_size = 1024  # 1KB
    data = os.urandom(file_size)
    
    # Write latency
    write_times = []
    for i in range(num_files):
        file_path = os.path.join(test_dir, f"latency_{i}.bin")
        start = time.time()
        with open(file_path, "wb") as f:
            f.write(data)
        write_times.append(time.time() - start)
    
    avg_write_latency = sum(write_times) / len(write_times)
    
    # Read latency
    read_times = []
    for i in range(num_files):
        file_path = os.path.join(test_dir, f"latency_{i}.bin")
        start = time.time()
        with open(file_path, "rb") as f:
            _ = f.read()
        read_times.append(time.time() - start)
    
    avg_read_latency = sum(read_times) / len(read_times)
    
    print(f"\n[PERF] Small File Latency (1KB, {num_files} files):")
    print(f"  Avg Write Latency: {avg_write_latency*1000:.2f}ms")
    print(f"  Avg Read Latency: {avg_read_latency*1000:.2f}ms")
    print(f"  Total Throughput: {format_throughput(num_files * file_size * 2, sum(write_times) + sum(read_times))}")

