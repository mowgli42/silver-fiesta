"""
Structured failure diagnosis for NFS test runs and AI troubleshooting.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from nfs_suite.ixdf import DisplayBlock, Status, render_blocks_text


DIAG_RULES = [
    (
        r"Connection timed out|timeout",
        "network_timeout",
        "Likely packet loss, high latency, or blackhole on the path to NFS.",
        "Check FAULT_PROFILE, netem sidecar logs, and host network.",
    ),
    (
        r"Input/output error|EIO",
        "io_error",
        "Likely mid-transfer disconnect or server instability.",
        "Inspect NFS server logs and disk health on the export volume.",
    ),
    (
        r"No such file or directory",
        "bad_export",
        "Likely wrong export path or server export misconfiguration.",
        "Verify /etc/exports and that /data exists on the server container.",
    ),
    (
        r"Permission denied|EPERM|EACCES",
        "permission",
        "Likely read-only export or root_squash.",
        "Review export options (rw vs ro) and root_squash settings.",
    ),
    (
        r"Stale file handle|ESTALE",
        "stale_handle",
        "Likely server restart or export reload during tests.",
        "Remount the share or restart the server cleanly before re-running.",
    ),
    (
        r"RPC|rpc",
        "rpc_error",
        "Possible NFS version mismatch or rpc services unavailable.",
        "Confirm vers=4 in mount options and rpcbind/nfsd on kernel server.",
    ),
    (
        r"mount.*failed|Failed to mount",
        "mount_failed",
        "Mount failed before tests — often DNS, port, or export path.",
        "Run preflight_check.py and review preflight IxDF blocks.",
    ),
    (
        r"Name or service not known|could not resolve",
        "dns_failure",
        "Hostname did not resolve inside the test container.",
        "Check Docker network aliases and /etc/hosts.",
    ),
    (
        r"Connection refused",
        "connection_refused",
        "Nothing listening on port 2049 or firewall blocking.",
        "Ensure nfs-server container is running and privileged.",
    ),
]

FAULT_HINTS = {
    "network_loss_10": "Expected: degraded throughput; some timeouts under load.",
    "network_latency_200": "Expected: slow tests; elevated durations.",
    "network_blackhole": "Expected: mount/connection failures.",
    "nfs_ro_export": "Expected: write tests fail with permission errors.",
    "nfs_badpath": "Expected: mount failure (bad export path).",
    "nfs_root_squash": "Expected: permission-related test differences.",
}


@dataclass
class DiagnosisReport:
    findings: List[Dict[str, str]] = field(default_factory=list)
    failed_tests: List[Dict[str, Any]] = field(default_factory=list)
    fault_profile: str = "none"
    expected_failures: int = 0
    actual_failures: int = 0
    blocks: List[DisplayBlock] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [
            "==========================================",
            "FAILURE DIAGNOSIS (v2)",
            "==========================================",
            f"Fault profile: {self.fault_profile}",
            f"Failures: {self.actual_failures} (expected: {self.expected_failures})",
            "",
        ]
        if self.blocks:
            lines.append(render_blocks_text(self.blocks))
        if not self.findings:
            lines.append("No known failure signatures detected in logs.")
        else:
            lines.append("Pattern matches:")
            for f in self.findings:
                lines.append(f"  • [{f['code']}] {f['hint']}")
                lines.append(f"    Action: {f['action']}")
        if self.failed_tests:
            lines.append("")
            lines.append(f"Failed tests ({len(self.failed_tests)}):")
            for t in self.failed_tests[:20]:
                lines.append(f"  - {t.get('nodeid', t.get('name', '?'))}")
        return "\n".join(lines)


def _load_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(errors="ignore"))
    except Exception:
        return None


def _collect_failure_text(report_json: Optional[dict], report_txt: str) -> str:
    parts = [report_txt]
    if report_json:
        for t in report_json.get("tests", []):
            if t.get("outcome") in ("failed", "error"):
                parts.append(t.get("nodeid", ""))
                for key in ("call", "setup", "teardown"):
                    block = t.get(key, {})
                    if isinstance(block, dict):
                        parts.append(block.get("longrepr", "") or "")
                        parts.append(block.get("crash", "") or "")
    return "\n".join(str(p) for p in parts if p)


def diagnose(
    report_json_path: Optional[str] = None,
    report_txt_path: Optional[str] = None,
    fault_profile: str = "none",
    expected_failures: int = 0,
    preflight_blocks: Optional[List[DisplayBlock]] = None,
) -> DiagnosisReport:
    report = DiagnosisReport(
        fault_profile=fault_profile or "none",
        expected_failures=int(expected_failures or 0),
    )

    txt = ""
    data = None
    if report_txt_path and Path(report_txt_path).exists():
        txt = Path(report_txt_path).read_text(errors="ignore")
    if report_json_path and Path(report_json_path).exists():
        data = _load_json(Path(report_json_path))

    combined = _collect_failure_text(data, txt)
    for pattern, code, hint, action in DIAG_RULES:
        if re.search(pattern, combined, re.IGNORECASE):
            report.findings.append(
                {"code": code, "hint": hint, "action": action, "pattern": pattern}
            )

    if data:
        report.failed_tests = [
            t
            for t in data.get("tests", [])
            if t.get("outcome") in ("failed", "error")
        ]
        report.actual_failures = len(report.failed_tests)

    # IxDF summary block
    if report.actual_failures == 0 and not report.findings:
        status = Status.OK
        summary = "No failures detected in this run."
    elif fault_profile != "none" and report.actual_failures > 0:
        status = Status.WARN
        summary = f"Failures under fault profile '{fault_profile}' — may be expected."
    else:
        status = Status.FAIL
        summary = f"{report.actual_failures} test failure(s) with actionable signatures."

    fault_hint = FAULT_HINTS.get(fault_profile, "")
    report.blocks = list(preflight_blocks or [])
    report.blocks.append(
        DisplayBlock(
            id="diagnosis",
            title="Failure Diagnosis",
            status=status,
            summary=summary,
            evidence=[f["hint"] for f in report.findings[:6]] or [fault_hint or "See full report."],
            action=report.findings[0]["action"] if report.findings else "Review HTML/JSON report.",
            metrics={
                "actual_failures": report.actual_failures,
                "expected_failures": report.expected_failures,
            },
        )
    )
    return report
