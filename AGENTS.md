# Agent instructions — silver-fiesta

NFS transfer-protocol test harness (Docker/Podman + pytest). Use this repo to validate NFS mount/read/write performance and fault behavior before wiring results into [bookish-train](https://github.com/mowgli42/bookish-train) backup diagnostics.

## Location on this machine

- Clone: `~/repo/silver-fiesta` (or `$REPOS_DIR/silver-fiesta`)
- Clone via: `~/github-env/clone.sh silver-fiesta`

## Prerequisites

- **Podman** (preferred) or Docker + compose
- **NFS kernel modules on the host** (required for in-container NFS server):
  ```bash
  sudo modprobe nfs nfsd
  ```
- Python 3 + venv for local pytest collection/smoke

## Setup (agent / CI-like host)

```bash
source ~/github-env/env.sh
cd ~/repo/silver-fiesta
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
chmod +x scripts/container-compose.sh
./scripts/container-compose.sh config -q   # validate compose file
```

Or: `~/github-env/setup.sh` (includes silver-fiesta when listed in `repos.conf`).

## Run full NFS suite (privileged)

```bash
cd ~/repo/silver-fiesta
make test          # lightweight NFS server (default)
make test-kernel   # kernel-based server (build + profile kernel)
```

Uses `./scripts/container-compose.sh` when `COMPOSE` is unset (Podman on this host).

Reports land in `tests/reports/` (`.txt`, `.html`, `.json`, performance and diagnosis sidecars).

## Quick smoke without NFS mount

```bash
cd ~/repo/silver-fiesta
.venv/bin/python -m pytest tests/ --collect-only -q
```

## Standalone against an external NFS host

```bash
./tests/standalone_test.sh <nfs-server-host>
```

## Integration with bookish-train

bookish-train uses structured `EBK` logs and `transfer-log.jsonl` for backup troubleshooting (`scripts/home-backup-chain-demo.py`, `clients/common/edge_observability.py`). When extending silver-fiesta for bookish-train protocol checks, emit the same log shapes so failed backups can be correlated with NFS probe results.

## Issue Tracking

This project uses **bd (beads)** for issue tracking. Run `bd prime` for workflow context, or install hooks with `bd hooks install` for automatic context injection.

Quick reference:

- `bd ready` - find unblocked work
- `bd create "Title" --type task --priority 2` - create an issue
- `bd close <id>` - close completed work
- `bd dolt push` - push Beads data when using a shared Beads remote

For full workflow details, run `bd prime`.
