"""Virtual IP allocation for multi-device BACnet simulation.

Each BAC0 device instance needs its own IP address on port 47808.
This module manages adding/removing virtual IPs on the container's
network interface so multiple devices can coexist on the same subnet.
"""

from __future__ import annotations

import ipaddress
import logging
import platform
import re
import subprocess

logger = logging.getLogger(__name__)

# Valid Linux interface names: alphanumeric, hyphens, dots, max 15 chars
_INTERFACE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,14}$")


def _validate_interface(interface: str) -> None:
    """Validate network interface name to prevent command injection."""
    if not _INTERFACE_RE.match(interface):
        raise ValueError(f"Invalid network interface name: {interface!r}")


def get_primary_ip(interface: str = "eth0") -> tuple[str, int]:
    """Detect the container's primary IP and prefix length.

    Returns (ip_address, prefix_length) e.g. ("172.18.0.10", 24).
    """
    _validate_interface(interface)

    if platform.system() != "Linux":
        # On non-Linux (local dev), return a placeholder
        logger.warning("Not on Linux; using 127.0.0.1 as primary IP (local dev mode)")
        return "127.0.0.1", 24

    result = subprocess.run(
        ["ip", "-4", "-o", "addr", "show", interface],
        capture_output=True,
        text=True,
        check=True,
    )
    # Output format: "2: eth0    inet 172.18.0.10/24 brd 172.18.0.255 scope global eth0"
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        for i, part in enumerate(parts):
            if part == "inet" and i + 1 < len(parts):
                addr_with_prefix = parts[i + 1]
                network = ipaddress.IPv4Interface(addr_with_prefix)
                return str(network.ip), network.network.prefixlen
    raise RuntimeError(f"Could not determine IP for interface {interface}")


def compute_virtual_ips(
    primary_ip: str,
    prefix_length: int,
    count: int,
) -> list[str]:
    """Compute virtual IPs for additional devices by incrementing the host portion.

    The first device uses the primary IP. This returns IPs for devices 2..N.
    """
    if count <= 1:
        return []

    network = ipaddress.IPv4Network(f"{primary_ip}/{prefix_length}", strict=False)
    primary = ipaddress.IPv4Address(primary_ip)

    virtual_ips: list[str] = []
    candidate = primary + 1
    while len(virtual_ips) < count - 1:
        if candidate == network.broadcast_address:
            raise RuntimeError(
                f"Subnet {network} too small for {count} devices "
                f"(only {network.num_addresses - 2} usable hosts)"
            )
        if candidate != primary and candidate in network:
            virtual_ips.append(str(candidate))
        candidate += 1

    return virtual_ips


def add_virtual_ip(ip: str, prefix_length: int, interface: str = "eth0") -> bool:
    """Add a virtual IP address to the network interface.

    Returns True on success, False on failure.
    Requires CAP_NET_ADMIN capability.
    """
    _validate_interface(interface)

    if platform.system() != "Linux":
        logger.warning("Not on Linux; skipping ip addr add for %s (local dev mode)", ip)
        return True

    try:
        subprocess.run(
            ["ip", "addr", "add", f"{ip}/{prefix_length}", "dev", interface],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Added virtual IP %s/%d on %s", ip, prefix_length, interface)
        return True
    except subprocess.CalledProcessError as e:
        if "RTNETLINK answers: File exists" in e.stderr:
            logger.warning("Virtual IP %s already exists on %s", ip, interface)
            return True
        logger.error("Failed to add virtual IP %s: %s", ip, e.stderr.strip())
        return False


def remove_virtual_ip(ip: str, prefix_length: int, interface: str = "eth0") -> None:
    """Remove a virtual IP address from the network interface."""
    _validate_interface(interface)

    if platform.system() != "Linux":
        return

    try:
        subprocess.run(
            ["ip", "addr", "del", f"{ip}/{prefix_length}", "dev", interface],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Removed virtual IP %s/%d from %s", ip, prefix_length, interface)
    except subprocess.CalledProcessError:
        logger.warning("Could not remove virtual IP %s from %s", ip, interface)


def setup_virtual_ips(
    primary_ip: str,
    prefix_length: int,
    device_count: int,
    explicit_ips: dict[int, str] | None = None,
    interface: str = "eth0",
) -> list[str]:
    """Set up virtual IPs for all devices. Returns the list of IPs (one per device).

    Args:
        primary_ip: The container's primary IP address.
        prefix_length: Subnet prefix length (e.g., 24).
        device_count: Total number of devices.
        explicit_ips: Optional dict mapping device index (0-based) to explicit IP.
        interface: Network interface name.

    Returns:
        List of IP addresses, one per device (index 0 = first device).
    """
    _validate_interface(interface)

    if device_count <= 0:
        return []

    explicit_ips = explicit_ips or {}

    # First device always gets the primary IP (unless explicitly overridden)
    auto_ips = compute_virtual_ips(primary_ip, prefix_length, device_count)

    all_ips: list[str] = []
    auto_idx = 0

    for i in range(device_count):
        if i in explicit_ips:
            ip = explicit_ips[i]
        elif i == 0:
            ip = primary_ip
        else:
            ip = auto_ips[auto_idx]
            auto_idx += 1
        all_ips.append(ip)

    # Detect collisions between explicit and auto-assigned IPs
    if len(set(all_ips)) != len(all_ips):
        seen: set[str] = set()
        dupes: set[str] = set()
        for ip in all_ips:
            if ip in seen:
                dupes.add(ip)
            seen.add(ip)
        raise RuntimeError(f"IP address collision detected: {dupes}")

    # Add virtual IPs (skip the primary, it already exists)
    for ip in all_ips:
        if ip != primary_ip:
            if not add_virtual_ip(ip, prefix_length, interface):
                raise RuntimeError(f"Failed to add virtual IP {ip}")

    return all_ips


def cleanup_virtual_ips(
    ips: list[str],
    primary_ip: str,
    prefix_length: int,
    interface: str = "eth0",
) -> None:
    """Remove all virtual IPs (except the primary) on shutdown."""
    for ip in ips:
        if ip != primary_ip:
            remove_virtual_ip(ip, prefix_length, interface)
