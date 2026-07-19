"""Parse silver-fiesta / pytest [PERF] lines and rank mount profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


PERF_LINE_RE = re.compile(
    r"\[PERF\]\s+(?P<label>.+?):\s*(?P<body>.*)$"
)
THROUGHPUT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>B|KB|MB|GB|TB)/s",
    re.IGNORECASE,
)
DURATION_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)s")
LATENCY_MS_RE = re.compile(
    r"Avg\s+(?P<kind>Write|Read)\s+Latency:\s+(?P<value>\d+(?:\.\d+)?)ms",
    re.IGNORECASE,
)
OPTIONS_RE = re.compile(r"^Options:\s*(?P<opts>.+)$", re.MULTILINE)
TARGET_RE = re.compile(r"^Target:\s*(?P<label>.+)$", re.MULTILINE)


def _to_bytes_per_sec(value: float, unit: str) -> float:
    mult = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
    }[unit.upper()]
    return value * mult


def format_bps(bps: float) -> str:
    units = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]
    value = float(bps)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{bps:.2f} B/s"


@dataclass
class PerfSample:
    label: str
    throughput_bps: float | None = None
    duration_s: float | None = None
    write_latency_ms: float | None = None
    read_latency_ms: float | None = None
    raw: str = ""


@dataclass
class ProfileResult:
    path: Path
    target: str
    mount_opts: str
    samples: list[PerfSample] = field(default_factory=list)

    def sample(self, label_substr: str) -> PerfSample | None:
        needle = label_substr.lower()
        for sample in self.samples:
            if needle in sample.label.lower():
                return sample
        return None

    def metric_bps(self, label_substr: str) -> float | None:
        sample = self.sample(label_substr)
        return sample.throughput_bps if sample else None

    def score_write_10mb(self) -> float | None:
        return self.metric_bps("Write 10MB")

    def score_read_10mb(self) -> float | None:
        return self.metric_bps("Read 10MB")

    def score_sequential(self) -> float | None:
        sample = self.sample("Sequential I/O")
        if sample and sample.throughput_bps is not None:
            return sample.throughput_bps
        # Sequential block may print Total on a following line already merged.
        return self.metric_bps("Total:")


def parse_perf_log(text: str, path: Path | None = None) -> ProfileResult:
    target_match = TARGET_RE.search(text)
    opts_match = OPTIONS_RE.search(text)
    result = ProfileResult(
        path=path or Path("<memory>"),
        target=(target_match.group("label").strip() if target_match else path.stem if path else "unknown"),
        mount_opts=(opts_match.group("opts").strip() if opts_match else ""),
    )

    pending_seq: PerfSample | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("[PERF]"):
            match = PERF_LINE_RE.search(line)
            if not match:
                continue
            label = match.group("label").strip()
            body = match.group("body").strip()
            sample = PerfSample(label=label, raw=line)
            thr = THROUGHPUT_RE.search(body)
            if thr:
                sample.throughput_bps = _to_bytes_per_sec(
                    float(thr.group("value")), thr.group("unit")
                )
            dur = DURATION_RE.search(body)
            if dur:
                sample.duration_s = float(dur.group("value"))
            result.samples.append(sample)
            if label.lower().startswith("sequential"):
                pending_seq = sample
            continue

        if pending_seq is not None:
            if "Total:" in line:
                thr = THROUGHPUT_RE.search(line)
                if thr:
                    pending_seq.throughput_bps = _to_bytes_per_sec(
                        float(thr.group("value")), thr.group("unit")
                    )
                pending_seq = None
            elif line.startswith("[PERF]") or line.startswith("="):
                pending_seq = None

        lat = LATENCY_MS_RE.search(line)
        if lat:
            kind = lat.group("kind").lower()
            value = float(lat.group("value"))
            # Attach to the most recent small-file sample if present.
            small = result.sample("Small File Latency")
            if small is None:
                small = PerfSample(label="Small File Latency", raw=line)
                result.samples.append(small)
            if kind == "write":
                small.write_latency_ms = value
            else:
                small.read_latency_ms = value

    return result


def load_perf_logs(paths: list[Path]) -> list[ProfileResult]:
    results: list[ProfileResult] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        results.append(parse_perf_log(text, path))
    return results


def rank_profiles(
    results: list[ProfileResult],
    *,
    metric: str = "write_10mb",
) -> list[tuple[ProfileResult, float | None]]:
    def key(item: ProfileResult) -> float:
        value: float | None
        if metric == "read_10mb":
            value = item.score_read_10mb()
        elif metric == "sequential":
            value = item.score_sequential()
        else:
            value = item.score_write_10mb()
        return value if value is not None else -1.0

    ordered = sorted(results, key=key, reverse=True)
    ranked: list[tuple[ProfileResult, float | None]] = []
    for item in ordered:
        if metric == "read_10mb":
            ranked.append((item, item.score_read_10mb()))
        elif metric == "sequential":
            ranked.append((item, item.score_sequential()))
        else:
            ranked.append((item, item.score_write_10mb()))
    return ranked


def format_comparison(
    results: list[ProfileResult],
    *,
    metric: str = "write_10mb",
) -> str:
    ranked = rank_profiles(results, metric=metric)
    lines = [
        "=" * 80,
        "NFS MOUNT PROFILE COMPARISON",
        "=" * 80,
        f"Primary metric: {metric} (higher throughput is better)",
        "",
        f"{'Rank':<5} {'Target':<22} {'Write10MB':>12} {'Read10MB':>12} {'Seq':>12} {'Opts'}",
        "-" * 80,
    ]
    for index, (item, _primary) in enumerate(ranked, start=1):
        w = item.score_write_10mb()
        r = item.score_read_10mb()
        s = item.score_sequential()
        opts = item.mount_opts or "(unknown)"
        if len(opts) > 36:
            opts = opts[:33] + "..."
        lines.append(
            f"{index:<5} {item.target[:22]:<22} "
            f"{(format_bps(w) if w is not None else 'n/a'):>12} "
            f"{(format_bps(r) if r is not None else 'n/a'):>12} "
            f"{(format_bps(s) if s is not None else 'n/a'):>12} "
            f"{opts}"
        )

    winner = next(((item, score) for item, score in ranked if score is not None), None)
    lines.append("")
    if winner:
        item, score = winner
        lines.append(
            f"Fastest ({metric}): {item.target} @ {format_bps(score)} "
            f"[{item.mount_opts}]"
        )
        lines.append(f"Log: {item.path}")
    else:
        lines.append("No [PERF] throughput samples found in the provided logs.")
        lines.append("Re-run with --perf-only (or a full suite that includes test_performance).")
    lines.append("=" * 80)
    return "\n".join(lines)
