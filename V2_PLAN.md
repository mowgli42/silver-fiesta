# NFS Container Testing Suite — v2.0 Plan

## Vision

Deliver a **shareable, skeptic-proof** NFS validation tool with:

1. **Termui-inspired TUI** — live panels for connectivity, test progress, and diagnosis
2. **SignOz observability** — structured logs/traces an AI agent (or human) can query
3. **IxDF-style displays** — clear information hierarchy: status → evidence → recommended action
4. **Progressive troubleshooting** — DNS → IP → port → mount before blaming NFS semantics
5. **Polished test environment** — unit tests for diagnosis/preflight, CI-friendly non-TUI mode

## Build Sequence (recommended)

| Phase | Deliverable | Why this order |
|-------|-------------|----------------|
| **1** | Preflight + IxDF displays + diagnosis fixes | Unblocks everything; works in CI without SignOz/TUI |
| **2** | OTEL → SignOz + incident bundle | Agents need structured context; builds on phase 1 |
| **3** | Textual TUI + `nfs-test` CLI | Polish layer; wraps existing `run_tests.sh` |
| **4** | Fault matrix gaps + baselines | Extends v1; optional after demo path works |
| **5** | Docs + demo script | What you show skeptics |

## Architecture (v2)

```
┌─────────────────────────────────────────────────────────────┐
│  nfs-test CLI / Textual TUI (optional, NFS_TUI=1)           │
├─────────────────────────────────────────────────────────────┤
│  run_tests.sh → preflight_check.py → pytest → reports       │
├─────────────────────────────────────────────────────────────┤
│  nfs_suite: ixdf | preflight | observability | diagnosis    │
├─────────────────────────────────────────────────────────────┤
│  OTLP → collector → SignOz (docker-compose.observability)   │
└─────────────────────────────────────────────────────────────┘
```

## Preflight sequence (troubleshooting ladder)

When there is no initial connection, checks run in order:

1. **DNS** — `getent hosts <host>` resolves?
2. **IP reachability** — ping or TCP probe (network faults use TCP only)
3. **NFS port** — TCP `:2049` open?
4. **Mount** — `mount -t nfs` with retries

Each step produces an **IxDF display block**: title, status (ok/warn/fail), evidence, next action.

## SignOz / AI troubleshooting

- Every run gets a `run_id` (UUID) as trace attribute
- Preflight, mount, and per-test spans exported via OTLP when `OTEL_ENABLED=true`
- **Incident bundle** (`*-incident.json`): JSON report + preflight + diagnosis + fault metadata — consumable by agents

## Running v2

```bash
# Standard (no TUI, no SignOz) — same as v1
make test

# Preflight only (local or in container)
python3 tests/preflight_check.py nfs-server-lightweight

# With observability
make test-observability

# Interactive TUI (host, requires textual)
NFS_TUI=1 make test-tui

# Generate incident bundle after a run
python3 tests/cli.py bundle tests/reports/<latest>.json
```

## Known v1 gaps addressed in v2

- [x] `diagnose_failures.py` CLI mismatch (JSON passed as text path)
- [x] No structured connectivity ladder
- [x] No centralized logging
- [x] No agent-ready incident artifact
- [ ] `network_blackhole` in Docker netem sidecar (phase 4)
- [ ] `server_restart`, `disk_full` fault wiring (phase 4)

## Demo script for colleagues

```bash
make test                    # green path
make test-preflight-demo     # shows IxDF blocks for a bad host
make test-observability      # SignOz UI + correlated run
```
