"""Tests for virtual IP networking module."""

import pytest

from bacnet_sim.networking import compute_virtual_ips, setup_virtual_ips


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
        """On non-Linux, add_virtual_ip is a no-op, so this tests the logic."""
        ips = setup_virtual_ips(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=1,
        )
        assert ips == ["172.18.0.10"]

    def test_multi_device_auto_assign(self):
        ips = setup_virtual_ips(
            primary_ip="172.18.0.10",
            prefix_length=24,
            device_count=3,
        )
        assert ips == ["172.18.0.10", "172.18.0.11", "172.18.0.12"]

    def test_explicit_ip_override(self):
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
