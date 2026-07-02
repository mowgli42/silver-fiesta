#!/usr/bin/env python3
"""Run connectivity preflight and print IxDF display blocks."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nfs_suite.ixdf import render_blocks_json, render_blocks_text  # noqa: E402
from nfs_suite.observability import configure_observability, span  # noqa: E402
from nfs_suite.preflight import run_preflight  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="NFS connectivity preflight (DNS → IP → port)")
    parser.add_argument("host", help="NFS server hostname or IP")
    parser.add_argument("--port", type=int, default=2049)
    parser.add_argument("--fault-profile", default=None)
    parser.add_argument("--json", action="store_true", help="Output JSON blocks")
    parser.add_argument("--max-attempts", type=int, default=30)
    args = parser.parse_args()

    configure_observability()
    with span("preflight", {"host": args.host}):
        result = run_preflight(
            args.host,
            port=args.port,
            fault_profile=args.fault_profile,
            max_attempts=args.max_attempts,
        )

    if args.json:
        print(render_blocks_json(result.blocks))
    else:
        print(result.to_ixdf_text())

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
