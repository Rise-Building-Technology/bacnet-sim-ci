#!/bin/bash
set -e

# BACnet Simulator Docker Entrypoint
# Sets up virtual IPs for multi-device simulation, then starts the Python process.
# Requires: --cap-add=NET_ADMIN for multi-device mode.

echo "bacnet-sim-ci: starting up..."

# The Python process handles virtual IP setup internally via networking.py.
# This entrypoint just ensures we exec into the Python process properly.
exec python -m bacnet_sim.main "$@"
