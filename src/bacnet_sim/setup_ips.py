"""Standalone IP setup script for Docker entrypoint.

Runs as root to add virtual IPs before the main process drops privileges.
"""

from __future__ import annotations

import argparse
import logging
import sys

from bacnet_sim.config import load_config
from bacnet_sim.networking import get_primary_ip, setup_virtual_ips

logger = logging.getLogger("bacnet_sim.setup_ips")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Set up virtual IPs for BACnet devices")
    parser.add_argument("--config", "-c", help="Path to YAML config file")
    args = parser.parse_args()

    config = load_config(args.config)

    if len(config.devices) <= 1:
        logger.info("Single device mode, no virtual IPs needed")
        return

    primary_ip, prefix_length = get_primary_ip()
    prefix_length = config.global_config.subnet_mask or prefix_length

    explicit_ips: dict[int, str] = {}
    for i, dev_config in enumerate(config.devices):
        if dev_config.ip is not None:
            explicit_ips[i] = dev_config.ip

    try:
        ips = setup_virtual_ips(
            primary_ip=primary_ip,
            prefix_length=prefix_length,
            device_count=len(config.devices),
            explicit_ips=explicit_ips,
        )
        logger.info("Virtual IPs configured: %s", ips)
    except Exception as e:
        logger.error("Failed to set up virtual IPs: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
