#!/bin/bash
set -e

PROFILE_NAME="${FAULT_PROFILE:-network_loss_10}"
PROFILE_PATH="/faults/${PROFILE_NAME}.yaml"

# Detect the network interface - when using network_mode: service, interface name may vary
# The netem container shares the network namespace with test-runner-faults, so we need
# to find the active interface that carries traffic to the NFS server
if [ -n "${NETEM_IFACE}" ]; then
  TARGET_IFACE="${NETEM_IFACE}"
else
  # Find the first non-lo interface that is UP and has an IP address
  # This should be the interface used for NFS traffic
  TARGET_IFACE=$(ip -o link show | grep -v " lo:" | grep -E "state UP|state UNKNOWN" | head -1 | awk -F': ' '{print $2}')
  if [ -z "$TARGET_IFACE" ]; then
    # Fallback: try common interface names
    for iface in eth0 eth1 ens0 ens1; do
      if ip link show "$iface" >/dev/null 2>&1; then
        TARGET_IFACE="$iface"
        break
      fi
    done
  fi
  if [ -z "$TARGET_IFACE" ]; then
    echo "ERROR: Could not find network interface"
    echo "Available interfaces:"
    ip link show
    exit 1
  fi
fi

echo "Applying netem profile: ${PROFILE_NAME} on ${TARGET_IFACE}"

if [ ! -f "$PROFILE_PATH" ]; then
  echo "Fault profile not found: $PROFILE_PATH"
  exit 1
fi

# Parse simple YAML key: value lines (strip quotes)
LOSS=$(grep -E '^  loss:' "$PROFILE_PATH" | awk '{print $2}' | tr -d '"' || true)
DELAY=$(grep -E '^  delay:' "$PROFILE_PATH" | awk '{print $2}' | tr -d '"' || true)
JITTER=$(grep -E '^  jitter:' "$PROFILE_PATH" | awk '{print $2}' | tr -d '"' || true)
RATE=$(grep -E '^  rate:' "$PROFILE_PATH" | awk '{print $2}' | tr -d '"' || true)

tc qdisc del dev "$TARGET_IFACE" root 2>/dev/null || true

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
  tc qdisc add dev "$TARGET_IFACE" root netem $NETEM_ARGS
fi

if [ -n "$RATE" ]; then
  tc qdisc add dev "$TARGET_IFACE" parent 1:1 handle 10: tbf rate "$RATE" burst 32kbit latency 400ms
fi

echo "Netem applied: $NETEM_ARGS ${RATE:+rate $RATE}"

# Verify netem is active
echo "Verifying netem configuration:"
tc qdisc show dev "$TARGET_IFACE" || echo "WARNING: Failed to verify netem configuration"

# Show interface statistics to help verify packet loss
echo "Interface statistics (will show packet drops if loss is working):"
cat /proc/net/dev | grep "$TARGET_IFACE" || true

# Keep container alive while tests run
tail -f /dev/null

