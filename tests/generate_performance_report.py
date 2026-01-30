#!/usr/bin/env python3
"""
Generate a comprehensive performance report from pytest JSON output.
This script parses the JSON report and creates a human-readable performance summary.
"""
import json
import sys
import os
from pathlib import Path


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


def format_bytes(bytes_val):
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def generate_performance_report(json_file):
    """Generate performance report from JSON file."""
    if not os.path.exists(json_file):
        print(f"Error: JSON report file not found: {json_file}", file=sys.stderr)
        return 1
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract test information
    tests = data.get('tests', [])
    
    # Group tests by outcome
    passed = [t for t in tests if t.get('outcome') == 'passed']
    failed = [t for t in tests if t.get('outcome') == 'failed']
    skipped = [t for t in tests if t.get('outcome') == 'skipped']
    
    # Calculate statistics
    total_duration = sum(t.get('duration', 0) for t in tests)
    avg_duration = total_duration / len(tests) if tests else 0
    
    # Sort by duration
    tests_by_duration = sorted(tests, key=lambda x: x.get('duration', 0), reverse=True)
    
    # Generate report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("NFS SERVER PERFORMANCE REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Total Tests: {len(tests)}")
    report_lines.append(f"  Passed: {len(passed)}")
    report_lines.append(f"  Failed: {len(failed)}")
    report_lines.append(f"  Skipped: {len(skipped)}")
    report_lines.append("")
    report_lines.append(f"Total Execution Time: {format_duration(total_duration)}")
    report_lines.append(f"Average Test Duration: {format_duration(avg_duration)}")
    report_lines.append("")
    
    # Performance tests
    perf_tests = [t for t in tests if 'performance' in t.get('keywords', {}).get('test', [])]
    if perf_tests:
        report_lines.append("-" * 80)
        report_lines.append("PERFORMANCE TESTS")
        report_lines.append("-" * 80)
        for test in perf_tests:
            name = test.get('nodeid', '').split('::')[-1]
            duration = test.get('duration', 0)
            outcome = test.get('outcome', 'unknown')
            report_lines.append(f"  {name}: {outcome.upper()} ({format_duration(duration)})")
        report_lines.append("")
    
    # Slowest tests
    report_lines.append("-" * 80)
    report_lines.append("SLOWEST TESTS (Top 10)")
    report_lines.append("-" * 80)
    for test in tests_by_duration[:10]:
        name = test.get('nodeid', '').split('::')[-1]
        duration = test.get('duration', 0)
        outcome = test.get('outcome', 'unknown')
        report_lines.append(f"  {format_duration(duration):>10} - {name} ({outcome})")
    report_lines.append("")
    
    # All tests list
    report_lines.append("-" * 80)
    report_lines.append("ALL TESTS EXECUTED")
    report_lines.append("-" * 80)
    for test in sorted(tests, key=lambda x: x.get('nodeid', '')):
        name = test.get('nodeid', '')
        duration = test.get('duration', 0)
        outcome = test.get('outcome', 'unknown')
        report_lines.append(f"  [{outcome.upper():<7}] {format_duration(duration):>10} - {name}")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    # Print and save
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save to file
    report_file = json_file.replace('.json', '-performance.txt')
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(f"\nPerformance report saved to: {report_file}")
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: generate_performance_report.py <json_report_file>", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(generate_performance_report(sys.argv[1]))

