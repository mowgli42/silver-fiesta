import os
import time


def test_timestamps_update(test_dir):
    """Test that mtime updates after writing.
    
    NOTE: Tests basic timestamp behavior. Does not test:
    - ctime (change time) behavior
    - atime (access time) behavior
    - Timestamp precision/accuracy across NFS versions
    """
    file_path = os.path.join(test_dir, "timestamp.txt")
    with open(file_path, "w") as f:
        f.write("first")

    stat1 = os.stat(file_path)
    time.sleep(1)

    with open(file_path, "w") as f:
        f.write("second")

    stat2 = os.stat(file_path)
    assert stat2.st_mtime > stat1.st_mtime


def test_utime_roundtrip(test_dir):
    """Test that utime is preserved.
    
    NOTE: Tests setting timestamps. Does not test:
    - Future timestamps (may be rejected by some NFS servers)
    - Very old timestamps (before epoch)
    - Nanosecond precision
    """
    file_path = os.path.join(test_dir, "utime.txt")
    with open(file_path, "w") as f:
        f.write("data")

    new_time = int(time.time()) - 3600
    os.utime(file_path, (new_time, new_time))
    stat = os.stat(file_path)
    assert int(stat.st_mtime) == new_time

