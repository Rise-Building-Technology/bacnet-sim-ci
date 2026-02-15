"""Configuration models and loading for the BACnet simulator."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator


class ObjectType(str, Enum):
    ANALOG_INPUT = "analog-input"
    ANALOG_OUTPUT = "analog-output"
    BINARY_INPUT = "binary-input"
    BINARY_OUTPUT = "binary-output"
    MULTISTATE_VALUE = "multistate-value"
    CHARACTER_STRING = "character-string"
    SCHEDULE = "schedule"
    TREND_LOG = "trend-log"


class NetworkProfileName(str, Enum):
    LOCAL_NETWORK = "local-network"
    REMOTE_SITE = "remote-site"
    UNRELIABLE_LINK = "unreliable-link"
    CUSTOM = "custom"
    NONE = "none"


class NetworkCustomConfig(BaseModel):
    min_delay_ms: float = 0
    max_delay_ms: float = 0
    drop_probability: float = 0.0

    @field_validator("drop_probability")
    @classmethod
    def validate_drop_probability(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("drop_probability must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_delay_range(self) -> NetworkCustomConfig:
        if self.min_delay_ms > self.max_delay_ms:
            raise ValueError("min_delay_ms must be <= max_delay_ms")
        return self


class ObjectConfig(BaseModel):
    type: ObjectType
    instance: int
    name: str
    unit: str | None = None
    value: Any = None
    commandable: bool = False
    inactive_text: str | None = None
    active_text: str | None = None
    states: list[str] | None = None

    @field_validator("instance")
    @classmethod
    def validate_instance(cls, v: int) -> int:
        if v < 0:
            raise ValueError("instance must be non-negative")
        return v


class DeviceConfig(BaseModel):
    device_id: int
    name: str
    ip: str | None = None
    network_profile: NetworkProfileName | None = None
    network_custom: NetworkCustomConfig | None = None
    objects: list[ObjectConfig] = []

    @model_validator(mode="after")
    def validate_unique_object_names(self) -> DeviceConfig:
        names = [obj.name for obj in self.objects]
        if len(names) != len(set(names)):
            dupes = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate object names in device {self.device_id}: {set(dupes)}")
        return self

    @model_validator(mode="after")
    def validate_unique_object_instances(self) -> DeviceConfig:
        seen: set[tuple[ObjectType, int]] = set()
        for obj in self.objects:
            key = (obj.type, obj.instance)
            if key in seen:
                raise ValueError(
                    f"Duplicate object {obj.type.value}:{obj.instance} in device {self.device_id}"
                )
            seen.add(key)
        return self


class GlobalConfig(BaseModel):
    api_port: int = 8099
    bacnet_port: int = 47808
    subnet_mask: int = 24
    network_profile: NetworkProfileName = NetworkProfileName.NONE


class SimulatorConfig(BaseModel):
    global_config: GlobalConfig = GlobalConfig()
    devices: list[DeviceConfig] = []

    @model_validator(mode="after")
    def validate_unique_device_ids(self) -> SimulatorConfig:
        ids = [d.device_id for d in self.devices]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate device IDs: {set(dupes)}")
        return self

    @model_validator(mode="after")
    def validate_unique_explicit_ips(self) -> SimulatorConfig:
        explicit_ips = [d.ip for d in self.devices if d.ip is not None]
        if len(explicit_ips) != len(set(explicit_ips)):
            dupes = [ip for ip in explicit_ips if explicit_ips.count(ip) > 1]
            raise ValueError(f"Duplicate explicit IPs: {set(dupes)}")
        return self


def _apply_env_overrides(config: SimulatorConfig) -> SimulatorConfig:
    """Apply environment variable overrides to the config."""
    if port := os.environ.get("BACNET_PORT"):
        config.global_config.bacnet_port = int(port)
    if api_port := os.environ.get("API_PORT"):
        config.global_config.api_port = int(api_port)
    if subnet := os.environ.get("BACNET_SUBNET_MASK"):
        config.global_config.subnet_mask = int(subnet)
    if profile := os.environ.get("NETWORK_PROFILE"):
        config.global_config.network_profile = NetworkProfileName(profile)

    # Override first device settings
    if config.devices:
        if device_id := os.environ.get("BACNET_DEVICE_ID"):
            config.devices[0].device_id = int(device_id)
        if device_name := os.environ.get("BACNET_DEVICE_NAME"):
            config.devices[0].name = device_name

    return config


def load_config(config_path: str | Path | None = None) -> SimulatorConfig:
    """Load simulator config from YAML file with env var overrides.

    Priority: env vars > YAML config > built-in defaults.
    """
    # Check for CONFIG_FILE env var
    if config_path is None:
        config_path = os.environ.get("CONFIG_FILE")

    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path) as f:
            raw = yaml.safe_load(f)

        if raw is None:
            raw = {}

        global_raw = raw.get("global", {})
        devices_raw = raw.get("devices", [])

        config = SimulatorConfig(
            global_config=GlobalConfig(**global_raw),
            devices=[DeviceConfig(**d) for d in devices_raw],
        )
    else:
        # Use built-in defaults
        from bacnet_sim.defaults import default_config

        config = default_config()

    return _apply_env_overrides(config)
