import os
import errno
import pytest


@pytest.mark.off_nominal
def test_disk_full_detection(test_dir):
    """Detect disk full via ENOSPC during write."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "disk_full":
        pytest.skip("Not a disk full profile.")

    file_path = os.path.join(test_dir, "disk_full_probe.bin")
    try:
        with open(file_path, "wb") as f:
            f.write(b"x" * (1024 * 1024))
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        assert e.errno in (errno.ENOSPC, errno.EDQUOT), f"Unexpected error: {e}"
        return

    pytest.fail("Disk full fault not detected; write succeeded")


@pytest.mark.off_nominal
def test_inode_exhaustion_detection(test_dir):
    """Detect inode exhaustion via file creation failures."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "inode_exhaustion":
        pytest.skip("Not an inode exhaustion profile.")

    try:
        for i in range(1000):
            with open(os.path.join(test_dir, f"inode_{i}.txt"), "w") as f:
                f.write("x")
    except OSError as e:
        assert e.errno in (errno.ENOSPC, errno.EDQUOT), f"Unexpected error: {e}"
        return

    pytest.fail("Inode exhaustion fault not detected; file creation succeeded")

