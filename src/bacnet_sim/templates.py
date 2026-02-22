"""Predefined device templates for common HVAC equipment types."""

from bacnet_sim.config import ObjectConfig, ObjectType

TEMPLATES: dict[str, list[ObjectConfig]] = {
    "ahu": [
        # Analog Inputs - sensor readings
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Supply Air Temp",
            unit="degreesFahrenheit",
            value=55.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=2,
            name="Return Air Temp",
            unit="degreesFahrenheit",
            value=72.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=3,
            name="Mixed Air Temp",
            unit="degreesFahrenheit",
            value=62.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=4,
            name="Outside Air Temp",
            unit="degreesFahrenheit",
            value=85.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=5,
            name="Supply Air Pressure",
            unit="inchesOfWater",
            value=1.5,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=6,
            name="Filter Differential Pressure",
            unit="inchesOfWater",
            value=0.8,
        ),
        # Analog Outputs - setpoints and control signals
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=1,
            name="Supply Air Temp Setpoint",
            unit="degreesFahrenheit",
            value=55.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=2,
            name="Cooling Valve Position",
            unit="percent",
            value=0.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=3,
            name="Heating Valve Position",
            unit="percent",
            value=0.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=4,
            name="Outside Air Damper Position",
            unit="percent",
            value=20.0,
            commandable=True,
        ),
        # Binary Inputs - status feedback
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=1,
            name="Supply Fan Status",
            inactive_text="Off",
            active_text="On",
            value=True,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=2,
            name="Return Fan Status",
            inactive_text="Off",
            active_text="On",
            value=True,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=3,
            name="Filter Alarm",
            inactive_text="Normal",
            active_text="Dirty",
            value=False,
        ),
        # Binary Outputs - commands
        ObjectConfig(
            type=ObjectType.BINARY_OUTPUT,
            instance=1,
            name="Supply Fan Command",
            inactive_text="Off",
            active_text="On",
            value=True,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_OUTPUT,
            instance=2,
            name="Return Fan Command",
            inactive_text="Off",
            active_text="On",
            value=True,
            commandable=True,
        ),
        # Multistate Values - operating modes
        ObjectConfig(
            type=ObjectType.MULTISTATE_VALUE,
            instance=1,
            name="Operating Mode",
            states=["Off", "Auto", "Heating", "Cooling", "Economizer"],
            value=2,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.MULTISTATE_VALUE,
            instance=2,
            name="Occupancy Mode",
            states=["Auto", "Occupied", "Unoccupied", "Standby"],
            value=1,
            commandable=True,
        ),
    ],
    "vav": [
        # Analog Inputs - sensor readings
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Zone Temp",
            unit="degreesFahrenheit",
            value=72.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=2,
            name="Discharge Air Temp",
            unit="degreesFahrenheit",
            value=55.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=3,
            name="Airflow",
            unit="cubicFeetPerMinute",
            value=400.0,
        ),
        # Analog Outputs - setpoints and control signals
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=1,
            name="Cooling Setpoint",
            unit="degreesFahrenheit",
            value=75.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=2,
            name="Heating Setpoint",
            unit="degreesFahrenheit",
            value=70.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=3,
            name="Damper Position",
            unit="percent",
            value=50.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=4,
            name="Reheat Valve Position",
            unit="percent",
            value=0.0,
            commandable=True,
        ),
        # Binary Inputs
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=1,
            name="Occupancy Sensor",
            inactive_text="Unoccupied",
            active_text="Occupied",
            value=True,
        ),
        # Binary Outputs
        ObjectConfig(
            type=ObjectType.BINARY_OUTPUT,
            instance=1,
            name="Reheat Enable",
            inactive_text="Disabled",
            active_text="Enabled",
            value=False,
            commandable=True,
        ),
        # Multistate Values
        ObjectConfig(
            type=ObjectType.MULTISTATE_VALUE,
            instance=1,
            name="Operating Mode",
            states=["Off", "Cooling", "Heating", "Deadband"],
            value=1,
            commandable=True,
        ),
    ],
    "boiler": [
        # Analog Inputs - sensor readings
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Supply Water Temp",
            unit="degreesFahrenheit",
            value=160.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=2,
            name="Return Water Temp",
            unit="degreesFahrenheit",
            value=140.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=3,
            name="Flue Gas Temp",
            unit="degreesFahrenheit",
            value=350.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=4,
            name="Water Pressure",
            unit="poundsForcePerSquareInch",
            value=25.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=5,
            name="Firing Rate",
            unit="percent",
            value=65.0,
        ),
        # Analog Outputs - setpoints
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=1,
            name="Supply Water Temp Setpoint",
            unit="degreesFahrenheit",
            value=160.0,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=2,
            name="Firing Rate Setpoint",
            unit="percent",
            value=65.0,
            commandable=True,
        ),
        # Binary Inputs - status feedback
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=1,
            name="Burner Status",
            inactive_text="Off",
            active_text="Firing",
            value=True,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=2,
            name="Low Water Alarm",
            inactive_text="Normal",
            active_text="Low Water",
            value=False,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=3,
            name="High Limit Alarm",
            inactive_text="Normal",
            active_text="High Limit",
            value=False,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=4,
            name="Pump Status",
            inactive_text="Off",
            active_text="On",
            value=True,
        ),
        # Binary Outputs - commands
        ObjectConfig(
            type=ObjectType.BINARY_OUTPUT,
            instance=1,
            name="Boiler Enable",
            inactive_text="Disabled",
            active_text="Enabled",
            value=True,
            commandable=True,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_OUTPUT,
            instance=2,
            name="Pump Command",
            inactive_text="Off",
            active_text="On",
            value=True,
            commandable=True,
        ),
        # Multistate Values
        ObjectConfig(
            type=ObjectType.MULTISTATE_VALUE,
            instance=1,
            name="Operating Mode",
            states=["Off", "Standby", "Low Fire", "High Fire", "Modulating"],
            value=5,
            commandable=True,
        ),
    ],
    "meter": [
        # Analog Inputs - metered values
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Power",
            unit="kilowatts",
            value=125.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=2,
            name="Energy",
            unit="kilowattHours",
            value=45230.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=3,
            name="Voltage",
            unit="volts",
            value=480.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=4,
            name="Current",
            unit="amperes",
            value=150.5,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=5,
            name="Power Factor",
            unit="noUnits",
            value=0.95,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=6,
            name="Frequency",
            unit="hertz",
            value=60.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=7,
            name="Demand",
            unit="kilowatts",
            value=130.0,
        ),
        ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=8,
            name="Peak Demand",
            unit="kilowatts",
            value=210.0,
        ),
        # Binary Inputs - alarm status
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=1,
            name="Communication Status",
            inactive_text="Offline",
            active_text="Online",
            value=True,
        ),
        ObjectConfig(
            type=ObjectType.BINARY_INPUT,
            instance=2,
            name="Over Current Alarm",
            inactive_text="Normal",
            active_text="Alarm",
            value=False,
        ),
        # Multistate Values
        ObjectConfig(
            type=ObjectType.MULTISTATE_VALUE,
            instance=1,
            name="Metering Mode",
            states=["Normal", "Test", "Calibration"],
            value=1,
            commandable=True,
        ),
    ],
}


def get_template(name: str) -> list[ObjectConfig]:
    """Return a deep copy of the template object list for the given name.

    Raises ValueError if the template name is not recognized.
    """
    if name not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES.keys()))
        raise ValueError(
            f"Unknown template: {name!r}. Available templates: {available}"
        )
    return [obj.model_copy(deep=True) for obj in TEMPLATES[name]]
