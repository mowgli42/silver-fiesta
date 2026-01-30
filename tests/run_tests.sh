#!/bin/bash
# Exit on error, but allow cleanup to run even if tests fail
# Use pipefail to catch errors in pipelines (like tee)
set -e -o pipefail

# Determine NFS server based on FAULT_PROFILE if not explicitly set
# Network faults use lightweight server; NFS config faults use nfs-server-faults
if [ -z "${NFS_SERVER}" ]; then
    if [ -n "${FAULT_PROFILE}" ] && echo "${FAULT_PROFILE}" | grep -q "^network_"; then
        # Network fault - use lightweight server
        NFS_SERVER="nfs-server-lightweight"
        NFS_SERVER_TYPE="${NFS_SERVER_TYPE:-lightweight}"
        FAULT_CLASS="${FAULT_CLASS:-network}"
    elif [ -n "${FAULT_PROFILE}" ]; then
        # NFS config fault - use nfs-server-faults
        NFS_SERVER="nfs-server-faults"
        NFS_SERVER_TYPE="${NFS_SERVER_TYPE:-faults}"
        FAULT_CLASS="${FAULT_CLASS:-nfs}"
    else
        # Default - use lightweight server
        NFS_SERVER="nfs-server-lightweight"
        NFS_SERVER_TYPE="${NFS_SERVER_TYPE:-lightweight}"
    fi
fi

SERVER_HOST="${NFS_SERVER}"
MOUNT_POINT="${NFS_MOUNT_POINT:-/mnt/nfs}"
NFS_VERSION="${NFS_VERSION:-4}"
NFS_MOUNT_OPTS="${NFS_MOUNT_OPTS:-vers=${NFS_VERSION},proto=tcp}"
PYTEST_ARGS="${PYTEST_ARGS:--v}"
FAULT_PROFILE="${FAULT_PROFILE:-none}"
FAULT_CLASS="${FAULT_CLASS:-none}"
EXPECTED_FAILURES="${EXPECTED_FAILURES:-0}"
BASELINE_JSON="${BASELINE_JSON:-}"

# Track test exit code
TEST_EXIT_CODE=0

# Debug logging - writes to stdout (for docker logs) and to report file (for full report)
# Debug logs are included in full report but filtered from summary
DEBUG_LOG="/tmp/nfs_test_debug.log"
log_debug() {
    local msg="[DEBUG $(date +%H:%M:%S)] $*"
    echo "$msg" | tee -a "$DEBUG_LOG"
    # Append to report file if it exists (will be created later in the script)
    [ -n "$REPORT_TXT" ] && [ -f "$REPORT_TXT" ] && echo "$msg" >> "$REPORT_TXT" || true
}

# Initialize report file early to capture debug logs
REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SYSTEM_TESTED="${NFS_SERVER_TYPE:-nfs-server}"
# Include fault profile in report name if set (will be set later if FAULT_PROFILE is provided)
REPORT_BASE="$REPORT_DIR/${TIMESTAMP}-${SYSTEM_TESTED}"
REPORT_TXT="${REPORT_BASE}.txt"
# Create report file early to capture debug logs
touch "$REPORT_TXT"

log_debug "=== Test Runner Startup ==="
log_debug "SERVER_HOST=${SERVER_HOST}"
log_debug "NFS_SERVER env=${NFS_SERVER:-not set}"
log_debug "NFS_SERVER_TYPE=${NFS_SERVER_TYPE:-not set}"

cleanup() {
  # Don't fail on cleanup errors - NFS unmount can be problematic in containers
  set +e
  if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "Unmounting $MOUNT_POINT..."
    # Try regular unmount first, then lazy unmount if that fails
    # Lazy unmount detaches immediately even if files are in use
    umount "$MOUNT_POINT" 2>/dev/null || umount -l "$MOUNT_POINT" 2>/dev/null || true
  fi
  set -e
}

check_nfs_ready() {
  timeout 1 bash -c "cat < /dev/null > /dev/tcp/${SERVER_HOST}/2049" 2>/dev/null
}

trap cleanup EXIT

log_debug "Starting server connectivity checks"
log_debug "Attempting to resolve hostname: $SERVER_HOST"
if getent hosts "$SERVER_HOST" >/dev/null 2>&1; then
    log_debug "Hostname resolved: $(getent hosts $SERVER_HOST)"
else
    log_debug "WARNING: Hostname not resolved in /etc/hosts"
fi

echo "Waiting for NFS server ($SERVER_HOST) to be reachable..."
# For network fault scenarios, use TCP connection check instead of ping
# (ping packets may be dropped by netem, but TCP connections will retry)
if [ -n "${FAULT_PROFILE}" ] && echo "${FAULT_PROFILE}" | grep -q "^network_"; then
  # Network fault scenario - use TCP connection check (more resilient to packet loss)
  log_debug "Network fault scenario detected - using TCP connection check"
  CONNECT_COUNT=0
  until check_nfs_ready; do
    CONNECT_COUNT=$((CONNECT_COUNT + 1))
    log_debug "TCP connection attempt $CONNECT_COUNT failed for $SERVER_HOST:2049"
    if [ $CONNECT_COUNT -ge 30 ]; then
      log_debug "ERROR: TCP connection failed after 30 attempts"
      log_debug "Checking network connectivity..."
      if command -v ip >/dev/null 2>&1; then
        ip addr show | grep -E "inet|eth" | head -5 >> "$DEBUG_LOG" || true
      fi
    cat /etc/hosts >> "$DEBUG_LOG" || true
    exit 1
  fi
  echo "waiting for $SERVER_HOST..."
  sleep 1
  done
  log_debug "TCP connection to $SERVER_HOST:2049 successful"
else
  # Normal scenario - use ping
  PING_COUNT=0
  until ping -c 1 "$SERVER_HOST" &> /dev/null; do
    PING_COUNT=$((PING_COUNT + 1))
    log_debug "Ping attempt $PING_COUNT failed for $SERVER_HOST"
    if [ $PING_COUNT -ge 30 ]; then
      log_debug "ERROR: Ping failed after 30 attempts"
      log_debug "Checking network connectivity..."
      if command -v ip >/dev/null 2>&1; then
        ip addr show | grep -E "inet|eth" | head -5 >> "$DEBUG_LOG" || true
      fi
      cat /etc/hosts >> "$DEBUG_LOG" || true
      exit 1
    fi
    echo "waiting for $SERVER_HOST..."
    sleep 1
  done
  log_debug "Ping successful to $SERVER_HOST"
fi

echo "Waiting for NFS service to be ready..."
NFS_CHECK_COUNT=0
until check_nfs_ready; do
  NFS_CHECK_COUNT=$((NFS_CHECK_COUNT + 1))
  log_debug "NFS port check attempt $NFS_CHECK_COUNT failed"
  if [ $NFS_CHECK_COUNT -ge 30 ]; then
    log_debug "ERROR: NFS port 2049 not accessible after 30 attempts"
    log_debug "Testing port connectivity..."
    timeout 2 bash -c "cat < /dev/null > /dev/tcp/${SERVER_HOST}/2049" 2>&1 >> "$DEBUG_LOG" || true
    exit 1
  fi
  echo "NFS port not ready, waiting..."
  sleep 2
done
log_debug "NFS port 2049 is accessible"

echo "Mounting NFS share from $SERVER_HOST:/ with options: $NFS_MOUNT_OPTS"
# Retry mount loop
MAX_RETRIES=10
COUNT=0
until mount -t nfs -o "$NFS_MOUNT_OPTS" "$SERVER_HOST":/ "$MOUNT_POINT"; do
  echo "Mount failed, retrying in 2 seconds..."
  sleep 2
  COUNT=$((COUNT+1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "Failed to mount NFS share after $MAX_RETRIES attempts."
    exit 1
  fi
done

echo "Mount successful. Running tests..."
export NFS_MOUNT_POINT="$MOUNT_POINT"

# Update report base name if fault profile is set (preserve debug logs in file)
if [ -n "${FAULT_PROFILE}" ] && [ "${FAULT_PROFILE}" != "none" ]; then
    NEW_REPORT_BASE="$REPORT_DIR/${TIMESTAMP}-${SYSTEM_TESTED}-${FAULT_PROFILE}"
    NEW_REPORT_TXT="${NEW_REPORT_BASE}.txt"
    # Copy existing debug logs to new file name, then rename
    if [ -f "$REPORT_TXT" ] && [ "$REPORT_TXT" != "$NEW_REPORT_TXT" ]; then
        cp "$REPORT_TXT" "$NEW_REPORT_TXT" 2>/dev/null || true
        REPORT_TXT="$NEW_REPORT_TXT"
        REPORT_BASE="$NEW_REPORT_BASE"
    fi
fi

# Set remaining report file paths
REPORT_HTML="${REPORT_BASE}.html"
REPORT_JSON="${REPORT_BASE}.json"
REPORT_SUMMARY="${REPORT_BASE}-summary.txt"
REPORT_PERF="${REPORT_BASE}-performance.txt"
REPORT_DIAGNOSIS="${REPORT_BASE}-diagnosis.txt"

# Start capturing all output to the full report file (append mode to preserve debug logs)
# Debug logs written before this point are already in REPORT_TXT
exec > >(tee -a "$REPORT_TXT") 2>&1

echo "=========================================="
echo "NFS Server Performance Test Suite"
echo "=========================================="
echo "Server Type: ${SYSTEM_TESTED}"
echo "Server Host: ${SERVER_HOST}"
echo "NFS Version: ${NFS_VERSION}"
echo "Mount Options: ${NFS_MOUNT_OPTS}"
echo "Fault Profile: ${FAULT_PROFILE}"
echo "Fault Class: ${FAULT_CLASS}"
echo "Expected Failures: ${EXPECTED_FAILURES}"
echo "Report Files:"
echo "  - Detailed: ${REPORT_TXT}"
echo "  - HTML: ${REPORT_HTML}"
echo "  - JSON: ${REPORT_JSON}"
echo "  - Summary: ${REPORT_SUMMARY}"
echo "=========================================="

# Run pytest with comprehensive reporting
# Temporarily disable exit on error to capture exit code
set +e

# Pytest options:
# -v: verbose (show each test name)
# -s: show stdout (don't capture)
# -rA: show extra test summary info for all tests
# --durations=0: show durations for all tests (0 means all, not just slowest)
# --tb=short: shorter traceback format
# --html: generate HTML report
# --json-report: generate JSON report
# --json-report-file: specify JSON report file
# --benchmark-only: only run benchmark tests (if using benchmark)
# --benchmark-autosave: automatically save benchmark results
# Capture all output (including debug logs from earlier) to the full report
# Debug logs are already in stdout from log_debug calls above
# Note: Test execution status is printed via pytest hooks in conftest.py
echo ""
echo "Starting test execution..."
echo "Each test will be displayed as it runs."
echo ""
pytest -v -s -rA --durations=0 --tb=short \
    --html="${REPORT_HTML}" --self-contained-html \
    --json-report --json-report-file="${REPORT_JSON}" \
    2>&1 | tee -a "$REPORT_TXT"

# Capture the exit code from pytest (first command in the pipe)
TEST_EXIT_CODE=${PIPESTATUS[0]}
set -e

# Generate comprehensive summary report
{
    echo "=========================================="
    echo "NFS SERVER PERFORMANCE TEST SUMMARY"
    echo "=========================================="
    echo "Test Run: ${TIMESTAMP}"
    echo "Server Type: ${SYSTEM_TESTED}"
    echo "Server Host: ${SERVER_HOST}"
    echo "NFS Version: ${NFS_VERSION}"
    echo "Mount Options: ${NFS_MOUNT_OPTS}"
    echo "Fault Profile: ${FAULT_PROFILE}"
    echo "Fault Class: ${FAULT_CLASS}"
    echo "Expected Failures: ${EXPECTED_FAILURES}"
    echo ""
    echo "----------------------------------------"
    echo "TEST EXECUTION SUMMARY"
    echo "----------------------------------------"
    
    # Extract test summary from pytest output
    if [ -f "$REPORT_TXT" ]; then
        echo ""
        echo "----------------------------------------"
        echo "TEST EXECUTION LIST"
        echo "----------------------------------------"
        
        # Extract all test names and their results (exclude debug lines)
        echo ""
        echo "All Tests Executed:"
        # Try to extract from pytest verbose output first
        if grep -v "\[DEBUG" "$REPORT_TXT" | grep -q "Running test:"; then
            # Extract from our custom "Running test:" format
            grep -v "\[DEBUG" "$REPORT_TXT" | grep "Running test:" | \
                sed 's/.*Running test: //' | \
                awk '{printf "  %-60s\n", $1}'
        fi
        # Also extract from pytest's standard output
        grep -v "\[DEBUG" "$REPORT_TXT" | grep -E "^tests/.*\.py::.* (PASSED|FAILED|SKIPPED|ERROR)" | \
            sed 's/^tests\///' | \
            awk '{printf "  %-60s %s\n", $1, $2}' || \
            grep -v "\[DEBUG" "$REPORT_TXT" | grep -E "PASSED|FAILED|SKIPPED|ERROR" | grep -v "test session" | head -100
        
        echo ""
        echo "----------------------------------------"
        echo "PERFORMANCE METRICS"
        echo "----------------------------------------"
        
        # Extract performance markers (exclude debug lines)
        if grep -v "\[DEBUG" "$REPORT_TXT" | grep -q "\[PERF\]"; then
            echo ""
            echo "Performance Measurements:"
            grep -v "\[DEBUG" "$REPORT_TXT" | grep "\[PERF\]" | sed 's/^/  /'
        fi
        
        # Extract duration information (exclude debug lines)
        if grep -v "\[DEBUG" "$REPORT_TXT" | grep -q "slowest"; then
            echo ""
            echo "Test Durations (slowest first):"
            grep -v "\[DEBUG" "$REPORT_TXT" | grep -A 100 "slowest" | grep -E "\.py::|seconds" | head -50 | sed 's/^/  /'
        fi
        
        # Extract summary statistics (exclude debug lines)
        if grep -v "\[DEBUG" "$REPORT_TXT" | grep -q "passed\|failed\|skipped"; then
            echo ""
            echo "Summary Statistics:"
            grep -v "\[DEBUG" "$REPORT_TXT" | grep -E "[0-9]+ (passed|failed|skipped|error)" | tail -5 | sed 's/^/  /'
        fi
        
        # Count tests by category (exclude debug lines)
        echo ""
        echo "Test Counts by Category:"
        total_tests=$(grep -v "\[DEBUG" "$REPORT_TXT" | grep -c "PASSED\|FAILED\|SKIPPED\|ERROR" | head -1 || echo "0")
        passed=$(grep -v "\[DEBUG" "$REPORT_TXT" | grep -c "PASSED" || echo "0")
        failed=$(grep -v "\[DEBUG" "$REPORT_TXT" | grep -c "FAILED" || echo "0")
        skipped=$(grep -v "\[DEBUG" "$REPORT_TXT" | grep -c "SKIPPED" || echo "0")
        echo "  Total: ${total_tests}"
        echo "  Passed: ${passed}"
        echo "  Failed: ${failed}"
        echo "  Skipped: ${skipped}"
        echo "  Expected Failures: ${EXPECTED_FAILURES}"
    fi
    
    echo ""
    echo "----------------------------------------"
    echo "REPORT FILES"
    echo "----------------------------------------"
    echo "Detailed Text Report: ${REPORT_TXT}"
    echo "HTML Report: ${REPORT_HTML}"
    echo "JSON Report: ${REPORT_JSON}"
    echo "This Summary: ${REPORT_SUMMARY}"
    echo "Performance Report: ${REPORT_PERF}"
    echo "Diagnosis Report: ${REPORT_DIAGNOSIS}"
    if [ -n "$BASELINE_JSON" ]; then
        echo "Baseline JSON: ${BASELINE_JSON}"
    fi
    echo ""
    echo "Exit Code: ${TEST_EXIT_CODE}"
    echo "=========================================="
} > "$REPORT_SUMMARY"

# Generate performance report from JSON if available
if [ -f "$REPORT_JSON" ] && command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "Generating performance analysis..."
    python3 /app/generate_performance_report.py "$REPORT_JSON" > "$REPORT_PERF" 2>/dev/null || true
fi

# Generate failure diagnosis report from JSON if available
if [ -f "$REPORT_JSON" ] && command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "Generating failure diagnosis..."
    python3 /app/diagnose_failures.py "$REPORT_JSON" "${FAULT_PROFILE:-none}" "${EXPECTED_FAILURES:-0}" > "$REPORT_DIAGNOSIS" 2>/dev/null || true
fi

# Display summary
cat "$REPORT_SUMMARY"
if [ -f "$REPORT_PERF" ]; then
    echo ""
    cat "$REPORT_PERF"
fi
if [ -f "$REPORT_DIAGNOSIS" ]; then
    echo ""
    cat "$REPORT_DIAGNOSIS"
fi

echo ""
echo "Tests completed with exit code: ${TEST_EXIT_CODE}"
exit $TEST_EXIT_CODE
