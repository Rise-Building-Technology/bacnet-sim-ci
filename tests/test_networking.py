"""Tests for virtual IP networking module."""

import subprocess
from unittest.mock import patch

import pytest

from bacnet_sim.networking import _ip_exists, add_virtual_ip, compute_virtual_ips, setup_virtual_ips


class TestComputeVirtualIps:
    def test_single_device_no_virtual_ips(self):
        ips = compute_virtual_ips("172.18.0.10", 24, count=1)
        assert ips == []

    def test_two_devices(self):
        ips = compute_virtual_ips("172.18.0.10", 24, count=2)
        assert ips == ["172.18.0.11"]

    def test_five_devices(self):
        ips = compute_virtual_ips("172.18.0.10", 24, count=5)
        assert ips == ["172.18.0.11", "172.18.0.12", "172.18.0.13", "172.18.0.14"]

    def test_sequential_from_primary(self):
        ips = compute_virtual_ips("172.18.0.50", 24, count=3)
        assert ips == ["172.18.0.51", "172.18.0.52"]

    def test_subnet_too_small(self):
        # /30 subnet has only 2 usable hosts
        with pytest.raises(RuntimeError, match="too small"):
            compute_virtual_ips("10.0.0.1", 30, count=5)

    def test_zero_devices(self):
        ips = compute_virtual_ips("172.18.0.10", 24, count=0)
        assert ips == []


class TestSetupVirtualIps:
    def test_single_device_returns_primary(self):
        ips = setup_virtual_ips(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=1,
        )
        assert ips == ["172.18.0.10"]

    @patch("bacnet_sim.networking.add_virtual_ip", return_value=True)
    def test_multi_device_auto_assign(self, mock_add):
        ips = setup_virtual_ips(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=3,
        )
        assert ips == ["172.18.0.10", "172.18.0.11", "172.18.0.12"]
        assert mock_add.call_count == 2

    @patch("bacnet_sim.networking.add_virtual_ip", return_value=True)
    def test_explicit_ip_override(self, mock_add):
        ips = setup_virtual_ips(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=3,
            explicit_ips={1: "172.18.0.50"},
        )
        assert ips[0] == "172.18.0.10"
        assert ips[1] == "172.18.0.50"
        assert ips[2] == "172.18.0.11"

    def test_zero_devices(self):
        ips = setup_virtual_ips(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=0,
        )
        assert ips == []

    @patch("bacnet_sim.networking.add_virtual_ip", return_value=True)
    def test_explicit_ip_collision_detected(self, mock_add):
        with pytest.raises(RuntimeError, match="IP address collision"):
            setup_virtual_ips(
                primary_ip="172.18.0.10",
                prefix_length=24,
                device_count=3,
                explicit_ips={1: "172.18.0.11"},  # Collides with auto-assigned
            )

    @patch("bacnet_sim.networking.add_virtual_ip", return_value=False)
    def test_failed_ip_add_raises(self, mock_add):
        with pytest.raises(RuntimeError, match="Failed to add virtual IP"):
            setup_virtual_ips(
                primary_ip="172.18.0.10",
                prefix_length=24,
                device_count=2,
            )


class TestIpExists:
    @patch("bacnet_sim.networking.platform.system", return_value="Linux")
    @patch("bacnet_sim.networking.subprocess.run")
    def test_ip_found(self, mock_run, mock_system):
        mock_run.return_value.stdout = (
            "2: eth0    inet 172.18.0.10/24 brd 172.18.0.255 scope global eth0\n"
            "2: eth0    inet 172.18.0.11/24 brd 172.18.0.255 scope global secondary eth0\n"
        )
        assert _ip_exists("172.18.0.11", "eth0") is True

    @patch("bacnet_sim.networking.platform.system", return_value="Linux")
    @patch("bacnet_sim.networking.subprocess.run")
    def test_ip_not_found(self, mock_run, mock_system):
        mock_run.return_value.stdout = (
            "2: eth0    inet 172.18.0.10/24 brd 172.18.0.255 scope global eth0\n"
        )
        assert _ip_exists("172.18.0.11", "eth0") is False

    @patch("bacnet_sim.networking.platform.system", return_value="Windows")
    def test_non_linux_returns_false(self, mock_system):
        assert _ip_exists("172.18.0.11", "eth0") is False

    @patch("bacnet_sim.networking.platform.system", return_value="Linux")
    @patch(
        "bacnet_sim.networking.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "ip"),
    )
    def test_command_failure_returns_false(self, mock_run, mock_system):
        assert _ip_exists("172.18.0.11", "eth0") is False


class TestAddVirtualIpEntrypointFallback:
    """Test add_virtual_ip handles IPs already set up by the entrypoint."""

    @patch("bacnet_sim.networking._ip_exists", return_value=True)
    @patch("bacnet_sim.networking.platform.system", return_value="Linux")
    @patch("bacnet_sim.networking.subprocess.run")
    def test_permitted_err_ip_exists_returns_true(
        self, mock_run, mock_system, mock_exists,
    ):
        """'Operation not permitted' + IP exists → True."""
        mock_run.side_effect = subprocess.CalledProcessError(
            2, "ip", stderr="RTNETLINK answers: Operation not permitted\n"
        )
        assert add_virtual_ip("172.18.0.11", 24) is True

    @patch("bacnet_sim.networking._ip_exists", return_value=False)
    @patch("bacnet_sim.networking.platform.system", return_value="Linux")
    @patch("bacnet_sim.networking.subprocess.run")
    def test_permitted_err_ip_missing_returns_false(
        self, mock_run, mock_system, mock_exists,
    ):
        """'Operation not permitted' + IP missing → False."""
        mock_run.side_effect = subprocess.CalledProcessError(
            2, "ip", stderr="RTNETLINK answers: Operation not permitted\n"
        )
        assert add_virtual_ip("172.18.0.11", 24) is False
