"""Unit tests for silver-fiesta CLI (no NFS required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import silver_fiesta as sf  # noqa: E402


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


def test_build_log_path_uses_timestamp_and_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sf, "timestamp_slug", lambda: "2026-07-01_12-00-00")
    target = sf.Target(host="192.168.1.10", export="/")
    path = sf.build_log_path(tmp_path, target)
    assert path.name == "2026-07-01_12-00-00-192.168.1.10.txt"


def test_target_from_args_with_export() -> None:
    args = sf.build_parser().parse_args(["nas:/exports/backup"])
    target = sf.target_from_args(args)
    assert target.host == "nas"
    assert target.export == "/exports/backup"


def test_list_targets_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "one.json"
    cfg.write_text(
        json.dumps({"targets": [{"name": "a", "host": "h1"}, {"host": "h2", "export": "/x"}]}),
        encoding="utf-8",
    )
    code = sf.main(["--config", str(cfg), "--list-targets"])
    assert code == 0
    out = capsys.readouterr().out
    assert "h1" in out
    assert "h2:/x" in out
