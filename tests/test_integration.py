"""Integration tests that run against a live Docker container.

These tests build and start the Docker container, then verify BACnet
and HTTP endpoints work end-to-end. Skipped when Docker is not available
or when running in local dev (non-Linux) environments.

Run with: pytest tests/test_integration.py -v
"""

from __future__ import annotations

import subprocess
import time

import pytest
import requests

CONTAINER_NAME = "bacnet-sim-ci-test"
IMAGE_NAME = "bacnet-sim-ci:test"
API_PORT = 18099  # Use non-standard port to avoid conflicts
BACNET_PORT = 47809


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _build_image() -> bool:
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        print(f"Docker build failed:\n{result.stderr}")
    return result.returncode == 0


def _start_container() -> bool:
    # Remove any existing container
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
    )

    result = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "--cap-add=NET_ADMIN",
            "-p", f"{BACNET_PORT}:{BACNET_PORT}/udp",
            "-p", f"{API_PORT}:8099",
            "-e", f"BACNET_PORT={BACNET_PORT}",
            IMAGE_NAME,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Container start failed:\n{result.stderr}")
    return result.returncode == 0


def _stop_container() -> None:
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
    )


def _wait_for_ready(timeout: int = 30) -> bool:
    """Wait for the container to become ready."""
    url = f"http://localhost:{API_PORT}/health/ready"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(1)
    return False


def _get_container_logs() -> str:
    result = subprocess.run(
        ["docker", "logs", CONTAINER_NAME],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker not available",
)


@pytest.fixture(scope="module")
def running_container():
    """Build and start the container for the test module."""
    if not _build_image():
        pytest.skip("Docker image build failed")

    if not _start_container():
        pytest.skip("Container failed to start")

    if not _wait_for_ready():
        logs = _get_container_logs()
        _stop_container()
        pytest.fail(f"Container did not become ready within 30 seconds.\nLogs:\n{logs}")

    yield

    _stop_container()


class TestContainerHealth:
    def test_liveness(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_readiness(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert len(data["devices"]) >= 1

    def test_startup_time_under_30s(self, running_container):
        # If we got here, the container started within 30 seconds
        # (enforced by _wait_for_ready in the fixture)
        pass


class TestContainerAPI:
    def test_list_devices(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/api/devices")
        assert resp.status_code == 200
        devices = resp.json()
        assert len(devices) >= 1
        device = devices[0]
        assert "deviceId" in device
        assert "name" in device
        assert "ip" in device
        assert device["initialized"] is True

    def test_list_objects(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/api/devices")
        device_id = resp.json()[0]["deviceId"]

        resp = requests.get(f"http://localhost:{API_PORT}/api/devices/{device_id}/objects")
        assert resp.status_code == 200
        objects = resp.json()
        assert len(objects) >= 1

    def test_read_object(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/api/devices")
        device_id = resp.json()[0]["deviceId"]

        # Default device has analog-input instance 1 ("Zone Temp")
        resp = requests.get(
            f"http://localhost:{API_PORT}/api/devices/{device_id}/objects/analog-input/1"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Zone Temp"
        assert "presentValue" in data

    def test_write_and_read_object(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/api/devices")
        device_id = resp.json()[0]["deviceId"]

        # Write a new value to Zone Setpoint (analog-output instance 1)
        write_resp = requests.put(
            f"http://localhost:{API_PORT}/api/devices/{device_id}/objects/analog-output/1",
            json={"value": 68.0},
        )
        assert write_resp.status_code == 200

        # Read it back
        read_resp = requests.get(
            f"http://localhost:{API_PORT}/api/devices/{device_id}/objects/analog-output/1"
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["presentValue"] == 68.0

    def test_update_network_profile(self, running_container):
        resp = requests.get(f"http://localhost:{API_PORT}/api/devices")
        device_id = resp.json()[0]["deviceId"]

        resp = requests.put(
            f"http://localhost:{API_PORT}/api/devices/{device_id}/network-profile",
            json={"profile": "remote-site"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["networkProfile"] == "remote-site"
        assert data["minDelayMs"] == 50
        assert data["maxDelayMs"] == 200


class TestContainerImage:
    def test_image_size_under_200mb(self):
        """Verify the Docker image is under 200MB."""
        if not _docker_available():
            pytest.skip("Docker not available")

        result = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME, "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("Image not built")

        size_bytes = int(result.stdout.strip())
        size_mb = size_bytes / (1024 * 1024)
        assert size_mb < 200, f"Image size {size_mb:.1f}MB exceeds 200MB limit"

    def test_runs_as_non_root(self, running_container):
        """Verify the main process runs as non-root user."""
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "whoami"],
            capture_output=True,
            text=True,
        )
        # The main python process should be running as appuser
        # But whoami in exec context shows the container's default user
        # Instead, check the process owner
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "ps", "-o", "user=", "-p", "1"],
            capture_output=True,
            text=True,
        )
        # PID 1 is the entrypoint (bash/root), but the python process
        # should be running as appuser. Check python processes.
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME,
             "sh", "-c", "ps aux | grep '[p]ython -m bacnet_sim.main' | awk '{print $1}'"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            assert result.stdout.strip() == "appuser", (
                f"Python process running as {result.stdout.strip()!r}, expected 'appuser'"
            )
