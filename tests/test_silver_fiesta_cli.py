"""Unit tests for silver-fiesta CLI (no NFS required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import silver_fiesta as sf  # noqa: E402
from nfs_suite.perf_compare import (  # noqa: E402
    format_comparison,
    parse_perf_log,
    rank_profiles,
)


def test_parse_config_targets(tmp_path: Path) -> None:
    cfg = tmp_path / "targets.json"
    cfg.write_text(
        json.dumps(
            {
                "log_dir": "out",
                "defaults": {"nfs_version": "4"},
                "targets": [
                    {"host": "nas-a", "export": "/data"},
                    {"name": "legacy", "host": "nas-b", "nfs_version": "3"},
                ],
            }
        ),
        encoding="utf-8",
    )
    run_cfg = sf.parse_config(cfg)
    assert run_cfg.log_dir == (tmp_path / "out").resolve()
    assert len(run_cfg.targets) == 2
    assert run_cfg.targets[1].name == "legacy"
    assert run_cfg.targets[1].nfs_version == "3"


def test_parse_config_profiles_expand_host(tmp_path: Path) -> None:
    cfg = tmp_path / "profiles.json"
    cfg.write_text(
        json.dumps(
            {
                "defaults": {
                    "host": "192.168.50.51",
                    "export": "/exports/data",
                    "nfs_version": "4",
                },
                "profiles": [
                    {
                        "name": "baseline-v4",
                        "mount_opts": "vers=4,proto=tcp,hard",
                    },
                    {
                        "name": "large-io-1m",
                        "mount_opts": "vers=4,proto=tcp,hard,rsize=1048576,wsize=1048576",
                        "notes": "1MiB buffers",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    run_cfg = sf.parse_config(cfg)
    assert len(run_cfg.targets) == 2
    merged = [sf.merge_target(t, run_cfg.defaults) for t in run_cfg.targets]
    assert merged[0].host == "192.168.50.51"
    assert merged[0].export == "/exports/data"
    assert merged[0].name == "baseline-v4"
    assert "rsize=1048576" in (merged[1].mount_opts or "")
    assert merged[1].notes == "1MiB buffers"


def test_parse_config_requires_profiles_or_targets(tmp_path: Path) -> None:
    cfg = tmp_path / "empty.json"
    cfg.write_text(json.dumps({"defaults": {"host": "x"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="profiles and/or targets"):
        sf.parse_config(cfg)


def test_merge_target_applies_defaults() -> None:
    target = sf.Target(host="10.0.0.1", export="/share")
    merged = sf.merge_target(target, {"nfs_version": "3", "mount_opts": "vers=3"})
    assert merged.nfs_version == "3"
    assert merged.mount_opts == "vers=3"


def test_log_slug_sanitizes_host() -> None:
    target = sf.Target(host="nas.local", export="/")
    assert target.log_slug() == "nas.local"
    named = sf.Target(host="x", export="/", name="My NAS (prod)")
    assert named.log_slug() == "My-NAS-prod"


def test_build_log_path_uses_timestamp_and_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sf, "timestamp_slug", lambda: "2026-07-01_12-00-00")
    target = sf.Target(host="192.168.1.10", export="/")
    path = sf.build_log_path(tmp_path, target)
    assert path.name == "2026-07-01_12-00-00-192.168.1.10.txt"


def test_build_env_perf_only(tmp_path: Path) -> None:
    target = sf.Target(host="nas", export="/", mount_opts="vers=4,proto=tcp,hard")
    env = sf.build_env(target, tmp_path / "log.txt", perf_only=True)
    assert env["PERF_TESTS"] == "1"
    assert env["NFS_PYTEST_ARGS"] == "-m performance"
    assert env["NFS_MOUNT_OPTS"] == "vers=4,proto=tcp,hard"


def test_target_from_args_with_export() -> None:
    args = sf.build_parser().parse_args(["nas:/exports/backup"])
    target = sf.target_from_args(args)
    assert target.host == "nas"
    assert target.export == "/exports/backup"


def test_list_targets_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "one.json"
    cfg.write_text(
        json.dumps(
            {"targets": [{"name": "a", "host": "h1"}, {"host": "h2", "export": "/x"}]}
        ),
        encoding="utf-8",
    )
    code = sf.main(["--config", str(cfg), "--list-targets"])
    assert code == 0
    out = capsys.readouterr().out
    assert "h1" in out
    assert "h2:/x" in out


def test_list_profiles_includes_mount_opts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "perf.json"
    cfg.write_text(
        json.dumps(
            {
                "defaults": {"host": "nas", "export": "/"},
                "profiles": [
                    {
                        "name": "p1",
                        "mount_opts": "vers=4,proto=tcp,hard,rsize=1048576",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    code = sf.main(["--config", str(cfg), "--list-targets"])
    assert code == 0
    out = capsys.readouterr().out
    assert "p1" in out
    assert "rsize=1048576" in out


def test_compare_logs_ranks_fastest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slow = tmp_path / "slow.txt"
    fast = tmp_path / "fast.txt"
    slow.write_text(
        "Target: baseline-v4\nOptions: vers=4,proto=tcp,hard\n"
        "[PERF] Write 10MB: 2.000s, Throughput: 5.00 MB/s\n"
        "[PERF] Read 10MB: 1.000s, Throughput: 10.00 MB/s\n",
        encoding="utf-8",
    )
    fast.write_text(
        "Target: large-io-1m\nOptions: vers=4,proto=tcp,hard,rsize=1048576\n"
        "[PERF] Write 10MB: 0.500s, Throughput: 20.00 MB/s\n"
        "[PERF] Read 10MB: 0.250s, Throughput: 40.00 MB/s\n",
        encoding="utf-8",
    )
    code = sf.main(["--compare-logs", str(slow), str(fast)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Fastest" in out
    assert "large-io-1m" in out


def test_perf_compare_parser_sequential_total() -> None:
    text = (
        "Target: seq-profile\nOptions: vers=4\n"
        "[PERF] Sequential I/O (10MB):\n"
        "  Write: 1.000s (10.00 MB/s)\n"
        "  Read: 0.500s (20.00 MB/s)\n"
        "  Total: 1.500s (13.33 MB/s)\n"
    )
    result = parse_perf_log(text)
    assert result.target == "seq-profile"
    assert result.score_sequential() is not None
    assert result.score_sequential() > 0


def test_rank_profiles_orders_by_write() -> None:
    a = parse_perf_log(
        "Target: a\nOptions: x\n[PERF] Write 10MB: 1s, Throughput: 10.00 MB/s\n"
    )
    b = parse_perf_log(
        "Target: b\nOptions: y\n[PERF] Write 10MB: 1s, Throughput: 50.00 MB/s\n"
    )
    ranked = rank_profiles([a, b])
    assert ranked[0][0].target == "b"
    report = format_comparison([a, b])
    assert "Fastest (write_10mb): b" in report


def test_bundled_performance_profiles_load() -> None:
    cfg = ROOT / "config" / "performance-profiles.json"
    run_cfg = sf.parse_config(cfg)
    assert len(run_cfg.targets) >= 6
    names = {t.name for t in run_cfg.targets}
    assert "baseline-v4" in names
    assert "large-io-1m" in names
    assert "nfsv3-tcp" in names
