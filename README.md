# Silver-fiesta

Client-side NFS probe. Mount a share from this machine, run a focused pytest suite, and **always** save a log named `YYYY-MM-DD_HH-MM-SS-<server>.txt`.

Use it before pointing backups or sync jobs at a NAS, or when debugging mount and write issues.

## Quick start

**Prerequisites:** NFS client tools (`nfs-common`), Python 3, pytest deps, and **sudo** (mount requires root).

```bash
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
chmod +x silver-fiesta

sudo ./silver-fiesta 192.168.50.51
sudo ./silver-fiesta nas.local:/exports/backup
```

Each run writes a log under `logs/`, for example:

```text
logs/2026-07-01_14-30-00-192.168.50.51.txt
```

## Config file (multiple servers / versions)

Pass a JSON config to test several targets in one invocation — different hosts, exports, or NFS versions:

```bash
sudo ./silver-fiesta --config config/example.json
sudo ./silver-fiesta --config my-lab.json --list-targets   # preview only
```

Example `config/example.json`:

```json
{
  "log_dir": "logs",
  "defaults": {
    "nfs_version": "4",
    "mount_opts": "vers=4,proto=tcp",
    "mount_point": "/tmp/nfs_test_mount"
  },
  "targets": [
    { "name": "nas-primary", "host": "192.168.50.51", "export": "/" },
    {
      "name": "nas-backup-v3",
      "host": "192.168.50.52",
      "export": "/mnt/backup",
      "nfs_version": "3",
      "mount_opts": "vers=3,proto=tcp,nolock"
    }
  ]
}
```

| Field | Purpose |
|-------|---------|
| `log_dir` | Where per-run logs are written (default: `logs/`) |
| `defaults` | Shared `nfs_version`, `mount_opts`, `mount_point`, `test_user` |
| `targets[]` | Each server: `host`, `export`, optional `name`, overrides |

CLI flags (`--nfs-version`, `--mount-opts`, `--mount-point`, `--log-dir`) apply to a single-server run and override defaults when using `--config`.

## What gets tested

The probe runs **64+ pytest cases** against the mounted share. Tests run as your normal user (not root) so `root_squash` behavior matches real clients.

| Module | Checks |
|--------|--------|
| `test_basic_io` | Create, read, write, append, directories, ~1MB files |
| `test_data_integrity` | CRC32 across sizes and data patterns |
| `test_advanced` | `chmod`, file locking (`fcntl`) |
| `test_concurrent` | Multi-process writes to separate files |
| `test_metadata` | `mtime` / `utime` behavior |
| `test_performance` | Write/read throughput and latency |
| `test_off_nominal_*` | Fault scenarios when run in container harness (see [TESTING.md](TESTING.md)) |

**Skipped or environment-dependent:** locking without `lockd`, some permission checks when running as root in containers.

## Options

```text
sudo ./silver-fiesta [host|host:/export] [options]

  -c, --config PATH       JSON config with multiple targets
  --export PATH           Export when host has no :/path (default: /)
  --nfs-version VER       NFS version (default: 4)
  --mount-opts OPTS       Mount options (default: vers=4,proto=tcp)
  --mount-point PATH      Local mount (default: /tmp/nfs_test_mount)
  --test-user USER        Run pytest as USER (default: SUDO_USER)
  --log-dir PATH          Log directory (default: logs/)
  --list-targets          Print targets from config and exit
```

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `mounting NFS requires root` | Re-run with `sudo` |
| Cannot create directories on share | `root_squash` — tool already runs pytest as your user; fix export ACLs on the server |
| Export not in `showmount` list | Wrong path; script prints available exports |
| `pytest not found` | Install deps: `.venv/bin/pip install -r tests/requirements.txt` |

Low-level runner (used internally): `tests/standalone_test.sh`.

## Container-based development

To spin up local NFS servers in Docker/Podman, run the full in-repo harness, fault injection, and HTML/JSON reports, see **[TESTING.md](TESTING.md)**.

## Integration

[bookish-train](https://github.com/mowgli42/bookish-train) can call this repo via `nfs_smoke` / `nfs_full` protocol probes during backup triage.
