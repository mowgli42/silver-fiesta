"""
Progressive connectivity checks: DNS → IP → NFS port.

Informs the area of concern before mount or pytest runs.
"""
from __future__ import annotations

import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional

from nfs_suite.ixdf import DisplayBlock, Status


NFS_PORT = 2049
DEFAULT_TIMEOUT_S = 2.0
DEFAULT_MAX_ATTEMPTS = 30


@dataclass
class PreflightResult:
    host: str
    port: int
    blocks: List[DisplayBlock] = field(default_factory=list)
    ok: bool = False
    resolved_ip: Optional[str] = None
    fault_profile: Optional[str] = None

    def to_ixdf_text(self) -> str:
        from nfs_suite.ixdf import render_blocks_text

        return render_blocks_text(self.blocks)


def _run_cmd(cmd: List[str], timeout: float = 5.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _resolve_dns(host: str) -> tuple[bool, Optional[str], List[str]]:
    evidence: List[str] = []
    try:
        proc = _run_cmd(["getent", "hosts", host])
        if proc.returncode == 0 and proc.stdout.strip():
            line = proc.stdout.strip().split()[0]
            evidence.append(f"getent: {proc.stdout.strip()}")
            return True, line, evidence
        evidence.append(f"getent failed (rc={proc.returncode})")
        if proc.stderr:
            evidence.append(proc.stderr.strip()[:200])
    except FileNotFoundError:
        evidence.append("getent not available")
    except subprocess.TimeoutExpired:
        evidence.append("getent timed out")

    # Fallback: socket resolution
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if infos:
            ip = infos[0][4][0]
            evidence.append(f"socket.getaddrinfo → {ip}")
            return True, ip, evidence
    except socket.gaierror as e:
        evidence.append(f"DNS resolution failed: {e}")

    return False, None, evidence


def _ping_host(ip_or_host: str, count: int = 1) -> tuple[bool, List[str]]:
    evidence: List[str] = []
    try:
        proc = _run_cmd(
            ["ping", "-c", str(count), "-W", "2", ip_or_host],
            timeout=10.0,
        )
        if proc.returncode == 0:
            evidence.append("ping: host replied")
            return True, evidence
        evidence.append(f"ping failed (rc={proc.returncode})")
        if proc.stdout:
            evidence.append(proc.stdout.strip().split("\n")[-1][:120])
    except FileNotFoundError:
        evidence.append("ping not available — skipped")
        return True, evidence  # non-fatal in minimal images
    except subprocess.TimeoutExpired:
        evidence.append("ping timed out")
    return False, evidence


def _tcp_port_open(host: str, port: int, timeout: float = DEFAULT_TIMEOUT_S) -> tuple[bool, List[str]]:
    evidence: List[str] = []
    try:
        with socket.create_connection((host, port), timeout=timeout):
            evidence.append(f"TCP {host}:{port} connected")
            return True, evidence
    except OSError as e:
        evidence.append(f"TCP {host}:{port} failed: {e}")
        return False, evidence


def _use_tcp_only_reachability(fault_profile: Optional[str]) -> bool:
    if not fault_profile:
        return False
    return fault_profile.startswith("network_")


def run_preflight(
    host: str,
    port: int = NFS_PORT,
    *,
    fault_profile: Optional[str] = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_interval_s: float = 1.0,
) -> PreflightResult:
    """
    Run DNS → IP → port checks with retries on port step.
    Returns structured IxDF blocks and overall ok flag.
    """
    result = PreflightResult(host=host, port=port, fault_profile=fault_profile)
    blocks: List[DisplayBlock] = []
    tcp_only = _use_tcp_only_reachability(fault_profile)

    # Step 1: DNS
    dns_ok, resolved_ip, dns_evidence = _resolve_dns(host)
    result.resolved_ip = resolved_ip
    dns_block = DisplayBlock(
        id="dns",
        title="DNS / Hostname",
        status=Status.OK if dns_ok else Status.FAIL,
        summary=f"{'Resolved' if dns_ok else 'Cannot resolve'} {host}",
        evidence=dns_evidence,
        action=None if dns_ok else "Verify service name, /etc/hosts, or Docker network DNS.",
        metrics={"host": host, "ip": resolved_ip or "—"},
    )
    blocks.append(dns_block)
    if not dns_ok:
        result.blocks = blocks
        return result

    target = resolved_ip or host

    # Step 2: IP reachability
    if tcp_only:
        reach_ok, reach_evidence = _tcp_port_open(target, port, timeout=1.0)
        reach_block = DisplayBlock(
            id="ip",
            title="IP Reachability (TCP)",
            status=Status.OK if reach_ok else Status.WARN,
            summary="Network fault profile — using TCP probe instead of ping",
            evidence=reach_evidence + ["Packet loss may drop ICMP; TCP to NFS port is authoritative."],
            action=None if reach_ok else "Check netem sidecar, bridge network, or firewall.",
        )
    else:
        reach_ok, reach_evidence = _ping_host(target)
        reach_block = DisplayBlock(
            id="ip",
            title="IP Reachability",
            status=Status.OK if reach_ok else Status.FAIL,
            summary=f"{'Host responds' if reach_ok else 'Host unreachable'} at {target}",
            evidence=reach_evidence,
            action=None if reach_ok else "Confirm container is running and on the same Docker network.",
            metrics={"target": target},
        )
    blocks.append(reach_block)

    # Step 3: NFS port (with retries)
    port_ok = False
    port_evidence: List[str] = []
    for attempt in range(1, max_attempts + 1):
        port_ok, port_evidence = _tcp_port_open(target, port)
        port_evidence.insert(0, f"attempt {attempt}/{max_attempts}")
        if port_ok:
            break
        time.sleep(retry_interval_s)

    port_block = DisplayBlock(
        id="port",
        title=f"NFS Service Port ({port})",
        status=Status.OK if port_ok else Status.FAIL,
        summary=f"Port {port} {'open' if port_ok else 'not reachable'} on {target}",
        evidence=port_evidence,
        action=None
        if port_ok
        else "Ensure NFS server container is up, privileged, and exporting. Check `docker logs nfs-server*`.",
        metrics={"port": port, "attempts": max_attempts},
    )
    blocks.append(port_block)

    result.blocks = blocks
    result.ok = dns_ok and port_ok and (reach_ok or tcp_only)
    return result
