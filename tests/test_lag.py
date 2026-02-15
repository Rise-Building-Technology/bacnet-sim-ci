"""Tests for network lag simulation."""

import time

import pytest

from bacnet_sim.config import NetworkCustomConfig, NetworkProfileName
from bacnet_sim.lag import PROFILES, LagProfile, get_lag_profile


class TestLagProfile:
    @pytest.mark.asyncio
    async def test_no_delay(self):
        profile = LagProfile(min_delay_ms=0, max_delay_ms=0, drop_probability=0)
        start = time.monotonic()
        result = await profile.apply()
        elapsed = time.monotonic() - start
        assert result is True
        assert elapsed < 0.05  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_delay_applied(self):
        profile = LagProfile(min_delay_ms=50, max_delay_ms=100, drop_probability=0)
        start = time.monotonic()
        result = await profile.apply()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert result is True
        assert elapsed_ms >= 45  # Allow small timing margin

    @pytest.mark.asyncio
    async def test_drop_always(self):
        profile = LagProfile(min_delay_ms=0, max_delay_ms=0, drop_probability=1.0)
        result = await profile.apply()
        assert result is False

    @pytest.mark.asyncio
    async def test_drop_never(self):
        profile = LagProfile(min_delay_ms=0, max_delay_ms=0, drop_probability=0.0)
        # Run 100 times, should never drop
        for _ in range(100):
            result = await profile.apply()
            assert result is True

    @pytest.mark.asyncio
    async def test_drop_probability(self):
        profile = LagProfile(min_delay_ms=0, max_delay_ms=0, drop_probability=0.5)
        results = [await profile.apply() for _ in range(1000)]
        drop_rate = results.count(False) / len(results)
        # Should be roughly 50% drops (allow wide margin for randomness)
        assert 0.3 < drop_rate < 0.7


class TestGetLagProfile:
    def test_none_profile(self):
        profile = get_lag_profile(NetworkProfileName.NONE)
        assert profile.min_delay_ms == 0
        assert profile.max_delay_ms == 0
        assert profile.drop_probability == 0

    def test_local_network(self):
        profile = get_lag_profile(NetworkProfileName.LOCAL_NETWORK)
        assert profile.max_delay_ms == 10
        assert profile.drop_probability == 0

    def test_remote_site(self):
        profile = get_lag_profile(NetworkProfileName.REMOTE_SITE)
        assert profile.min_delay_ms == 50
        assert profile.max_delay_ms == 200
        assert profile.drop_probability == 0.01

    def test_unreliable_link(self):
        profile = get_lag_profile(NetworkProfileName.UNRELIABLE_LINK)
        assert profile.min_delay_ms == 200
        assert profile.max_delay_ms == 1000
        assert profile.drop_probability == 0.10

    def test_custom_profile(self):
        custom = NetworkCustomConfig(
            min_delay_ms=100, max_delay_ms=500, drop_probability=0.05
        )
        profile = get_lag_profile(NetworkProfileName.CUSTOM, custom)
        assert profile.min_delay_ms == 100
        assert profile.max_delay_ms == 500
        assert profile.drop_probability == 0.05

    def test_custom_without_config_raises(self):
        with pytest.raises(ValueError, match="requires network_custom"):
            get_lag_profile(NetworkProfileName.CUSTOM, None)

    def test_predefined_profiles_exist(self):
        for name in [
            NetworkProfileName.NONE,
            NetworkProfileName.LOCAL_NETWORK,
            NetworkProfileName.REMOTE_SITE,
            NetworkProfileName.UNRELIABLE_LINK,
        ]:
            assert name in PROFILES
