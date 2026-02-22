"""Tests for main entry point (start_devices)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bacnet_sim.config import (
    DeviceConfig,
    GlobalConfig,
    NetworkProfileName,
    ObjectConfig,
    ObjectType,
    SimulatorConfig,
)
from bacnet_sim.devices import SimulatedDevice
from bacnet_sim.lag import LagProfile
from bacnet_sim.main import start_devices

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    device_count: int = 2,
    explicit_ips: dict[int, str] | None = None,
) -> SimulatorConfig:
    """Build a SimulatorConfig with the given number of devices."""
    devices = []
    for i in range(device_count):
        ip = explicit_ips.get(i) if explicit_ips else None
        devices.append(
            DeviceConfig(
                device_id=1001 + i,
                name=f"Device-{i}",
                ip=ip,
                objects=[
                    ObjectConfig(
                        type=ObjectType.ANALOG_INPUT,
                        instance=1,
                        name="Temp",
                        value=72.0,
                    ),
                ],
            )
        )
    return SimulatorConfig(
        global_config=GlobalConfig(
            bacnet_port=47808,
            subnet_mask=24,
            network_profile=NetworkProfileName.NONE,
        ),
        devices=devices,
    )


def _make_simulated_device(device_id: int, ip: str) -> SimulatedDevice:
    """Build a mock SimulatedDevice for return values."""
    config = DeviceConfig(device_id=device_id, name=f"Device-{device_id}")
    return SimulatedDevice(
        config=config,
        ip=ip,
        port=47808,
        bacnet=MagicMock(),
        lag_profile=LagProfile(0, 0, 0),
        initialized=True,
    )


# ---------------------------------------------------------------------------
# start_devices tests
# ---------------------------------------------------------------------------

class TestStartDevices:
    @pytest.mark.asyncio
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_all_devices_started(
        self, mock_create_device, mock_get_primary_ip, mock_setup_ips
    ):
        """All devices created successfully."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 24)
        mock_setup_ips.return_value = ["172.18.0.10", "172.18.0.11"]

        dev0 = _make_simulated_device(1001, "172.18.0.10")
        dev1 = _make_simulated_device(1002, "172.18.0.11")
        mock_create_device.side_effect = [dev0, dev1]

        config = _make_config(device_count=2)
        devices, primary_ip, prefix_length = await start_devices(config)

        assert len(devices) == 2
        assert primary_ip == "172.18.0.10"
        assert prefix_length == 24
        assert mock_create_device.call_count == 2

    @pytest.mark.asyncio
    @patch("bacnet_sim.main.remove_virtual_ip")
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_partial_failure_cleans_up_ips(
        self,
        mock_create_device,
        mock_get_primary_ip,
        mock_setup_ips,
        mock_remove_ip,
    ):
        """When one device fails, its virtual IP is cleaned up."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 24)
        mock_setup_ips.return_value = ["172.18.0.10", "172.18.0.11"]

        dev0 = _make_simulated_device(1001, "172.18.0.10")
        mock_create_device.side_effect = [dev0, Exception("BAC0 failed")]

        config = _make_config(device_count=2)
        devices, primary_ip, prefix_length = await start_devices(config)

        assert len(devices) == 1
        assert devices[0].device_id == 1001
        # The failed device's IP (non-primary) should be cleaned up
        mock_remove_ip.assert_called_once_with("172.18.0.11", 24)

    @pytest.mark.asyncio
    @patch("bacnet_sim.main.remove_virtual_ip")
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_primary_ip_not_cleaned_on_failure(
        self,
        mock_create_device,
        mock_get_primary_ip,
        mock_setup_ips,
        mock_remove_ip,
    ):
        """When device 0 (primary IP) fails, the primary IP is NOT removed."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 24)
        mock_setup_ips.return_value = ["172.18.0.10", "172.18.0.11"]

        dev1 = _make_simulated_device(1002, "172.18.0.11")
        mock_create_device.side_effect = [Exception("BAC0 failed"), dev1]

        config = _make_config(device_count=2)
        devices, _, _ = await start_devices(config)

        assert len(devices) == 1
        assert devices[0].device_id == 1002
        # Primary IP should NOT be passed to remove_virtual_ip
        mock_remove_ip.assert_not_called()

    @pytest.mark.asyncio
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_total_failure_raises_runtime_error(
        self, mock_create_device, mock_get_primary_ip, mock_setup_ips
    ):
        """When ALL devices fail, a RuntimeError is raised."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 24)
        mock_setup_ips.return_value = ["172.18.0.10"]

        mock_create_device.side_effect = Exception("BAC0 failed")

        config = _make_config(device_count=1)
        with pytest.raises(RuntimeError, match="No devices started successfully"):
            await start_devices(config)

    @pytest.mark.asyncio
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_subnet_mask_from_config(
        self, mock_create_device, mock_get_primary_ip, mock_setup_ips
    ):
        """Global config subnet_mask overrides the detected prefix_length."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 16)
        mock_setup_ips.return_value = ["172.18.0.10"]

        dev = _make_simulated_device(1001, "172.18.0.10")
        mock_create_device.return_value = dev

        config = _make_config(device_count=1)
        # config.global_config.subnet_mask is 24; detected was 16
        _, _, prefix_length = await start_devices(config)

        assert prefix_length == 24
        mock_setup_ips.assert_called_once_with(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=1,
            explicit_ips={},
        )

    @pytest.mark.asyncio
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_explicit_ips_passed_through(
        self, mock_create_device, mock_get_primary_ip, mock_setup_ips
    ):
        """Explicit IPs from device configs are forwarded to setup_virtual_ips."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 24)
        mock_setup_ips.return_value = ["172.18.0.50", "172.18.0.11"]

        dev0 = _make_simulated_device(1001, "172.18.0.50")
        dev1 = _make_simulated_device(1002, "172.18.0.11")
        mock_create_device.side_effect = [dev0, dev1]

        config = _make_config(
            device_count=2,
            explicit_ips={0: "172.18.0.50"},
        )
        devices, _, _ = await start_devices(config)

        assert len(devices) == 2
        mock_setup_ips.assert_called_once_with(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=2,
            explicit_ips={0: "172.18.0.50"},
        )

    @pytest.mark.asyncio
    @patch("bacnet_sim.main.setup_virtual_ips")
    @patch("bacnet_sim.main.get_primary_ip")
    @patch("bacnet_sim.main.create_device", new_callable=AsyncMock)
    async def test_create_device_called_with_correct_args(
        self, mock_create_device, mock_get_primary_ip, mock_setup_ips
    ):
        """Verify that create_device is called with the right keyword arguments."""
        mock_get_primary_ip.return_value = ("172.18.0.10", 24)
        mock_setup_ips.return_value = ["172.18.0.10"]

        dev = _make_simulated_device(1001, "172.18.0.10")
        mock_create_device.return_value = dev

        config = _make_config(device_count=1)
        await start_devices(config)

        mock_create_device.assert_called_once_with(
            config=config.devices[0],
            ip="172.18.0.10",
            port=47808,
            subnet_mask=24,
            global_network_profile=NetworkProfileName.NONE,
        )
