"""Main entry point for the BACnet simulator."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from typing import TYPE_CHECKING

import uvicorn

from bacnet_sim.api import create_app
from bacnet_sim.config import load_config
from bacnet_sim.devices import SimulatedDevice, create_device, shutdown_device
from bacnet_sim.networking import (
    cleanup_virtual_ips,
    get_primary_ip,
    setup_virtual_ips,
)

if TYPE_CHECKING:
    from bacnet_sim.config import SimulatorConfig

logger = logging.getLogger("bacnet_sim")

# Global state for the running simulator
_devices: list[SimulatedDevice] = []


def get_devices() -> list[SimulatedDevice]:
    """Get the list of running simulated devices."""
    return _devices


async def start_devices(config: SimulatorConfig) -> tuple[list[SimulatedDevice], str, int]:
    """Start all configured BACnet devices with virtual IP allocation.

    Returns (devices, primary_ip, prefix_length) so caller can clean up IPs.
    """
    # Detect primary IP
    primary_ip, prefix_length = get_primary_ip()
    prefix_length = config.global_config.subnet_mask or prefix_length
    logger.info("Primary IP: %s/%d", primary_ip, prefix_length)

    # Build explicit IP map from config
    explicit_ips: dict[int, str] = {}
    for i, dev_config in enumerate(config.devices):
        if dev_config.ip is not None:
            explicit_ips[i] = dev_config.ip

    # Set up virtual IPs
    device_count = len(config.devices)
    ips = setup_virtual_ips(
        primary_ip=primary_ip,
        prefix_length=prefix_length,
        device_count=device_count,
        explicit_ips=explicit_ips,
    )

    # Create each device
    devices: list[SimulatedDevice] = []
    for i, dev_config in enumerate(config.devices):
        try:
            device = await create_device(
                config=dev_config,
                ip=ips[i],
                port=config.global_config.bacnet_port,
                subnet_mask=prefix_length,
                global_network_profile=config.global_config.network_profile,
            )
            devices.append(device)
        except Exception as e:
            logger.error("Failed to create device %d: %s", dev_config.device_id, e)

    if not devices:
        raise RuntimeError("No devices started successfully")

    return devices, primary_ip, prefix_length


async def main() -> None:
    """Main async entry point."""
    parser = argparse.ArgumentParser(description="BACnet Device Simulator")
    parser.add_argument("--config", "-c", help="Path to YAML config file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Load config
    config = load_config(args.config)
    logger.info(
        "Loaded config: %d device(s), API port %d, BACnet port %d",
        len(config.devices),
        config.global_config.api_port,
        config.global_config.bacnet_port,
    )

    # Start devices
    global _devices
    _devices, primary_ip, prefix_length = await start_devices(config)
    logger.info("Started %d device(s)", len(_devices))

    # Create and start FastAPI
    app = create_app(_devices)
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.global_config.api_port,
        log_level=args.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    # Handle SIGTERM/SIGINT for graceful shutdown
    def handle_signal(sig: int, _frame: object) -> None:
        logger.info("Received signal %d, shutting down...", sig)
        server.should_exit = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Run uvicorn (it will handle the event loop)
    logger.info("Starting API server on 0.0.0.0:%d", config.global_config.api_port)
    try:
        await server.serve()
    finally:
        # Cleanup
        logger.info("Shutting down devices...")
        for device in _devices:
            await shutdown_device(device)

        # Clean up virtual IPs (using stored values from start_devices)
        cleanup_virtual_ips(
            [d.ip for d in _devices],
            primary_ip,
            prefix_length,
        )
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
