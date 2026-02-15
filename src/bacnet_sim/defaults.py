"""Default HVAC controller device configuration."""

from bacnet_sim.config import (
    DeviceConfig,
    GlobalConfig,
    ObjectConfig,
    ObjectType,
    SimulatorConfig,
)


def default_config() -> SimulatorConfig:
    """Return the built-in default simulator config: a single generic HVAC controller."""
    return SimulatorConfig(
        global_config=GlobalConfig(),
        devices=[
            DeviceConfig(
                device_id=1001,
                name="HVAC Controller",
                objects=[
                    ObjectConfig(
                        type=ObjectType.ANALOG_INPUT,
                        instance=1,
                        name="Zone Temp",
                        unit="degreesCelsius",
                        value=72.5,
                    ),
                    ObjectConfig(
                        type=ObjectType.ANALOG_INPUT,
                        instance=2,
                        name="Supply Air Temp",
                        unit="degreesCelsius",
                        value=55.0,
                    ),
                    ObjectConfig(
                        type=ObjectType.ANALOG_OUTPUT,
                        instance=1,
                        name="Zone Setpoint",
                        unit="degreesCelsius",
                        value=72.0,
                        commandable=True,
                    ),
                    ObjectConfig(
                        type=ObjectType.BINARY_INPUT,
                        instance=1,
                        name="Fan Status",
                        inactive_text="Off",
                        active_text="On",
                        value=True,
                    ),
                    ObjectConfig(
                        type=ObjectType.BINARY_OUTPUT,
                        instance=1,
                        name="Fan Command",
                        inactive_text="Off",
                        active_text="On",
                        value=False,
                        commandable=True,
                    ),
                    ObjectConfig(
                        type=ObjectType.ANALOG_OUTPUT,
                        instance=2,
                        name="Damper Position",
                        unit="percent",
                        value=50.0,
                        commandable=True,
                    ),
                    ObjectConfig(
                        type=ObjectType.MULTISTATE_VALUE,
                        instance=1,
                        name="Occupancy Mode",
                        states=["Auto", "Occupied", "Unoccupied", "Standby"],
                        value=1,
                        commandable=True,
                    ),
                    ObjectConfig(
                        type=ObjectType.CHARACTER_STRING,
                        instance=1,
                        name="Device Status",
                        value="Normal",
                        commandable=True,
                    ),
                ],
            )
        ],
    )
