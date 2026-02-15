#!/bin/bash
set -e

# BACnet Simulator Docker Entrypoint
# Runs as root to set up virtual IPs, then drops to non-root user.
# Requires: --cap-add=NET_ADMIN for multi-device mode.

echo "bacnet-sim-ci: starting up..."

# Phase 1: Set up virtual IPs as root (requires NET_ADMIN)
python -m bacnet_sim.setup_ips "$@"

# Phase 2: Drop privileges and run the application as appuser
echo "bacnet-sim-ci: dropping privileges to appuser..."
exec gosu appuser python -m bacnet_sim.main "$@"
