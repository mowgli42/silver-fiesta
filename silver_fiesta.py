#!/usr/bin/env python3
"""Silver-fiesta: standalone NFS client probe.

Mounts an NFS export from this host, runs the pytest suite, and always writes
a timestamped log named after the server under logs/ (or log_dir from config).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
TESTS_DIR = REPO_ROOT / "tests"
STANDALONE_SCRIPT = TESTS_DIR / "standalone_test.sh"
DEFAULT_LOG_DIR = REPO_ROOT / "logs"
DEFAULT_MOUNT_POINT = "/tmp/nfs_test_mount"
DEFAULT_NFS_VERSION = "4"
DEFAULT_MOUNT_OPTS = "vers=4,proto=tcp"


def _ensure_nfs_suite_path() -> None:
    tests_path = str(TESTS_DIR)
    if tests_path not in sys.path:
        sys.path.insert(0, tests_path)


def run_connectivity_preflight(
    target: Target,
    *,
    log_file: Path | None = None,
    skip: bool = False,
) -> int:
    """DNS → IP → port ladder. Returns 0 if ok or skipped, 1 on failure."""
    if skip:
        return 0

    _ensure_nfs_suite_path()
    try:
        from nfs_suite.observability import configure_observability, span
        from nfs_suite.preflight import run_preflight
    except ImportError as exc:
        print(f"Warning: preflight unavailable ({exc}); continuing.", file=sys.stderr)
        return 0

    configure_observability()
    with span("preflight", {"host": target.host}):
        result = run_preflight(target.host, max_attempts=30, retry_interval_s=1.0)

    text = result.to_ixdf_text()
    print(text)
    if log_file:
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write("\n--- Preflight ---\n")
            fh.write(text)
            fh.write("\n")

    if not result.ok:
        print(f"Preflight failed for {target.host}; skipping mount.", file=sys.stderr)
        return 1
    return 0


@dataclass
class Target:
    host: str
    export: str = "/"
    name: str | None = None
    nfs_version: str | None = None
    mount_opts: str | None = None
    mount_point: str | None = None
    test_user: str | None = None

    @property
    def server_spec(self) -> str:
        return f"{self.host}:{self.export}"

    @property
    def label(self) -> str:
        return self.name or self.host

    def log_slug(self) -> str:
        raw = self.name or self.host
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-")
        return slug or "nfs-server"


@dataclass
class RunConfig:
    log_dir: Path = field(default_factory=lambda: DEFAULT_LOG_DIR)
    defaults: dict[str, Any] = field(default_factory=dict)
    targets: list[Target] = field(default_factory=list)


def _load_json_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a JSON object: {path}")
    return data


def parse_config(path: Path) -> RunConfig:
    data = _load_json_config(path)
    log_dir = Path(data.get("log_dir", DEFAULT_LOG_DIR))
    if not log_dir.is_absolute():
        log_dir = (path.parent / log_dir).resolve()

    defaults = data.get("defaults", {})
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be an object")

    raw_targets = data.get("targets")
    if not raw_targets:
        raise ValueError("config must include a non-empty targets list")
    if not isinstance(raw_targets, list):
        raise ValueError("targets must be a list")

    targets: list[Target] = []
    for index, item in enumerate(raw_targets):
        if not isinstance(item, dict):
            raise ValueError(f"targets[{index}] must be an object")
        host = item.get("host")
        if not host:
            raise ValueError(f"targets[{index}] missing host")
        targets.append(
            Target(
                host=str(host),
                export=str(item.get("export", "/")),
                name=item.get("name"),
                nfs_version=item.get("nfs_version"),
                mount_opts=item.get("mount_opts"),
                mount_point=item.get("mount_point"),
                test_user=item.get("test_user"),
            )
        )

    return RunConfig(log_dir=log_dir, defaults=defaults or {}, targets=targets)


def target_from_args(args: argparse.Namespace) -> Target:
    server_spec = args.server
    if ":" in server_spec:
        host, export = server_spec.split(":", 1)
    else:
        host, export = server_spec, args.export
    return Target(
        host=host,
        export=export,
        nfs_version=args.nfs_version,
        mount_opts=args.mount_opts,
        mount_point=args.mount_point,
        test_user=args.test_user,
    )


def merge_target(target: Target, defaults: dict[str, Any]) -> Target:
    return Target(
        host=target.host,
        export=target.export,
        name=target.name,
        nfs_version=target.nfs_version or str(defaults.get("nfs_version", DEFAULT_NFS_VERSION)),
        mount_opts=target.mount_opts or defaults.get("mount_opts", DEFAULT_MOUNT_OPTS),
        mount_point=target.mount_point or defaults.get("mount_point", DEFAULT_MOUNT_POINT),
        test_user=target.test_user or defaults.get("test_user"),
    )


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


def build_log_path(log_dir: Path, target: Target) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{timestamp_slug()}-{target.log_slug()}.txt"


def build_env(target: Target, log_file: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["NFS_SERVER"] = target.server_spec
    env["NFS_EXPORT"] = target.export if target.export.startswith("/") else f"/{target.export}"
    env["NFS_MOUNT_POINT"] = target.mount_point or DEFAULT_MOUNT_POINT
    env["NFS_VERSION"] = target.nfs_version or DEFAULT_NFS_VERSION
    env["NFS_MOUNT_OPTS"] = target.mount_opts or DEFAULT_MOUNT_OPTS
    env["NFS_SERVER_TYPE"] = "standalone"
    env["SILVER_FIESTA_LOG_FILE"] = str(log_file)
    if target.test_user:
        env["NFS_TEST_USER"] = target.test_user
    return env


def run_target(
    target: Target,
    log_dir: Path,
    *,
    skip_preflight: bool = False,
    preflight_only: bool = False,
) -> tuple[int, Path]:
    log_file = build_log_path(log_dir, target)
    env = build_env(target, log_file)

    header = (
        f"Silver-fiesta NFS probe\n"
        f"Target: {target.label}\n"
        f"Mount: {target.server_spec}\n"
        f"Options: {env['NFS_MOUNT_OPTS']}\n"
        f"Log: {log_file}\n"
        f"{'=' * 72}\n"
    )
    log_file.write_text(header, encoding="utf-8")

    print(header, end="")

    preflight_code = run_connectivity_preflight(
        target, log_file=log_file, skip=skip_preflight
    )
    if preflight_code != 0:
        return preflight_code, log_file
    if preflight_only:
        print(f"[PREFLIGHT OK] {target.label} -> {log_file}")
        return 0, log_file

    print(f"Running tests (log -> {log_file})...")

    if not STANDALONE_SCRIPT.is_file():
        msg = f"Missing runner script: {STANDALONE_SCRIPT}\n"
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(msg)
        print(msg, file=sys.stderr)
        return 1, log_file

    cmd = [str(STANDALONE_SCRIPT), target.server_spec]
    proc = subprocess.run(cmd, env=env, cwd=REPO_ROOT)
    return proc.returncode, log_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="silver-fiesta",
        description="Probe an NFS server from this client. Always writes a dated log per server.",
    )
    parser.add_argument(
        "server",
        nargs="?",
        help="NFS server as host or host:/export (e.g. 192.168.1.10 or nas:/backup)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="JSON config with targets, defaults, and log_dir",
    )
    parser.add_argument(
        "--export",
        default="/",
        help="Export path when server is host-only (default: /)",
    )
    parser.add_argument(
        "--nfs-version",
        default=None,
        help=f"NFS version (default: {DEFAULT_NFS_VERSION})",
    )
    parser.add_argument(
        "--mount-opts",
        default=None,
        help=f"Mount options (default: {DEFAULT_MOUNT_OPTS})",
    )
    parser.add_argument(
        "--mount-point",
        default=None,
        help=f"Local mount point (default: {DEFAULT_MOUNT_POINT})",
    )
    parser.add_argument(
        "--test-user",
        default=None,
        help="User to run pytest as (default: SUDO_USER or current user)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help=f"Directory for log files (default: {DEFAULT_LOG_DIR})",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="With --config, print configured targets and exit",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run DNS → IP → port checks only (no mount)",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip connectivity preflight before mount",
    )
    return parser


def _run_targets(
    targets: list[Target],
    log_dir: Path,
    args: argparse.Namespace,
) -> int:
    failures = 0
    for target in targets:
        code, log_file = run_target(
            target,
            log_dir,
            skip_preflight=args.skip_preflight,
            preflight_only=args.preflight_only,
        )
        status = "PASS" if code == 0 else "FAIL"
        print(f"[{status}] {target.label} (exit {code}) -> {log_file}")
        if code != 0:
            failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.config:
        run_cfg = parse_config(args.config)
        log_dir = args.log_dir or run_cfg.log_dir
        if args.list_targets:
            for target in run_cfg.targets:
                merged = merge_target(target, run_cfg.defaults)
                print(f"{merged.label}\t{merged.server_spec}\tvers={merged.nfs_version}")
            return 0

        if args.server:
            parser.error("pass either a server argument or --config, not both")

        merged = [merge_target(t, run_cfg.defaults) for t in run_cfg.targets]
        return _run_targets(merged, log_dir, args)

    if not args.server:
        parser.print_help()
        print("\nExamples:", file=sys.stderr)
        print("  sudo ./silver-fiesta 192.168.50.51", file=sys.stderr)
        print("  sudo ./silver-fiesta nas.local:/exports/backup", file=sys.stderr)
        print("  sudo ./silver-fiesta --config config/example.json", file=sys.stderr)
        return 2

    log_dir = args.log_dir or DEFAULT_LOG_DIR
    target = merge_target(
        target_from_args(args),
        {
            "nfs_version": args.nfs_version or DEFAULT_NFS_VERSION,
            "mount_opts": args.mount_opts or DEFAULT_MOUNT_OPTS,
            "mount_point": args.mount_point or DEFAULT_MOUNT_POINT,
            "test_user": args.test_user,
        },
    )
    return _run_targets([target], log_dir, args)


if __name__ == "__main__":
    sys.exit(main())
