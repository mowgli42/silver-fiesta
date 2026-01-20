import os
import pytest
import stat
import fcntl
import time

def test_permissions(test_dir):
    """Test file permission changes."""
    file_path = os.path.join(test_dir, "perm_test.txt")
    with open(file_path, "w") as f:
        f.write("data")
        
    # Change to read-only (for owner)
    # Note: If running as root inside container, permissions might be ignored unless we drop privileges.
    # But usually creating a file with 0o444 and trying to open 'w' should enforce checks or at least reflect stat.
    os.chmod(file_path, 0o444)
    mode = os.stat(file_path).st_mode
    assert stat.S_IMODE(mode) == 0o444
    
    # If we are root, we might still be able to write even with 444. 
    # Checking if we are effectively root
    if os.geteuid() != 0:
        with pytest.raises(PermissionError):
            with open(file_path, "w") as f:
                f.write("new data")
    
    # Change back to writable
    os.chmod(file_path, 0o644)
    with open(file_path, "w") as f:
        f.write("new data")

def test_file_locking(test_dir):
    """Test advisory file locking (flock)."""
    file_path = os.path.join(test_dir, "lock_test.txt")
    with open(file_path, "w") as f:
        f.write("lock me")
        
    f1 = open(file_path, "r+")
    
    try:
        # Acquire exclusive lock
        fcntl.flock(f1, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Try to acquire lock with another file handle
        f2 = open(file_path, "r+")
        try:
            with pytest.raises((BlockingIOError, OSError)):
                # OSError can happen on some NFS implementations if lockd is missing
                fcntl.flock(f2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            f2.close()
            
        # Unlock
        fcntl.flock(f1, fcntl.LOCK_UN)
        
        # Now f2 should be able to lock (simulated by re-opening)
        f3 = open(file_path, "r+")
        try:
            fcntl.flock(f3, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f3, fcntl.LOCK_UN)
        finally:
            f3.close()
            
    except OSError as e:
        pytest.skip(f"Locking not supported or failed: {e}")
    finally:
        f1.close()
