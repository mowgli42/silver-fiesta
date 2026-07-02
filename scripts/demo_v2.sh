#!/usr/bin/env bash
# Quick v2 demo for colleagues — no full Docker suite required
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== NFS Test Suite v2 Demo ==="
echo ""

echo "1) IxDF preflight — good host (localhost)"
PYTHONPATH=tests python3 tests/preflight_check.py 127.0.0.1 --max-attempts 1 || true
echo ""

echo "2) IxDF preflight — bad host (shows DNS failure)"
PYTHONPATH=tests python3 tests/preflight_check.py definitely-not-a-real-nfs-host.invalid --max-attempts 1 || true
echo ""

echo "3) Unit tests (preflight + diagnosis)"
make test-unit-v2
echo ""

echo "4) Full suite (Docker) — run manually:"
echo "   make test"
echo "   make test-observability"
echo ""
echo "After a run, inspect: tests/reports/*-incident.json"
