"""Unit tests for v2 diagnosis."""
import json
import tempfile
from pathlib import Path

from nfs_suite.diagnosis import diagnose


def test_diagnose_mount_failure_from_text(tmp_path):
    txt = tmp_path / "report.txt"
    txt.write_text("Failed to mount NFS share after 10 attempts\nConnection refused")
    report = diagnose(report_txt_path=str(txt))
    codes = [f["code"] for f in report.findings]
    assert "mount_failed" in codes or "connection_refused" in codes


def test_diagnose_json_failures(tmp_path):
    data = {
        "tests": [
            {"nodeid": "tests/test_basic_io.py::test_x", "outcome": "failed", "call": {"longrepr": "Permission denied"}},
        ]
    }
    j = tmp_path / "report.json"
    j.write_text(json.dumps(data))
    report = diagnose(report_json_path=str(j), fault_profile="nfs_ro_export", expected_failures=1)
    assert report.actual_failures == 1
    assert any(f["code"] == "permission" for f in report.findings)
