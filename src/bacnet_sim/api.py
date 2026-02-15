"""FastAPI application for the BACnet simulator REST API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bacnet_sim.config import NetworkCustomConfig, NetworkProfileName
from bacnet_sim.devices import SimulatedDevice
from bacnet_sim.health import check_liveness, check_readiness
from bacnet_sim.lag import get_lag_profile

logger = logging.getLogger(__name__)


class WriteValueRequest(BaseModel):
    value: float | int | str | bool


class NetworkProfileRequest(BaseModel):
    profile: NetworkProfileName
    min_delay_ms: float | None = None
    max_delay_ms: float | None = None
    drop_probability: float | None = None


def create_app(devices: list[SimulatedDevice]) -> FastAPI:
    """Create the FastAPI application with routes bound to the given devices."""
    app = FastAPI(
        title="BACnet Simulator API",
        description="REST API for managing simulated BACnet devices",
        version="0.1.0",
    )

    def _find_device(device_id: int) -> SimulatedDevice:
        for d in devices:
            if d.device_id == device_id:
                return d
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # --- Health endpoints ---

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return check_liveness()

    @app.get("/health/ready")
    async def health_ready() -> JSONResponse:
        body, is_ready = check_readiness(devices)
        status_code = 200 if is_ready else 503
        return JSONResponse(content=body, status_code=status_code)

    # --- Device endpoints ---

    @app.get("/api/devices")
    async def list_devices() -> list[dict[str, Any]]:
        return [
            {
                "deviceId": d.device_id,
                "name": d.name,
                "ip": d.ip,
                "port": d.port,
                "objectCount": len(d.config.objects),
                "initialized": d.initialized,
                "networkProfile": (
                    d.config.network_profile.value
                    if d.config.network_profile
                    else "none"
                ),
            }
            for d in devices
        ]

    @app.get("/api/devices/{device_id}/objects")
    async def list_objects(device_id: int) -> list[dict[str, Any]]:
        device = _find_device(device_id)
        return device.list_objects()

    @app.get("/api/devices/{device_id}/objects/{object_type}/{instance}")
    async def read_object(device_id: int, object_type: str, instance: int) -> dict[str, Any]:
        device = _find_device(device_id)
        obj_config = device.config.find_object(object_type, instance)
        if obj_config is None:
            raise HTTPException(
                status_code=404,
                detail=f"Object {object_type}:{instance} not found on device {device_id}",
            )

        try:
            bacnet_obj = device.get_object(obj_config.name)
            result: dict[str, Any] = {
                "type": obj_config.type.value,
                "instance": obj_config.instance,
                "name": obj_config.name,
                "presentValue": bacnet_obj.presentValue,
                "commandable": obj_config.commandable,
            }
            try:
                result["statusFlags"] = list(bacnet_obj.statusFlags)
            except Exception:
                pass
            return result
        except Exception:
            logger.exception(
                "Error reading object %s:%d on device %d",
                object_type, instance, device_id,
            )
            raise HTTPException(status_code=500, detail="Internal error reading object")

    @app.put("/api/devices/{device_id}/objects/{object_type}/{instance}")
    async def write_object(
        device_id: int, object_type: str, instance: int, body: WriteValueRequest
    ) -> dict[str, Any]:
        device = _find_device(device_id)
        obj_config = device.config.find_object(object_type, instance)
        if obj_config is None:
            raise HTTPException(
                status_code=404,
                detail=f"Object {object_type}:{instance} not found on device {device_id}",
            )

        try:
            bacnet_obj = device.get_object(obj_config.name)
            bacnet_obj.presentValue = body.value
            return {
                "type": obj_config.type.value,
                "instance": obj_config.instance,
                "name": obj_config.name,
                "presentValue": bacnet_obj.presentValue,
            }
        except Exception:
            logger.exception(
                "Error writing object %s:%d on device %d",
                object_type, instance, device_id,
            )
            raise HTTPException(status_code=500, detail="Internal error writing object")

    # --- Network profile endpoint ---

    @app.put("/api/devices/{device_id}/network-profile")
    async def update_network_profile(device_id: int, body: NetworkProfileRequest) -> dict[str, Any]:
        device = _find_device(device_id)

        custom_config = None
        if body.profile == NetworkProfileName.CUSTOM:
            custom_config = NetworkCustomConfig(
                min_delay_ms=body.min_delay_ms if body.min_delay_ms is not None else 0,
                max_delay_ms=body.max_delay_ms if body.max_delay_ms is not None else 0,
                drop_probability=body.drop_probability if body.drop_probability is not None else 0,
            )

        device.lag_profile = get_lag_profile(body.profile, custom_config)
        device.config.network_profile = body.profile

        return {
            "deviceId": device.device_id,
            "networkProfile": body.profile.value,
            "minDelayMs": device.lag_profile.min_delay_ms,
            "maxDelayMs": device.lag_profile.max_delay_ms,
            "dropProbability": device.lag_profile.drop_probability,
        }

    return app
