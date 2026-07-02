"""
Incident bundle for AI agents and human post-mortems.

Aggregates JSON report, preflight, diagnosis, and run metadata.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nfs_suite.diagnosis import diagnose
from nfs_suite.ixdf import DisplayBlock
from nfs_suite.observability import get_run_id
from nfs_suite.preflight import PreflightResult


def build_incident_bundle(
    report_json_path: str,
    *,
    report_txt_path: Optional[str] = None,
    preflight: Optional[PreflightResult] = None,
    fault_profile: str = "none",
    expected_failures: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    json_path = Path(report_json_path)
    txt_path = report_txt_path or str(json_path).replace(".json", ".txt")

    report_data = None
    if json_path.exists():
        report_data = json.loads(json_path.read_text(errors="ignore"))

    preflight_blocks: List[DisplayBlock] = list(preflight.blocks) if preflight else []
    diag = diagnose(
        report_json_path=str(json_path) if json_path.exists() else None,
        report_txt_path=txt_path if Path(txt_path).exists() else None,
        fault_profile=fault_profile,
        expected_failures=expected_failures,
        preflight_blocks=preflight_blocks,
    )

    bundle: Dict[str, Any] = {
        "schema_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": get_run_id(),
        "environment": {
            "NFS_SERVER": os.environ.get("NFS_SERVER"),
            "NFS_SERVER_TYPE": os.environ.get("NFS_SERVER_TYPE"),
            "NFS_VERSION": os.environ.get("NFS_VERSION"),
            "FAULT_PROFILE": fault_profile,
            "FAULT_CLASS": os.environ.get("FAULT_CLASS"),
        },
        "preflight": {
            "ok": preflight.ok if preflight else None,
            "host": preflight.host if preflight else None,
            "resolved_ip": preflight.resolved_ip if preflight else None,
            "blocks": [b.to_dict() for b in (preflight.blocks if preflight else [])],
        },
        "diagnosis": {
            "findings": diag.findings,
            "actual_failures": diag.actual_failures,
            "expected_failures": diag.expected_failures,
            "blocks": [b.to_dict() for b in diag.blocks],
            "text": diag.to_text(),
        },
        "pytest_summary": _pytest_summary(report_data),
        "agent_prompt": _agent_prompt(diag, preflight, fault_profile),
    }
    if extra:
        bundle["extra"] = extra
    return bundle


def _pytest_summary(data: Optional[dict]) -> Dict[str, Any]:
    if not data:
        return {}
    tests = data.get("tests", [])
    return {
        "total": len(tests),
        "passed": sum(1 for t in tests if t.get("outcome") == "passed"),
        "failed": sum(1 for t in tests if t.get("outcome") == "failed"),
        "skipped": sum(1 for t in tests if t.get("outcome") == "skipped"),
        "duration": data.get("duration"),
    }


def _agent_prompt(diag, preflight: Optional[PreflightResult], fault_profile: str) -> str:
    lines = [
        "You are troubleshooting an NFS container test run.",
        f"Fault profile: {fault_profile}",
    ]
    if preflight and not preflight.ok:
        lines.append("Preflight did NOT pass — focus on DNS/network/port before NFS semantics.")
        for b in preflight.blocks:
            if b.status.value == "fail":
                lines.append(f"  - {b.title}: {b.summary} → {b.action}")
    if diag.findings:
        lines.append("Detected signatures:")
        for f in diag.findings:
            lines.append(f"  - {f['code']}: {f['hint']} | Action: {f['action']}")
    lines.append("Recommend: check docker logs, verify export path, compare to baseline if available.")
    return "\n".join(lines)


def write_incident_bundle(bundle: Dict[str, Any], output_path: str) -> str:
    path = Path(output_path)
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return str(path)
