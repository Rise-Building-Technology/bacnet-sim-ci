"""Tests for device templates and template-based DeviceConfig creation."""

import pytest
from pydantic import ValidationError

from bacnet_sim.config import DeviceConfig, ObjectConfig, ObjectType
from bacnet_sim.templates import TEMPLATES, get_template


class TestGetTemplate:
    def test_ahu_template_loads(self):
        objects = get_template("ahu")
        assert len(objects) > 0
        types_present = {obj.type for obj in objects}
        assert ObjectType.ANALOG_INPUT in types_present
        assert ObjectType.ANALOG_OUTPUT in types_present
        assert ObjectType.BINARY_INPUT in types_present
        assert ObjectType.BINARY_OUTPUT in types_present
        assert ObjectType.MULTISTATE_VALUE in types_present

    def test_vav_template_loads(self):
        objects = get_template("vav")
        assert len(objects) > 0
        names = {obj.name for obj in objects}
        assert "Zone Temp" in names
        assert "Damper Position" in names

    def test_boiler_template_loads(self):
        objects = get_template("boiler")
        assert len(objects) > 0
        names = {obj.name for obj in objects}
        assert "Supply Water Temp" in names
        assert "Burner Status" in names

    def test_meter_template_loads(self):
        objects = get_template("meter")
        assert len(objects) > 0
        names = {obj.name for obj in objects}
        assert "Power" in names
        assert "Energy" in names
        assert "Voltage" in names

    def test_unknown_template_raises_error(self):
        with pytest.raises(ValueError, match="Unknown template"):
            get_template("nonexistent")

    def test_error_message_lists_available_templates(self):
        with pytest.raises(ValueError, match="ahu") as exc_info:
            get_template("nonexistent")
        msg = str(exc_info.value)
        for name in TEMPLATES:
            assert name in msg

    def test_get_template_returns_deep_copy(self):
        objects_a = get_template("vav")
        objects_b = get_template("vav")
        # Mutating one should not affect the other
        objects_a[0].value = 999.0
        assert objects_b[0].value != 999.0

    def test_all_templates_have_unique_type_instance_pairs(self):
        for name, objects in TEMPLATES.items():
            seen: set[tuple[ObjectType, int]] = set()
            for obj in objects:
                key = (obj.type, obj.instance)
                assert key not in seen, (
                    f"Template {name!r} has duplicate {obj.type.value}:{obj.instance}"
                )
                seen.add(key)

    def test_all_templates_have_unique_names(self):
        for name, objects in TEMPLATES.items():
            names = [obj.name for obj in objects]
            assert len(names) == len(set(names)), (
                f"Template {name!r} has duplicate object names"
            )

    def test_all_templates_use_fahrenheit_for_temperature(self):
        for name, objects in TEMPLATES.items():
            for obj in objects:
                if obj.unit is not None and "degree" in obj.unit.lower():
                    assert obj.unit == "degreesFahrenheit", (
                        f"Template {name!r} object {obj.name!r} uses {obj.unit} "
                        f"instead of degreesFahrenheit"
                    )


class TestDeviceConfigWithTemplate:
    def test_template_expands_objects(self):
        device = DeviceConfig(
            device_id=2001,
            name="AHU-1",
            template="ahu",
        )
        assert len(device.objects) == len(TEMPLATES["ahu"])
        names = {obj.name for obj in device.objects}
        assert "Supply Air Temp" in names
        assert "Supply Fan Command" in names

    def test_template_with_explicit_objects_merged(self):
        custom_temp = ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Custom Supply Temp",
            unit="degreesFahrenheit",
            value=60.0,
        )
        device = DeviceConfig(
            device_id=2001,
            name="AHU-1",
            template="ahu",
            objects=[custom_temp],
        )
        # The explicit object should replace the template one with same type+instance
        template_count = len(TEMPLATES["ahu"])
        assert len(device.objects) == template_count
        # Find the AI:1 object - it should be the custom one
        ai1 = device.find_object("analog-input", 1)
        assert ai1 is not None
        assert ai1.name == "Custom Supply Temp"
        assert ai1.value == 60.0

    def test_template_with_additional_explicit_object(self):
        extra_obj = ObjectConfig(
            type=ObjectType.CHARACTER_STRING,
            instance=1,
            name="Description",
            value="Main AHU on roof",
        )
        device = DeviceConfig(
            device_id=2001,
            name="AHU-1",
            template="ahu",
            objects=[extra_obj],
        )
        # Should have all template objects plus the extra one
        assert len(device.objects) == len(TEMPLATES["ahu"]) + 1
        cs1 = device.find_object("character-string", 1)
        assert cs1 is not None
        assert cs1.name == "Description"

    def test_unknown_template_in_device_config_raises_error(self):
        with pytest.raises(ValidationError, match="Unknown template"):
            DeviceConfig(
                device_id=2001,
                name="Bad Device",
                template="nonexistent",
            )

    def test_no_template_works_as_before(self):
        device = DeviceConfig(
            device_id=2001,
            name="Simple Device",
            objects=[
                ObjectConfig(
                    type=ObjectType.ANALOG_INPUT,
                    instance=1,
                    name="Temp",
                    unit="degreesFahrenheit",
                    value=72.0,
                ),
            ],
        )
        assert len(device.objects) == 1
        assert device.template is None

    def test_vav_template_in_device_config(self):
        device = DeviceConfig(
            device_id=3001,
            name="VAV-1",
            template="vav",
        )
        assert len(device.objects) == len(TEMPLATES["vav"])
        assert device.find_object("analog-input", 1) is not None

    def test_boiler_template_in_device_config(self):
        device = DeviceConfig(
            device_id=4001,
            name="Boiler-1",
            template="boiler",
        )
        assert len(device.objects) == len(TEMPLATES["boiler"])

    def test_meter_template_in_device_config(self):
        device = DeviceConfig(
            device_id=5001,
            name="Meter-1",
            template="meter",
        )
        assert len(device.objects) == len(TEMPLATES["meter"])
