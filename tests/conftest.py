import pytest
import os
import shutil
import uuid
import time

MOUNT_POINT = os.environ.get("NFS_MOUNT_POINT", "/mnt/nfs")


@pytest.fixture(scope="session", autouse=True)
def _v2_observability():
    """Initialize OTLP tracing when OTEL_ENABLED=true."""
    try:
        from nfs_suite.observability import configure_observability

        configure_observability()
    except ImportError:
        pass


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


# Hook to print test execution status
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Print when a test starts executing."""
    import sys
    test_name = item.nodeid
    # Clean up test name for display (remove tests/ prefix if present)
    display_name = test_name.replace("tests/", "").replace(".py::", "::")
    print(f"\n{'='*80}", flush=True)
    print(f"Running test: {display_name}", flush=True)
    print(f"{'='*80}", flush=True)
    sys.stdout.flush()


# Hook to track test execution time and print performance info
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Track test execution time and add to report."""
    outcome = yield
    rep = outcome.get_result()
    
    # Store duration in the report for later use
    if hasattr(call, 'duration'):
        rep.duration = call.duration
    elif hasattr(call, 'stop') and hasattr(call, 'start'):
        rep.duration = call.stop - call.start if call.stop and call.start else None
    
    # Print test completion info
    if rep.when == "call":
        import sys
        test_name = item.nodeid.replace("tests/", "").replace(".py::", "::")
        status = rep.outcome.upper()
        duration = getattr(rep, 'duration', None)
        if duration:
            print(f"\n[TEST COMPLETE] {test_name}: {status} ({duration:.3f}s)", flush=True)
        else:
            print(f"\n[TEST COMPLETE] {test_name}: {status}", flush=True)
        sys.stdout.flush()
