"""Value simulation engine for dynamic BACnet object values."""

from __future__ import annotations

import asyncio
import logging
import math
import random
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SimulationMode(StrEnum):
    SINE = "sine"
    RANDOM_WALK = "random-walk"
    STEP = "step"


@dataclass
class SimulationConfig:
    mode: SimulationMode
    interval_seconds: float = 5.0
    # Sine params
    center: float = 0.0
    amplitude: float = 1.0
    period_seconds: float = 60.0
    # Random walk params
    initial: float = 0.0
    step_size: float = 1.0
    min_value: float = float("-inf")
    max_value: float = float("inf")
    # Step params
    values: list[Any] = field(default_factory=list)


@dataclass
class SimulationTask:
    config: SimulationConfig
    _task: asyncio.Task | None = field(default=None, repr=False)
    _paused: bool = False
    _elapsed: float = 0.0
    _step_index: int = 0
    _current: float = 0.0

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def run(self, set_value: Any) -> None:
        """Run the simulation loop, calling set_value(v) to update the object."""
        self._current = (
            self.config.initial
            if self.config.mode == SimulationMode.RANDOM_WALK
            else self.config.center
        )
        self._elapsed = 0.0
        self._step_index = 0

        try:
            while True:
                await asyncio.sleep(self.config.interval_seconds)
                if self._paused:
                    continue
                self._elapsed += self.config.interval_seconds

                if self.config.mode == SimulationMode.SINE:
                    value = self.config.center + self.config.amplitude * math.sin(
                        2 * math.pi * self._elapsed / self.config.period_seconds
                    )
                elif self.config.mode == SimulationMode.RANDOM_WALK:
                    delta = random.uniform(-self.config.step_size, self.config.step_size)
                    self._current = max(
                        self.config.min_value,
                        min(self.config.max_value, self._current + delta),
                    )
                    value = self._current
                elif self.config.mode == SimulationMode.STEP:
                    if not self.config.values:
                        continue
                    value = self.config.values[self._step_index % len(self.config.values)]
                    self._step_index += 1
                else:
                    continue

                try:
                    set_value(value)
                except Exception as e:
                    logger.warning("Failed to set simulated value: %s", e)
        except asyncio.CancelledError:
            pass


class SimulationManager:
    """Manages simulation tasks for multiple objects."""

    def __init__(self) -> None:
        self._tasks: dict[str, SimulationTask] = {}  # key: "deviceId:objName"

    def _key(self, device_id: int, obj_name: str) -> str:
        return f"{device_id}:{obj_name}"

    def start(
        self,
        device_id: int,
        obj_name: str,
        config: SimulationConfig,
        set_value: Any,
    ) -> SimulationTask:
        key = self._key(device_id, obj_name)
        # Stop existing simulation if any
        if key in self._tasks:
            self._tasks[key].stop()

        sim = SimulationTask(config=config)
        sim._task = asyncio.create_task(sim.run(set_value))
        self._tasks[key] = sim
        return sim

    def stop(self, device_id: int, obj_name: str) -> bool:
        key = self._key(device_id, obj_name)
        if key in self._tasks:
            self._tasks[key].stop()
            del self._tasks[key]
            return True
        return False

    def get(self, device_id: int, obj_name: str) -> SimulationTask | None:
        return self._tasks.get(self._key(device_id, obj_name))

    def stop_all(self) -> None:
        for sim in self._tasks.values():
            sim.stop()
        self._tasks.clear()
