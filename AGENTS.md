# Agent instructions — silver-fiesta

NFS client probe + container test harness. Standalone tool for real servers; Docker/Podman stack for CI and fault injection.

## Location on this machine

- Clone: `~/repo/silver-fiesta` (or `$REPOS_DIR/silver-fiesta`)
- Clone via: `~/github-env/clone.sh silver-fiesta`

## Prerequisites

- **NFS client** (`nfs-common`) for standalone probes; **sudo** for mount
- **Podman** (preferred) or Docker + compose for in-repo harness
- **NFS kernel modules on the host** when running compose NFS servers:
  ```bash
  sudo modprobe nfs nfsd
  ```
- Python 3 + venv

## Setup

```bash
source ~/github-env/env.sh
cd ~/repo/silver-fiesta
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
chmod +x silver-fiesta scripts/container-compose.sh
```

## Standalone client probe (primary tool)

```bash
sudo ./silver-fiesta 192.168.50.51
sudo ./silver-fiesta nas:/exports/backup --nfs-version 3 --mount-opts vers=3,proto=tcp,nolock
sudo ./silver-fiesta --config config/example.json
```

Logs: `logs/YYYY-MM-DD_HH-MM-SS-<server>.txt` (always created). Preflight (DNS → IP → port) runs before mount unless `--skip-preflight`.

```bash
sudo ./silver-fiesta 192.168.50.51 --preflight-only   # connectivity only
make demo-v2                                          # v2 IxDF demo (no NFS)
make test-unit-v2                                     # v2 unit tests
```

## Container harness (development / CI)

See [TESTING.md](TESTING.md).

```bash
make test          # lightweight NFS server (default)
make test-kernel   # kernel-based server
```

Reports: `tests/reports/`.

## Quick smoke without NFS mount

```bash
.venv/bin/python -m pytest tests/ --collect-only -q
.venv/bin/python -m pytest tests/test_silver_fiesta_cli.py -q
```

## Integration with bookish-train

bookish-train uses structured `EBK` logs and `transfer-log.jsonl` for backup troubleshooting. When extending silver-fiesta for bookish-train protocol checks, emit the same log shapes so failed backups can be correlated with NFS probe results.

## Issue Tracking

This project uses **bd (beads)** for issue tracking. Run `bd prime` for workflow context.

- `bd ready` - find unblocked work
- `bd create "Title" --type task --priority 2` - create an issue
- `bd close <id>` - close completed work
