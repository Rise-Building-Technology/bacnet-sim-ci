"""Configuration models and loading for the BACnet simulator."""

from __future__ import annotations

import ipaddress
import logging
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)


class ObjectType(StrEnum):
    ANALOG_INPUT = "analog-input"
    ANALOG_OUTPUT = "analog-output"
    BINARY_INPUT = "binary-input"
    BINARY_OUTPUT = "binary-output"
    MULTISTATE_VALUE = "multistate-value"
    CHARACTER_STRING = "character-string"
    SCHEDULE = "schedule"
    TREND_LOG = "trend-log"


class NetworkProfileName(StrEnum):
    LOCAL_NETWORK = "local-network"
    REMOTE_SITE = "remote-site"
    UNRELIABLE_LINK = "unreliable-link"
    CUSTOM = "custom"
    NONE = "none"


class NetworkCustomConfig(BaseModel):
    min_delay_ms: float = 0
    max_delay_ms: float = 0
    drop_probability: float = 0.0

    @field_validator("min_delay_ms", "max_delay_ms")
    @classmethod
    def validate_non_negative_delay(cls, v: float) -> float:
        if v < 0:
            raise ValueError("delay values must be non-negative")
        return v

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

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: int) -> int:
        if not 0 <= v <= 4194303:
            raise ValueError("device_id must be 0-4194303 (BACnet 22-bit range)")
        return v

    @field_validator("ip")
    @classmethod
    def validate_ip_format(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                ipaddress.IPv4Address(v)
            except ValueError:
                raise ValueError(f"Invalid IPv4 address: {v}")
        return v

    @model_validator(mode="after")
    def validate_unique_object_names(self) -> DeviceConfig:
        names = [obj.name for obj in self.objects]
        seen: set[str] = set()
        dupes: set[str] = set()
        for n in names:
            if n in seen:
                dupes.add(n)
            seen.add(n)
        if dupes:
            raise ValueError(f"Duplicate object names in device {self.device_id}: {dupes}")
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

    def find_object(self, object_type: str, instance: int) -> ObjectConfig | None:
        """Find an object config by type and instance."""
        for obj in self.objects:
            if obj.type.value == object_type and obj.instance == instance:
                return obj
        return None


class GlobalConfig(BaseModel):
    api_port: int = 8099
    bacnet_port: int = 47808
    subnet_mask: int = 24
    network_profile: NetworkProfileName = NetworkProfileName.NONE

    @field_validator("subnet_mask")
    @classmethod
    def validate_subnet_mask(cls, v: int) -> int:
        if not 1 <= v <= 30:
            raise ValueError("subnet_mask must be 1-30")
        return v

    @field_validator("api_port", "bacnet_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("port must be 1-65535")
        return v


class SimulatorConfig(BaseModel):
    global_config: GlobalConfig = GlobalConfig()
    devices: list[DeviceConfig] = []

    @model_validator(mode="after")
    def validate_unique_device_ids(self) -> SimulatorConfig:
        seen: set[int] = set()
        dupes: set[int] = set()
        for d in self.devices:
            if d.device_id in seen:
                dupes.add(d.device_id)
            seen.add(d.device_id)
        if dupes:
            raise ValueError(f"Duplicate device IDs: {dupes}")
        return self

    @model_validator(mode="after")
    def validate_unique_explicit_ips(self) -> SimulatorConfig:
        seen: set[str] = set()
        dupes: set[str] = set()
        for d in self.devices:
            if d.ip is not None:
                if d.ip in seen:
                    dupes.add(d.ip)
                seen.add(d.ip)
        if dupes:
            raise ValueError(f"Duplicate explicit IPs: {dupes}")
        return self


def _parse_env_int(env_var: str, min_val: int, max_val: int) -> int | None:
    """Parse an integer environment variable with range validation."""
    raw = os.environ.get(env_var)
    if raw is None:
        return None
    try:
        val = int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {env_var} must be an integer, got: {raw!r}")
    if not min_val <= val <= max_val:
        raise ValueError(f"Environment variable {env_var} must be {min_val}-{max_val}, got: {val}")
    return val


def _apply_env_overrides(config: SimulatorConfig) -> None:
    """Apply environment variable overrides to the config (mutates in place)."""
    if (port := _parse_env_int("BACNET_PORT", 1, 65535)) is not None:
        config.global_config.bacnet_port = port
    if (api_port := _parse_env_int("API_PORT", 1, 65535)) is not None:
        config.global_config.api_port = api_port
    if (subnet := _parse_env_int("BACNET_SUBNET_MASK", 1, 30)) is not None:
        config.global_config.subnet_mask = subnet
    if profile := os.environ.get("NETWORK_PROFILE"):
        config.global_config.network_profile = NetworkProfileName(profile)

    # Override first device settings
    if config.devices:
        if (device_id := _parse_env_int("BACNET_DEVICE_ID", 0, 4194303)) is not None:
            config.devices[0].device_id = device_id
        if device_name := os.environ.get("BACNET_DEVICE_NAME"):
            config.devices[0].name = device_name


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
        from bacnet_sim.defaults import default_config  # avoid circular import

        config = default_config()

    _apply_env_overrides(config)
    return config
