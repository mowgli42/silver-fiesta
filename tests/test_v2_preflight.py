"""Unit tests for v2 preflight and IxDF displays (no Docker required)."""
import socket
from unittest.mock import patch

import pytest

from nfs_suite.ixdf import DisplayBlock, Status, render_blocks_text
from nfs_suite.preflight import run_preflight
from nfs_suite.diagnosis import diagnose


def test_ixdf_render_contains_title():
    blocks = [
        DisplayBlock(
            id="dns",
            title="DNS / Hostname",
            status=Status.OK,
            summary="Resolved localhost",
            evidence=["getent: 127.0.0.1 localhost"],
            action=None,
        )
    ]
    text = render_blocks_text(blocks)
    assert "DNS / Hostname" in text
    assert "OK" in text


@patch("nfs_suite.preflight._resolve_dns")
@patch("nfs_suite.preflight._ping_host")
@patch("nfs_suite.preflight._tcp_port_open")
def test_preflight_ok(mock_port, mock_ping, mock_dns):
    mock_dns.return_value = (True, "10.0.0.2", ["resolved"])
    mock_ping.return_value = (True, ["ping ok"])
    mock_port.return_value = (True, ["port open"])

    result = run_preflight("nfs-server", max_attempts=1, retry_interval_s=0)
    assert result.ok
    assert len(result.blocks) == 3
    assert result.blocks[0].id == "dns"


@patch("nfs_suite.preflight._resolve_dns")
def test_preflight_dns_fail(mock_dns):
    mock_dns.return_value = (False, None, ["failed"])
    result = run_preflight("nonexistent.invalid", max_attempts=1, retry_interval_s=0)
    assert not result.ok
    assert result.blocks[0].status == Status.FAIL


def test_diagnose_mount_failure():
    report = diagnose(
        report_txt_path=None,
        report_json_path=None,
        fault_profile="none",
    )
    # empty report — no findings
    assert report.actual_failures == 0

    text = "Failed to mount NFS share after 10 attempts"
    report2 = diagnose(report_txt_path=None, report_json_path=None)
    # inject via fake - use diagnose with text in json-less way
    from nfs_suite.diagnosis import _collect_failure_text

    combined = text
    findings = []
    import re
    from nfs_suite.diagnosis import DIAG_RULES

    for pattern, code, hint, action in DIAG_RULES:
        if re.search(pattern, combined, re.IGNORECASE):
            findings.append(code)
    assert "mount_failed" in findings or any("mount" in f for f in findings)


@patch("nfs_suite.preflight.socket.create_connection")
@patch("nfs_suite.preflight._resolve_dns")
@patch("nfs_suite.preflight._ping_host")
def test_network_fault_uses_tcp_reachability(mock_ping, mock_dns, mock_conn):
    mock_dns.return_value = (True, "10.0.0.5", ["ok"])
    mock_conn.return_value.__enter__ = lambda s: s
    mock_conn.return_value.__exit__ = lambda *a: None

    with patch("nfs_suite.preflight._tcp_port_open", return_value=(True, ["tcp ok"])):
        result = run_preflight("host", fault_profile="network_loss_10", max_attempts=1, retry_interval_s=0)
    assert mock_ping.call_count == 0  # ping skipped for network faults
    assert result.blocks[1].title.startswith("IP Reachability (TCP)")
