"""Tests for the FastAPI REST API."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from bacnet_sim.api import create_app
from bacnet_sim.config import DeviceConfig, ObjectConfig, ObjectType
from bacnet_sim.devices import SimulatedDevice
from bacnet_sim.lag import LagProfile


def _make_mock_device(
    device_id: int = 1001,
    name: str = "TestDevice",
    ip: str = "172.18.0.10",
    port: int = 47808,
    initialized: bool = True,
) -> SimulatedDevice:
    """Create a mock SimulatedDevice for testing."""
    config = DeviceConfig(
        device_id=device_id,
        name=name,
        objects=[
            ObjectConfig(
                type=ObjectType.ANALOG_INPUT,
                instance=1,
                name="Zone Temp",
                unit="degreesCelsius",
                value=72.5,
            ),
            ObjectConfig(
                type=ObjectType.BINARY_OUTPUT,
                instance=1,
                name="Fan Command",
                commandable=True,
                value=False,
            ),
        ],
    )

    # Mock the BAC0 device
    temp_obj = MagicMock()
    temp_obj.presentValue = 72.5
    temp_obj.statusFlags = [0, 0, 0, 0]

    fan_obj = MagicMock()
    fan_obj.presentValue = False
    fan_obj.statusFlags = [0, 0, 0, 0]

    objects_map = {"Zone Temp": temp_obj, "Fan Command": fan_obj}

    mock_bacnet = MagicMock()
    mock_bacnet.__getitem__ = MagicMock(side_effect=lambda name: objects_map[name])

    device = SimulatedDevice(
        config=config,
        ip=ip,
        port=port,
        bacnet=mock_bacnet,
        lag_profile=LagProfile(0, 0, 0),
        initialized=initialized,
    )
    return device


@pytest.fixture
def client():
    """Create a test client with a mock device."""
    device = _make_mock_device()
    app = create_app([device])
    return TestClient(app)


@pytest.fixture
def client_multi():
    """Create a test client with multiple mock devices."""
    devices = [
        _make_mock_device(device_id=1001, name="AHU-1", ip="172.18.0.10"),
        _make_mock_device(device_id=1002, name="AHU-2", ip="172.18.0.11"),
    ]
    app = create_app(devices)
    return TestClient(app)


class TestHealthEndpoints:
    def test_liveness(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_readiness_when_ready(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_readiness_when_not_ready(self):
        device = _make_mock_device(initialized=False)
        device.bacnet = None
        app = create_app([device])
        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not_ready"

    def test_readiness_no_devices(self):
        app = create_app([])
        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 503


class TestDeviceEndpoints:
    def test_list_devices(self, client):
        resp = client.get("/api/devices")
        assert resp.status_code == 200
        devices = resp.json()
        assert len(devices) == 1
        assert devices[0]["deviceId"] == 1001
        assert devices[0]["name"] == "TestDevice"
        assert devices[0]["ip"] == "172.18.0.10"

    def test_list_devices_multi(self, client_multi):
        resp = client_multi.get("/api/devices")
        assert resp.status_code == 200
        devices = resp.json()
        assert len(devices) == 2

    def test_list_objects(self, client):
        resp = client.get("/api/devices/1001/objects")
        assert resp.status_code == 200
        objects = resp.json()
        assert len(objects) == 2
        assert objects[0]["name"] == "Zone Temp"

    def test_list_objects_not_found(self, client):
        resp = client.get("/api/devices/9999/objects")
        assert resp.status_code == 404


class TestObjectEndpoints:
    def test_read_object(self, client):
        resp = client.get("/api/devices/1001/objects/analog-input/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Zone Temp"
        assert data["presentValue"] == 72.5

    def test_read_object_not_found(self, client):
        resp = client.get("/api/devices/1001/objects/analog-input/99")
        assert resp.status_code == 404

    def test_write_object(self, client):
        resp = client.put(
            "/api/devices/1001/objects/analog-input/1",
            json={"value": 75.0},
        )
        assert resp.status_code == 200

    def test_write_object_not_found(self, client):
        resp = client.put(
            "/api/devices/1001/objects/analog-input/99",
            json={"value": 75.0},
        )
        assert resp.status_code == 404


class TestNetworkProfileEndpoint:
    def test_update_profile(self, client):
        resp = client.put(
            "/api/devices/1001/network-profile",
            json={"profile": "remote-site"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["networkProfile"] == "remote-site"
        assert data["minDelayMs"] == 50
        assert data["maxDelayMs"] == 200

    def test_update_custom_profile(self, client):
        resp = client.put(
            "/api/devices/1001/network-profile",
            json={
                "profile": "custom",
                "min_delay_ms": 100,
                "max_delay_ms": 500,
                "drop_probability": 0.1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["networkProfile"] == "custom"
        assert data["minDelayMs"] == 100

    def test_update_profile_device_not_found(self, client):
        resp = client.put(
            "/api/devices/9999/network-profile",
            json={"profile": "none"},
        )
        assert resp.status_code == 404
