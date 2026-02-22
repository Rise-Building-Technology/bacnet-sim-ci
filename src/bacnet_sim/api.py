"""FastAPI application for the BACnet simulator REST API."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from bacnet_sim.config import NetworkCustomConfig, NetworkProfileName, ObjectType
from bacnet_sim.devices import SimulatedDevice, _apply_bacnet_lag
from bacnet_sim.health import check_liveness, check_readiness
from bacnet_sim.lag import get_lag_profile
from bacnet_sim.simulation import SimulationConfig, SimulationManager, SimulationMode

logger = logging.getLogger(__name__)


class WriteValueRequest(BaseModel):
    value: float | int | str | bool


class BulkReadItem(BaseModel):
    type: str
    instance: int


class BulkReadRequest(BaseModel):
    objects: list[BulkReadItem]


class BulkWriteItem(BaseModel):
    type: str
    instance: int
    value: float | int | str | bool


class BulkWriteRequest(BaseModel):
    objects: list[BulkWriteItem]


class SimulationRequest(BaseModel):
    mode: SimulationMode
    interval_seconds: float = Field(5.0, gt=0)
    center: float = 0.0
    amplitude: float = 1.0
    period_seconds: float = Field(60.0, gt=0)
    initial: float = 0.0
    step_size: float = Field(1.0, gt=0)
    min_value: float = float("-inf")
    max_value: float = float("inf")
    values: list[Any] = Field(default_factory=list)


class NetworkProfileRequest(BaseModel):
    profile: NetworkProfileName
    min_delay_ms: float | None = None
    max_delay_ms: float | None = None
    drop_probability: float | None = None


def create_app(devices: list[SimulatedDevice]) -> FastAPI:
    """Create the FastAPI application with routes bound to the given devices."""
    snapshots: dict[str, dict] = {}
    sim_manager = SimulationManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
        yield
        sim_manager.stop_all()

    app = FastAPI(
        title="BACnet Simulator API",
        description="REST API for managing simulated BACnet devices",
        version="0.1.0",
        lifespan=lifespan,
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
    async def read_object(device_id: int, object_type: ObjectType, instance: int) -> dict[str, Any]:
        device = _find_device(device_id)

        should_proceed = await device.lag_profile.apply()
        if not should_proceed:
            raise HTTPException(
                status_code=503,
                detail=f"Simulated network drop for device {device_id}",
            )

        obj_config = device.config.find_object(object_type.value, instance)
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
        device_id: int, object_type: ObjectType, instance: int, body: WriteValueRequest
    ) -> dict[str, Any]:
        device = _find_device(device_id)

        should_proceed = await device.lag_profile.apply()
        if not should_proceed:
            raise HTTPException(
                status_code=503,
                detail=f"Simulated network drop for device {device_id}",
            )

        obj_config = device.config.find_object(object_type.value, instance)
        if obj_config is None:
            raise HTTPException(
                status_code=404,
                detail=f"Object {object_type}:{instance} not found on device {device_id}",
            )

        try:
            bacnet_obj = device.get_object(obj_config.name)
            sim_manager.stop(device.device_id, obj_config.name)
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

        # Re-apply lag to BACnet protocol handlers
        if device.bacnet is not None:
            if device.lag_profile.max_delay_ms > 0 or device.lag_profile.drop_probability > 0:
                _apply_bacnet_lag(device.bacnet, device.lag_profile)

        return {
            "deviceId": device.device_id,
            "networkProfile": body.profile.value,
            "minDelayMs": device.lag_profile.min_delay_ms,
            "maxDelayMs": device.lag_profile.max_delay_ms,
            "dropProbability": device.lag_profile.drop_probability,
        }

    # --- Bulk read/write endpoints ---

    @app.post("/api/devices/{device_id}/objects/read")
    async def bulk_read_objects(device_id: int, body: BulkReadRequest) -> list[dict[str, Any]]:
        device = _find_device(device_id)

        should_proceed = await device.lag_profile.apply()
        if not should_proceed:
            raise HTTPException(
                status_code=503,
                detail=f"Simulated network drop for device {device_id}",
            )

        results = []
        for item in body.objects:
            obj_type = item.type
            instance = item.instance
            obj_config = device.config.find_object(obj_type, instance)
            if obj_config is None:
                results.append({"type": obj_type, "instance": instance, "error": "not found"})
                continue
            try:
                bacnet_obj = device.get_object(obj_config.name)
                results.append({
                    "type": obj_config.type.value,
                    "instance": obj_config.instance,
                    "name": obj_config.name,
                    "presentValue": bacnet_obj.presentValue,
                })
            except Exception:
                results.append({"type": obj_type, "instance": instance, "error": "read failed"})
        return results

    @app.post("/api/devices/{device_id}/objects/write")
    async def bulk_write_objects(device_id: int, body: BulkWriteRequest) -> dict[str, Any]:
        device = _find_device(device_id)

        should_proceed = await device.lag_profile.apply()
        if not should_proceed:
            raise HTTPException(
                status_code=503,
                detail=f"Simulated network drop for device {device_id}",
            )

        written = 0
        errors = []
        for item in body.objects:
            obj_config = device.config.find_object(item.type, item.instance)
            if obj_config is None:
                errors.append({"type": item.type, "instance": item.instance, "error": "not found"})
                continue
            try:
                bacnet_obj = device.get_object(obj_config.name)
                sim_manager.stop(device.device_id, obj_config.name)
                bacnet_obj.presentValue = item.value
                written += 1
            except Exception as e:
                errors.append({"type": item.type, "instance": item.instance, "error": str(e)})
        return {"written": written, "errors": errors}

    # --- State management endpoints ---

    @app.post("/api/reset")
    async def reset_state() -> dict[str, Any]:
        """Reset all objects to their initial config values."""
        sim_manager.stop_all()
        reset_count = 0
        for device in devices:
            if device.bacnet is None:
                continue
            for obj_config in device.config.objects:
                if obj_config.value is not None:
                    try:
                        device.bacnet[obj_config.name].presentValue = obj_config.value
                        reset_count += 1
                    except Exception:
                        pass
        return {"reset": True, "objectsReset": reset_count}

    @app.post("/api/snapshot")
    async def create_snapshot() -> dict[str, Any]:
        """Save the current state of all devices."""
        snapshot_id = str(uuid.uuid4())[:8]
        state: dict[int, dict[str, Any]] = {}
        for device in devices:
            device_state: dict[str, Any] = {}
            if device.bacnet is None:
                continue
            for obj_config in device.config.objects:
                try:
                    obj = device.bacnet[obj_config.name]
                    device_state[obj_config.name] = obj.presentValue
                except Exception:
                    pass
            state[device.device_id] = device_state
        snapshots[snapshot_id] = state
        return {
            "snapshotId": snapshot_id,
            "devices": len(state),
        }

    @app.post("/api/snapshot/{snapshot_id}/restore")
    async def restore_snapshot(snapshot_id: str) -> dict[str, Any]:
        """Restore a previously saved snapshot."""
        sim_manager.stop_all()
        if snapshot_id not in snapshots:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        state = snapshots[snapshot_id]
        restored = 0
        for device in devices:
            device_state = state.get(device.device_id, {})
            if device.bacnet is None:
                continue
            for obj_name, value in device_state.items():
                try:
                    device.bacnet[obj_name].presentValue = value
                    restored += 1
                except Exception:
                    pass
        return {"restored": True, "objectsRestored": restored}

    # --- Simulation endpoints ---

    @app.post("/api/devices/{device_id}/objects/{object_type}/{instance}/simulate")
    async def start_simulation(
        device_id: int, object_type: ObjectType, instance: int, body: SimulationRequest
    ) -> dict[str, Any]:
        device = _find_device(device_id)
        obj_config = device.config.find_object(object_type.value, instance)
        if obj_config is None:
            raise HTTPException(
                status_code=404, detail=f"Object {object_type}:{instance} not found"
            )

        bacnet_obj = device.get_object(obj_config.name)
        config = SimulationConfig(
            mode=body.mode,
            interval_seconds=body.interval_seconds,
            center=body.center,
            amplitude=body.amplitude,
            period_seconds=body.period_seconds,
            initial=body.initial,
            step_size=body.step_size,
            min_value=body.min_value,
            max_value=body.max_value,
            values=body.values,
        )

        def set_value(v: Any) -> None:
            bacnet_obj.presentValue = v

        sim_manager.start(device.device_id, obj_config.name, config, set_value)
        return {"status": "started", "mode": body.mode.value, "object": obj_config.name}

    @app.delete("/api/devices/{device_id}/objects/{object_type}/{instance}/simulate")
    async def stop_simulation(
        device_id: int, object_type: ObjectType, instance: int
    ) -> dict[str, Any]:
        device = _find_device(device_id)
        obj_config = device.config.find_object(object_type.value, instance)
        if obj_config is None:
            raise HTTPException(
                status_code=404, detail=f"Object {object_type}:{instance} not found"
            )
        stopped = sim_manager.stop(device.device_id, obj_config.name)
        return {"status": "stopped" if stopped else "not_running", "object": obj_config.name}

    @app.get("/api/devices/{device_id}/objects/{object_type}/{instance}/simulate")
    async def get_simulation_status(
        device_id: int, object_type: ObjectType, instance: int
    ) -> dict[str, Any]:
        device = _find_device(device_id)
        obj_config = device.config.find_object(object_type.value, instance)
        if obj_config is None:
            raise HTTPException(
                status_code=404, detail=f"Object {object_type}:{instance} not found"
            )
        sim = sim_manager.get(device.device_id, obj_config.name)
        if sim is None:
            return {"status": "not_running", "object": obj_config.name}
        return {
            "status": "paused" if sim.paused else "running",
            "mode": sim.config.mode.value,
            "object": obj_config.name,
        }

    return app
