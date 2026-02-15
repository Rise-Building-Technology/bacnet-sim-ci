"""Network lag simulation for BACnet responses.

Applies configurable latency and packet drops to simulate real-world
network conditions. Each device can have its own lag profile.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

from bacnet_sim.config import NetworkCustomConfig, NetworkProfileName


@dataclass
class LagProfile:
    """Defines network simulation parameters for a device."""

    min_delay_ms: float
    max_delay_ms: float
    drop_probability: float

    async def apply(self) -> bool:
        """Apply lag to the current request.

        Returns True if the request should proceed, False if it should be dropped.
        """
        # Check for drop
        if self.drop_probability > 0 and random.random() < self.drop_probability:
            return False

        # Apply delay
        if self.max_delay_ms > 0:
            delay_ms = random.uniform(self.min_delay_ms, self.max_delay_ms)
            await asyncio.sleep(delay_ms / 1000.0)

        return True


# Predefined profiles matching the plan
PROFILES: dict[NetworkProfileName, LagProfile] = {
    NetworkProfileName.NONE: LagProfile(
        min_delay_ms=0, max_delay_ms=0, drop_probability=0.0
    ),
    NetworkProfileName.LOCAL_NETWORK: LagProfile(
        min_delay_ms=0, max_delay_ms=10, drop_probability=0.0
    ),
    NetworkProfileName.REMOTE_SITE: LagProfile(
        min_delay_ms=50, max_delay_ms=200, drop_probability=0.01
    ),
    NetworkProfileName.UNRELIABLE_LINK: LagProfile(
        min_delay_ms=200, max_delay_ms=1000, drop_probability=0.10
    ),
}


def get_lag_profile(
    profile_name: NetworkProfileName,
    custom_config: NetworkCustomConfig | None = None,
) -> LagProfile:
    """Get a LagProfile for the given profile name.

    For 'custom' profiles, uses the provided NetworkCustomConfig.
    """
    if profile_name == NetworkProfileName.CUSTOM:
        if custom_config is None:
            raise ValueError("Custom network profile requires network_custom configuration")
        return LagProfile(
            min_delay_ms=custom_config.min_delay_ms,
            max_delay_ms=custom_config.max_delay_ms,
            drop_probability=custom_config.drop_probability,
        )
    return PROFILES.get(profile_name, PROFILES[NetworkProfileName.NONE])
