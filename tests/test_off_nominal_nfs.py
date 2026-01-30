import os
import pytest


@pytest.mark.off_nominal
def test_read_only_export_detection(test_dir):
    """Detect read-only export by expecting write failure."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "nfs_ro_export":
        pytest.skip("Not a read-only export profile.")

    file_path = os.path.join(test_dir, "ro_probe.txt")
    with pytest.raises(PermissionError):
        with open(file_path, "w") as f:
            f.write("should fail")


@pytest.mark.off_nominal
def test_root_squash_detection(test_dir):
    """Detect root_squash by expecting write failure as root."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "nfs_root_squash":
        pytest.skip("Not a root_squash profile.")

    file_path = os.path.join(test_dir, "root_squash_probe.txt")
    with pytest.raises(PermissionError):
        with open(file_path, "w") as f:
            f.write("should fail")

