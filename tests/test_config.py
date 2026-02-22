"""Tests for configuration loading and validation."""


import pytest
from pydantic import ValidationError

from bacnet_sim.config import (
    DeviceConfig,
    GlobalConfig,
    NetworkCustomConfig,
    NetworkProfileName,
    ObjectConfig,
    ObjectType,
    SimulatorConfig,
    load_config,
)


class TestObjectConfig:
    def test_valid_analog_input(self):
        obj = ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Zone Temp",
            unit="degreesFahrenheit",
            value=72.5,
        )
        assert obj.type == ObjectType.ANALOG_INPUT
        assert obj.instance == 1
        assert obj.value == 72.5

    def test_negative_instance_rejected(self):
        with pytest.raises(ValidationError):
            ObjectConfig(
                type=ObjectType.ANALOG_INPUT,
                instance=-1,
                name="Bad",
            )

    def test_commandable_flag(self):
        obj = ObjectConfig(
            type=ObjectType.ANALOG_OUTPUT,
            instance=1,
            name="Setpoint",
            commandable=True,
        )
        assert obj.commandable is True

    def test_unsupported_object_type_rejected(self):
        with pytest.raises(ValidationError):
            ObjectConfig(
                type="schedule",
                instance=1,
                name="Test Schedule",
            )

    def test_unsupported_trend_log_type_rejected(self):
        with pytest.raises(ValidationError):
            ObjectConfig(
                type="trend-log",
                instance=1,
                name="Test Trend Log",
            )


class TestDeviceConfig:
    def test_valid_device(self):
        device = DeviceConfig(
            device_id=1001,
            name="AHU-1",
            objects=[
                ObjectConfig(type=ObjectType.ANALOG_INPUT, instance=1, name="Temp"),
                ObjectConfig(type=ObjectType.BINARY_OUTPUT, instance=1, name="Fan"),
            ],
        )
        assert device.device_id == 1001
        assert len(device.objects) == 2

    def test_duplicate_object_names_rejected(self):
        with pytest.raises(ValidationError, match="Duplicate object names"):
            DeviceConfig(
                device_id=1001,
                name="AHU-1",
                objects=[
                    ObjectConfig(type=ObjectType.ANALOG_INPUT, instance=1, name="Temp"),
                    ObjectConfig(type=ObjectType.ANALOG_INPUT, instance=2, name="Temp"),
                ],
            )

    def test_duplicate_type_instance_rejected(self):
        with pytest.raises(ValidationError, match="Duplicate object"):
            DeviceConfig(
                device_id=1001,
                name="AHU-1",
                objects=[
                    ObjectConfig(type=ObjectType.ANALOG_INPUT, instance=1, name="Temp1"),
                    ObjectConfig(type=ObjectType.ANALOG_INPUT, instance=1, name="Temp2"),
                ],
            )

    def test_explicit_ip(self):
        device = DeviceConfig(
            device_id=1001,
            name="AHU-1",
            ip="172.18.0.50",
        )
        assert device.ip == "172.18.0.50"


class TestSimulatorConfig:
    def test_duplicate_device_ids_rejected(self):
        with pytest.raises(ValidationError, match="Duplicate device IDs"):
            SimulatorConfig(
                devices=[
                    DeviceConfig(device_id=1001, name="A"),
                    DeviceConfig(device_id=1001, name="B"),
                ]
            )

    def test_duplicate_explicit_ips_rejected(self):
        with pytest.raises(ValidationError, match="Duplicate explicit IPs"):
            SimulatorConfig(
                devices=[
                    DeviceConfig(device_id=1001, name="A", ip="172.18.0.10"),
                    DeviceConfig(device_id=1002, name="B", ip="172.18.0.10"),
                ]
            )

    def test_valid_multi_device(self):
        config = SimulatorConfig(
            devices=[
                DeviceConfig(device_id=1001, name="A"),
                DeviceConfig(device_id=1002, name="B"),
                DeviceConfig(device_id=1003, name="C"),
            ]
        )
        assert len(config.devices) == 3


class TestNetworkCustomConfig:
    def test_valid_custom(self):
        c = NetworkCustomConfig(min_delay_ms=50, max_delay_ms=200, drop_probability=0.05)
        assert c.min_delay_ms == 50

    def test_invalid_drop_probability(self):
        with pytest.raises(ValidationError):
            NetworkCustomConfig(min_delay_ms=0, max_delay_ms=0, drop_probability=1.5)

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(ValidationError):
            NetworkCustomConfig(min_delay_ms=200, max_delay_ms=100, drop_probability=0)


class TestGlobalConfig:
    def test_defaults(self):
        g = GlobalConfig()
        assert g.api_port == 8099
        assert g.bacnet_port == 47808
        assert g.subnet_mask == 24
        assert g.network_profile == NetworkProfileName.NONE


class TestLoadConfig:
    def test_load_from_yaml(self, sample_device_yaml):
        config = load_config(str(sample_device_yaml))
        assert len(config.devices) == 1
        assert config.devices[0].device_id == 1001
        assert len(config.devices[0].objects) == 2

    def test_load_multi_device_yaml(self, multi_device_yaml):
        config = load_config(str(multi_device_yaml))
        assert len(config.devices) == 3
        assert config.devices[0].device_id == 1001
        assert config.devices[1].device_id == 1002
        assert config.devices[2].device_id == 1003

    def test_load_defaults_when_no_file(self):
        config = load_config(None)
        assert len(config.devices) == 1
        assert config.devices[0].device_id == 1001
        assert config.devices[0].name == "HVAC Controller"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.yaml")

    def test_env_var_overrides(self, sample_device_yaml, monkeypatch):
        monkeypatch.setenv("BACNET_DEVICE_ID", "9999")
        monkeypatch.setenv("API_PORT", "9090")
        config = load_config(str(sample_device_yaml))
        assert config.devices[0].device_id == 9999
        assert config.global_config.api_port == 9090

    def test_config_file_env_var(self, sample_device_yaml, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE", str(sample_device_yaml))
        config = load_config(None)
        assert len(config.devices) == 1
        assert config.devices[0].device_id == 1001
