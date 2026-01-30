#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


DIAG_RULES = [
    (r"Connection timed out|timeout", "network_timeout", "Likely packet loss/latency or blackhole."),
    (r"Input/output error|EIO", "io_error", "Likely mid-transfer disconnect or server instability."),
    (r"No such file or directory", "bad_export", "Likely wrong export path or server export misconfig."),
    (r"Permission denied|EPERM|EACCES", "permission", "Likely read-only export or root_squash."),
    (r"Stale file handle|ESTALE", "stale_handle", "Likely server restart or export reload."),
    (r"RPC|rpc", "rpc_error", "Possible NFS version mismatch or rpc services unavailable."),
    (r"mount.*failed", "mount_failed", "Mount failed; check NFS version, export path, or network."),
]


def load_text(path):
    try:
        return Path(path).read_text(errors="ignore")
    except Exception:
        return ""


def diagnose_from_text(text):
    findings = []
    for pattern, code, hint in DIAG_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append({"code": code, "hint": hint, "pattern": pattern})
    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: diagnose_failures.py <report_txt> [report_json]")
        return 1

    report_txt = sys.argv[1]
    report_json = sys.argv[2] if len(sys.argv) > 2 else None

    text = load_text(report_txt)
    findings = diagnose_from_text(text)

    print("==========================================")
    print("FAILURE DIAGNOSIS")
    print("==========================================")
    if not findings:
        print("No known failure signatures detected.")
    else:
        for item in findings:
            print(f"- {item['code']}: {item['hint']} (pattern: {item['pattern']})")

    if report_json and Path(report_json).exists():
        try:
            data = json.loads(Path(report_json).read_text())
            failures = [t for t in data.get("tests", []) if t.get("outcome") in ("failed", "error")]
            print("")
            print(f"JSON failures: {len(failures)}")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

