#!/usr/bin/env python3
"""
Termui-inspired TUI for NFS test runs (Textual).

Optional: set NFS_TUI=1 when running on a host with textual installed.
In Docker/CI, keep NFS_TUI unset for plain stdout.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Log, Static
except ImportError:
    print("Textual not installed. pip install textual", file=sys.stderr)
    sys.exit(1)

from nfs_suite.ixdf import Status, render_blocks_text  # noqa: E402
from nfs_suite.preflight import run_preflight  # noqa: E402


class NFSTestTUI(App):
    """Live dashboard: preflight panels + log tail."""

    TITLE = "NFS Test Suite v2"
    CSS = """
    #preflight { height: 1fr; border: solid green; }
    #logs { height: 1fr; border: solid cyan; }
    Static { padding: 1; }
    """

    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh_preflight", "Refresh")]

    def __init__(self, host: str, fault_profile: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.fault_profile = fault_profile

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical():
                yield Static("Preflight", id="preflight-title")
                yield Static("Running checks…", id="preflight")
            with Vertical():
                yield Static("Logs", id="logs-title")
                yield Log(id="logs", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_preflight()

    def action_refresh_preflight(self) -> None:
        result = run_preflight(self.host, fault_profile=self.fault_profile, max_attempts=5)
        text = render_blocks_text(result.blocks)
        overall = "READY" if result.ok else "NOT READY"
        self.query_one("#preflight", Static).update(f"[{overall}]\n\n{text}")
        log = self.query_one("#logs", Log)
        log.write_line(f"Preflight {overall} for {self.host}")

    def run_compose(self, profile: str = "default") -> int:
        log = self.query_one("#logs", Log)
        cmd = ["docker-compose", "--profile", profile, "up", "--build", "--abort-on-container-exit"]
        log.write_line(" ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            cwd=os.environ.get("NFS_COMPOSE_DIR", "."),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout
        for line in proc.stdout:
            log.write_line(line.rstrip())
        return proc.wait()


def main() -> int:
    host = os.environ.get("NFS_SERVER", "nfs-server-lightweight")
    fault = os.environ.get("FAULT_PROFILE")
    app = NFSTestTUI(host=host, fault_profile=fault)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
