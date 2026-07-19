#!/usr/bin/env python3
"""Compare silver-fiesta probe logs and rank NFS mount profiles by [PERF] metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1] / "tests"
sys.path.insert(0, str(TESTS_DIR))

from nfs_suite.perf_compare import format_comparison, load_perf_logs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rank NFS mount profiles from silver-fiesta probe logs.",
    )
    parser.add_argument(
        "logs",
        nargs="+",
        type=Path,
        help="Probe log files (logs/*.txt) that contain [PERF] lines",
    )
    parser.add_argument(
        "--metric",
        default="write_10mb",
        choices=("write_10mb", "read_10mb", "sequential"),
        help="Primary ranking metric (default: write_10mb)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path to write the comparison report",
    )
    args = parser.parse_args(argv)

    missing = [str(p) for p in args.logs if not p.is_file()]
    if missing:
        print(f"Missing log files: {', '.join(missing)}", file=sys.stderr)
        return 1

    report = format_comparison(load_perf_logs(args.logs), metric=args.metric)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"\nSaved -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
