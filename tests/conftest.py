import pytest
import os
import shutil
import uuid

MOUNT_POINT = os.environ.get("NFS_MOUNT_POINT", "/mnt/nfs")

@pytest.fixture(scope="session")
def nfs_root():
    if not os.path.exists(MOUNT_POINT):
        pytest.fail(f"NFS mount point {MOUNT_POINT} does not exist.")
    if not os.path.ismount(MOUNT_POINT):
        pytest.fail(f"NFS mount point {MOUNT_POINT} is not mounted.")
    return MOUNT_POINT

@pytest.fixture(scope="session")
def nfs_server_type():
    """Return the configured NFS server type (kernel or lightweight)."""
    return os.environ.get("NFS_SERVER_TYPE", "kernel")

@pytest.fixture(scope="function")
def test_dir(nfs_root):
    """Creates a temporary directory on the NFS share for each test."""
    dir_name = f"test_{uuid.uuid4()}"
    path = os.path.join(nfs_root, dir_name)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        pytest.fail(f"Failed to create test dir {path}: {e}")
        
    yield path
    
    # Cleanup
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except OSError as e:
        print(f"Warning: Failed to cleanup {path}: {e}")
