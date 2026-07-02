#!/usr/bin/env sh
# Run compose with Podman (preferred) or Docker. Same compose file works for both.
# Usage: ./scripts/container-compose.sh [compose args...]
set -e

if [ -n "${CONTAINER_RUNTIME:-}" ]; then
  rt="$CONTAINER_RUNTIME"
else
  if command -v podman >/dev/null 2>&1; then
    rt=podman
  elif command -v docker >/dev/null 2>&1; then
    rt=docker
  else
    echo "Need podman or docker in PATH (or set CONTAINER_RUNTIME)." >&2
    exit 1
  fi
fi

case "$rt" in
  podman)
    if command -v podman-compose >/dev/null 2>&1; then
      exec podman-compose "$@"
    else
      exec podman compose "$@"
    fi
    ;;
  docker)
    if command -v docker-compose >/dev/null 2>&1; then
      exec docker-compose "$@"
    else
      exec docker compose "$@"
    fi
    ;;
  *)
    echo "CONTAINER_RUNTIME must be podman or docker." >&2
    exit 1
    ;;
esac
