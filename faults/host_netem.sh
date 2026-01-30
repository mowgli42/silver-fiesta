#!/bin/bash
set -e

ACTION="${1:-apply}"
PROFILE_NAME="${2:-network_loss_10}"
PROFILE_PATH="$(dirname "$0")/${PROFILE_NAME}.yaml"
BRIDGE_IFACE="${DOCKER_BRIDGE_IFACE:-docker0}"

if [ "$ACTION" = "clear" ]; then
  tc qdisc del dev "$BRIDGE_IFACE" root 2>/dev/null || true
  echo "Cleared netem on $BRIDGE_IFACE"
  exit 0
fi

if [ ! -f "$PROFILE_PATH" ]; then
  echo "Fault profile not found: $PROFILE_PATH"
  exit 1
fi

LOSS=$(grep -E '^  loss:' "$PROFILE_PATH" | awk '{print $2}' || true)
DELAY=$(grep -E '^  delay:' "$PROFILE_PATH" | awk '{print $2}' || true)
JITTER=$(grep -E '^  jitter:' "$PROFILE_PATH" | awk '{print $2}' || true)
RATE=$(grep -E '^  rate:' "$PROFILE_PATH" | awk '{print $2}' || true)

tc qdisc del dev "$BRIDGE_IFACE" root 2>/dev/null || true

NETEM_ARGS=""
if [ -n "$LOSS" ]; then
  NETEM_ARGS="$NETEM_ARGS loss $LOSS"
fi
if [ -n "$DELAY" ]; then
  NETEM_ARGS="$NETEM_ARGS delay $DELAY"
  if [ -n "$JITTER" ]; then
    NETEM_ARGS="$NETEM_ARGS $JITTER"
  fi
fi

if [ -n "$NETEM_ARGS" ]; then
  tc qdisc add dev "$BRIDGE_IFACE" root netem $NETEM_ARGS
fi

if [ -n "$RATE" ]; then
  tc qdisc add dev "$BRIDGE_IFACE" parent 1:1 handle 10: tbf rate "$RATE" burst 32kbit latency 400ms
fi

echo "Applied netem on $BRIDGE_IFACE: $NETEM_ARGS ${RATE:+rate $RATE}"

