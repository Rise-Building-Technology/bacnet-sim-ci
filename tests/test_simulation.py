"""Tests for value simulation engine."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from bacnet_sim.simulation import (
    SimulationConfig,
    SimulationManager,
    SimulationMode,
    SimulationTask,
)


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


def _make_mock_task() -> MagicMock:
    """Return a MagicMock that behaves like a non-done asyncio.Task.

    Both ``done`` and ``cancel`` are plain (non-async) mocks so that calling
    them inside SimulationTask.stop() never produces an unawaited-coroutine.
    The ``spec`` is intentionally restricted to those two attributes so that
    pytest's async-mock introspection does not auto-wrap anything as a
    coroutine.
    """
    mock_task = MagicMock(spec=["done", "cancel"])
    mock_task.done.return_value = False
    mock_task.cancel.return_value = True
    return mock_task


def _patch_create_task():
    """Patch ``asyncio.create_task`` so no event loop is required.

    The coroutine argument passed to ``create_task`` is intentionally closed
    (via ``.close()``) to prevent Python from emitting an unawaited-coroutine
    ``ResourceWarning``.
    """
    def _fake_create_task(coro, **kwargs):
        # Discard the coroutine cleanly so it is not flagged as never-awaited.
        coro.close()
        return _make_mock_task()

    return patch("asyncio.create_task", side_effect=_fake_create_task)


class TestSimulationManager:
    def test_start_creates_task(self):
        with _patch_create_task():
            mgr = SimulationManager()
            config = SimulationConfig(mode=SimulationMode.SINE, interval_seconds=1.0)
            sim = mgr.start(1001, "Zone Temp", config, lambda v: None)
            assert sim.running

    def test_stop_returns_true_when_running(self):
        with _patch_create_task():
            mgr = SimulationManager()
            config = SimulationConfig(mode=SimulationMode.SINE, interval_seconds=1.0)
            mgr.start(1001, "Zone Temp", config, lambda v: None)
            assert mgr.stop(1001, "Zone Temp") is True

    def test_stop_returns_false_when_not_running(self):
        mgr = SimulationManager()
        assert mgr.stop(1001, "Zone Temp") is False

    def test_get_returns_none_when_not_running(self):
        mgr = SimulationManager()
        assert mgr.get(1001, "Zone Temp") is None

    def test_get_returns_task_when_running(self):
        with _patch_create_task():
            mgr = SimulationManager()
            config = SimulationConfig(mode=SimulationMode.SINE, interval_seconds=1.0)
            mgr.start(1001, "Zone Temp", config, lambda v: None)
            assert mgr.get(1001, "Zone Temp") is not None

    def test_stop_all(self):
        with _patch_create_task():
            mgr = SimulationManager()
            config = SimulationConfig(mode=SimulationMode.SINE, interval_seconds=1.0)
            mgr.start(1001, "Temp1", config, lambda v: None)
            mgr.start(1001, "Temp2", config, lambda v: None)
            mgr.stop_all()
            assert mgr.get(1001, "Temp1") is None
            assert mgr.get(1001, "Temp2") is None

    def test_start_replaces_existing(self):
        with _patch_create_task():
            mgr = SimulationManager()
            config1 = SimulationConfig(
                mode=SimulationMode.SINE, interval_seconds=1.0,
            )
            config2 = SimulationConfig(
                mode=SimulationMode.STEP, interval_seconds=2.0, values=[1, 2],
            )
            mgr.start(1001, "Zone Temp", config1, lambda v: None)
            mgr.start(1001, "Zone Temp", config2, lambda v: None)
            sim = mgr.get(1001, "Zone Temp")
            assert sim is not None
            assert sim.config.mode == SimulationMode.STEP
