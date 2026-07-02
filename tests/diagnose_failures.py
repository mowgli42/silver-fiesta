#!/usr/bin/env python3
"""CLI wrapper for v2 structured failure diagnosis."""
import sys
from pathlib import Path

# Allow imports when run from /app or tests/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nfs_suite.diagnosis import diagnose  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: diagnose_failures.py <report_json> [fault_profile] [expected_failures] [report_txt]",
            file=sys.stderr,
        )
        return 1

    report_json = sys.argv[1]
    fault_profile = sys.argv[2] if len(sys.argv) > 2 else "none"
    expected_failures = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 0
    report_txt = sys.argv[4] if len(sys.argv) > 4 else report_json.replace(".json", ".txt")

    report = diagnose(
        report_json_path=report_json,
        report_txt_path=report_txt,
        fault_profile=fault_profile,
        expected_failures=expected_failures,
    )
    print(report.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
