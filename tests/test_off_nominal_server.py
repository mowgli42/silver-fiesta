import os
import pytest


@pytest.mark.off_nominal
def test_server_restart_detection(test_dir):
    """Detect server restart via stale file handle (ESTALE)."""
    profile = os.environ.get("FAULT_PROFILE", "")
    if profile != "server_restart":
        pytest.skip("Not a server restart profile.")

    file_path = os.path.join(test_dir, "restart_probe.txt")
    with open(file_path, "w") as f:
        f.write("before restart")

    # Expect a stale handle or IO error after restart
    with pytest.raises(OSError):
        with open(file_path, "r") as f:
            _ = f.read()

