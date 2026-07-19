# NFS performance tuning reference (client + server)

This note maps common NFS performance tweaks to what silver-fiesta can exercise
directly. Use with `config/performance-profiles.json` and
`sudo ./silver-fiesta --perf-only --compare-perf`.

## Client mount options (sweepable)

| Knob | Example | Profile(s) | Notes |
|------|---------|------------|-------|
| `rsize` / `wsize` | `1048576` or `65536` | `large-io-1m`, `large-io-64k` | Larger I/O reduces round-trips for sequential media |
| `hard` | always prefer for integrity | all bundled profiles | Soft mounts can error out under load |
| `timeo` / `retrans` | `timeo=600,retrans=5` | `resilient-timeouts` | Helps flaky links; not a throughput win |
| `ac` / `actimeo` | `actimeo=60` | `cache-actimeo-60` | Cuts getattr chatter on read-heavy single-writer |
| `nocto` | `nocto` | `cache-nocto` | Skip close-to-open; **not** for multi-writer |
| `nfsvers` / `vers` | `3` vs `4` | `nfsv3-*`, `baseline-v4` | v3 can be faster on some simple exports |
| `proto=tcp` | TCP | all | Prefer TCP over UDP on modern stacks |

Workflow: edit `defaults.host` → `--list-targets` → `--perf-only --compare-perf` →
keep the winner in `/etc/fstab` or your backup client's mount string → optional
server changes below → re-sweep.

## Server / network options (manual, then re-sweep)

These cannot be applied by the client probe; change them on the NAS or LAN, then
re-run the same profile set to measure impact.

| Knob | Where | Guidance |
|------|-------|----------|
| nfsd threads | `/etc/nfs.conf` `[nfsd] threads=32` | Raise for multi-client / 10G |
| export `sync` vs `async` | `/etc/exports` | `async` faster, crash risk; keep `sync` for VMs/DBs |
| `no_subtree_check` | exports | Common with home-lab exports |
| Jumbo frames (MTU 9000) | NIC + switch | Only if end-to-end support |
| TCP buffers | `sysctl` `rmem`/`wmem` | Helps saturate high-BDP links |
| Storage / ZFS recordsize | dataset | Match workload block size |

## Measuring

silver-fiesta `test_performance` emits `[PERF]` lines for write/read throughput
and small-file latency. `scripts/compare_perf.py` ranks logs by
`write_10mb` (default), `read_10mb`, or `sequential`.

For raw network ceiling before NFS tuning, run `iperf3` between client and server.
