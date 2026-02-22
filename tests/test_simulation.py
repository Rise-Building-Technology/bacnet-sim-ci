"""Tests for value simulation engine."""

import asyncio

import pytest

from bacnet_sim.simulation import SimulationConfig, SimulationMode, SimulationTask


class TestSimulationTask:
    @pytest.mark.asyncio
    async def test_sine_simulation(self):
        values = []
        config = SimulationConfig(
            mode=SimulationMode.SINE,
            interval_seconds=0.05,
            center=72.0,
            amplitude=5.0,
            period_seconds=1.0,
        )
        sim = SimulationTask(config=config)
        sim._task = asyncio.create_task(sim.run(lambda v: values.append(v)))
        await asyncio.sleep(0.3)
        sim.stop()
        assert len(values) >= 2
        # Values should be around center
        for v in values:
            assert 67.0 <= v <= 77.0

    @pytest.mark.asyncio
    async def test_step_simulation(self):
        values = []
        config = SimulationConfig(
            mode=SimulationMode.STEP,
            interval_seconds=0.05,
            values=[1, 2, 3],
        )
        sim = SimulationTask(config=config)
        sim._task = asyncio.create_task(sim.run(lambda v: values.append(v)))
        await asyncio.sleep(0.2)
        sim.stop()
        assert len(values) >= 2
        # Should cycle through 1, 2, 3
        assert values[0] == 1
        assert values[1] == 2

    @pytest.mark.asyncio
    async def test_random_walk_bounded(self):
        values = []
        config = SimulationConfig(
            mode=SimulationMode.RANDOM_WALK,
            interval_seconds=0.05,
            initial=50.0,
            step_size=2.0,
            min_value=40.0,
            max_value=60.0,
        )
        sim = SimulationTask(config=config)
        sim._task = asyncio.create_task(sim.run(lambda v: values.append(v)))
        await asyncio.sleep(0.3)
        sim.stop()
        assert len(values) >= 2
        for v in values:
            assert 40.0 <= v <= 60.0

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        values = []
        config = SimulationConfig(
            mode=SimulationMode.STEP,
            interval_seconds=0.05,
            values=[1, 2, 3],
        )
        sim = SimulationTask(config=config)
        sim._task = asyncio.create_task(sim.run(lambda v: values.append(v)))
        await asyncio.sleep(0.15)
        count_before = len(values)
        sim.pause()
        await asyncio.sleep(0.15)
        count_during_pause = len(values)
        assert count_during_pause == count_before  # No new values while paused
        sim.resume()
        await asyncio.sleep(0.15)
        sim.stop()
        assert len(values) > count_during_pause  # Values resumed
