#!/bin/bash
set -e

ACTION="${1:-apply}"
PORT="${2:-2049}"

if [ "$ACTION" = "clear" ]; then
  iptables -D DOCKER-USER -p tcp --dport "$PORT" -j DROP 2>/dev/null || true
  iptables -D DOCKER-USER -p udp --dport "$PORT" -j DROP 2>/dev/null || true
  echo "Cleared iptables drop on port $PORT"
  exit 0
fi

iptables -I DOCKER-USER -p tcp --dport "$PORT" -j DROP
iptables -I DOCKER-USER -p udp --dport "$PORT" -j DROP
echo "Applied iptables drop on port $PORT"

