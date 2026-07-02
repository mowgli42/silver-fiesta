#!/usr/bin/env python3
"""NFS Test Suite v2 CLI."""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nfs_suite.incident_bundle import build_incident_bundle, write_incident_bundle  # noqa: E402
from nfs_suite.preflight import run_preflight  # noqa: E402


def cmd_preflight(args: argparse.Namespace) -> int:
    from preflight_check import main as preflight_main

    sys.argv = ["preflight_check.py", args.host]
    if args.fault_profile:
        sys.argv.extend(["--fault-profile", args.fault_profile])
    if args.json:
        sys.argv.append("--json")
    return preflight_main()


def cmd_bundle(args: argparse.Namespace) -> int:
    preflight = None
    if args.host:
        preflight = run_preflight(args.host, fault_profile=args.fault_profile)
    bundle = build_incident_bundle(
        args.report_json,
        fault_profile=args.fault_profile or "none",
        expected_failures=args.expected_failures,
        preflight=preflight,
    )
    out = args.output or args.report_json.replace(".json", "-incident.json")
    path = write_incident_bundle(bundle, out)
    print(f"Incident bundle written: {path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    env = {**dict(**{k: v for k, v in []}), **__import__("os").environ}
    if args.observability:
        env["OTEL_ENABLED"] = "true"
    cmd = ["docker-compose"]
    if args.profile:
        cmd.extend(["--profile", args.profile])
    cmd.extend(["up", "--build", "--abort-on-container-exit"])
    return subprocess.call(cmd, env=env, cwd=args.compose_dir)


def main() -> int:
    parser = argparse.ArgumentParser(prog="nfs-test", description="NFS Container Testing Suite v2")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pre = sub.add_parser("preflight", help="DNS → IP → port checks")
    p_pre.add_argument("host")
    p_pre.add_argument("--fault-profile", default=None)
    p_pre.add_argument("--json", action="store_true")
    p_pre.set_defaults(func=cmd_preflight)

    p_bundle = sub.add_parser("bundle", help="Build AI incident bundle from report JSON")
    p_bundle.add_argument("report_json")
    p_bundle.add_argument("--host", default=None)
    p_bundle.add_argument("--fault-profile", default="none")
    p_bundle.add_argument("--expected-failures", type=int, default=0)
    p_bundle.add_argument("-o", "--output", default=None)
    p_bundle.set_defaults(func=cmd_bundle)

    p_run = sub.add_parser("run", help="Run docker-compose test (wrapper)")
    p_run.add_argument("--profile", default="default")
    p_run.add_argument("--observability", action="store_true")
    p_run.add_argument("--compose-dir", default=".")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
