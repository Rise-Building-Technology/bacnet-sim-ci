"""Health check logic for the BACnet simulator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bacnet_sim.devices import SimulatedDevice


def check_liveness() -> dict:
    """Liveness check: is the process running?"""
    return {"status": "alive"}


def check_readiness(devices: list[SimulatedDevice]) -> tuple[dict, bool]:
    """Readiness check: are all devices initialized?

    Returns (response_body, is_ready).
    """
    if not devices:
        return {"status": "not_ready", "reason": "no devices configured"}, False

    device_statuses = []
    all_ready = True
    for device in devices:
        ready = device.initialized and device.bacnet is not None
        device_statuses.append({
            "device_id": device.device_id,
            "name": device.name,
            "ip": device.ip,
            "ready": ready,
        })
        if not ready:
            all_ready = False

    return {
        "status": "ready" if all_ready else "not_ready",
        "devices": device_statuses,
    }, all_ready
