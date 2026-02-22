"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_device_yaml(tmp_path):
    """Create a sample device config YAML file."""
    config = tmp_path / "config.yaml"
    config.write_text(
        """\
global:
  api_port: 8099
  bacnet_port: 47808
  subnet_mask: 24
  network_profile: local-network

devices:
  - device_id: 1001
    name: "Test AHU"
    objects:
      - type: analog-input
        instance: 1
        name: "Zone Temp"
        unit: degreesFahrenheit
        value: 72.5
      - type: binary-output
        instance: 1
        name: "Fan Command"
        inactive_text: "Off"
        active_text: "On"
        value: false
        commandable: true
"""
    )
    return config


@pytest.fixture
def multi_device_yaml(tmp_path):
    """Create a multi-device config YAML file."""
    config = tmp_path / "multi.yaml"
    config.write_text(
        """\
global:
  api_port: 8099
  bacnet_port: 47808

devices:
  - device_id: 1001
    name: "AHU-1"
    objects:
      - type: analog-input
        instance: 1
        name: "Zone Temp"
        unit: degreesFahrenheit
        value: 72.5
  - device_id: 1002
    name: "AHU-2"
    objects:
      - type: analog-input
        instance: 1
        name: "Zone Temp"
        unit: degreesFahrenheit
        value: 68.0
  - device_id: 1003
    name: "VAV-1"
    objects:
      - type: binary-input
        instance: 1
        name: "Damper Status"
        value: true
"""
    )
    return config
