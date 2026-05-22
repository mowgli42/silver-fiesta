"""
IxDF-style information displays for NFS troubleshooting.

Structured blocks follow interaction-design best practices:
  - Clear title and status at a glance
  - Evidence (what we measured)
  - Recommended next action (what to do)
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import List, Optional


class Status(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
    RUNNING = "running"


@dataclass
class DisplayBlock:
    """Single panel in a termui-style dashboard."""

    id: str
    title: str
    status: Status
    summary: str
    evidence: List[str] = field(default_factory=list)
    action: Optional[str] = None
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def _status_glyph(status: Status) -> str:
    return {
        Status.OK: "✓",
        Status.WARN: "⚠",
        Status.FAIL: "✗",
        Status.SKIP: "○",
        Status.RUNNING: "…",
    }.get(status, "?")


def render_blocks_text(blocks: List[DisplayBlock], width: int = 72) -> str:
    """Render blocks as bordered terminal panels (termui-inspired)."""
    lines: List[str] = []
    border = "─" * (width - 2)

    for block in blocks:
        glyph = _status_glyph(block.status)
        header = f" {glyph} {block.title} [{block.status.value.upper()}] "
        pad = max(0, width - len(header) - 2)
        lines.append(f"┌{border}┐")
        lines.append(f"│{header}{' ' * pad}│")
        lines.append(f"├{border}┤")
        lines.append(f"│ {block.summary[: width - 4]:<{width - 4}} │")
        for ev in block.evidence[:8]:
            ev_line = f"  • {ev}"[: width - 4]
            lines.append(f"│ {ev_line:<{width - 4}} │")
        if block.metrics:
            for k, v in list(block.metrics.items())[:6]:
                m = f"  {k}: {v}"[: width - 4]
                lines.append(f"│ {m:<{width - 4}} │")
        if block.action:
            act = f"→ {block.action}"[: width - 4]
            lines.append(f"├{border}┤")
            lines.append(f"│ {act:<{width - 4}} │")
        lines.append(f"└{border}┘")
        lines.append("")
    return "\n".join(lines)


def render_blocks_json(blocks: List[DisplayBlock]) -> str:
    return json.dumps([b.to_dict() for b in blocks], indent=2)
