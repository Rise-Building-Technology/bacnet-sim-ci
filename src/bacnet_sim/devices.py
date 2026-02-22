"""BAC0 device creation and management.

Creates BAC0.lite() instances from DeviceConfig, registers BACnet objects
using the BAC0 factory pattern, and manages device lifecycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import BAC0
from BAC0.core.devices.local.factory import (
    ObjectFactory,
    analog_input,
    analog_output,
    binary_input,
    binary_output,
    character_string,
    make_state_text,
    multistate_value,
)

from bacnet_sim.config import DeviceConfig, NetworkProfileName, ObjectConfig, ObjectType
from bacnet_sim.lag import LagProfile, get_lag_profile

logger = logging.getLogger(__name__)

# Map ObjectType enum to BAC0 factory functions
OBJECT_FACTORIES = {
    ObjectType.ANALOG_INPUT: analog_input,
    ObjectType.ANALOG_OUTPUT: analog_output,
    ObjectType.BINARY_INPUT: binary_input,
    ObjectType.BINARY_OUTPUT: binary_output,
    ObjectType.MULTISTATE_VALUE: multistate_value,
    ObjectType.CHARACTER_STRING: character_string,
}


@dataclass
class SimulatedDevice:
    """A running BAC0 device with its configuration and lag profile."""

    config: DeviceConfig
    ip: str
    port: int
    bacnet: Any | None = None  # BAC0 device instance (None before initialization)
    lag_profile: LagProfile = field(default_factory=lambda: LagProfile(0, 0, 0))
    initialized: bool = False

    @property
    def device_id(self) -> int:
        return self.config.device_id

    @property
    def name(self) -> str:
        return self.config.name

    def get_object(self, name: str) -> Any:
        """Get a BACnet object by name from the BAC0 device."""
        if self.bacnet is None:
            raise RuntimeError(f"Device {self.device_id} not initialized")
        return self.bacnet[name]

    def list_objects(self) -> list[dict[str, Any]]:
        """List all configured objects with their current values."""
        objects = []
        for obj_config in self.config.objects:
            obj_info: dict[str, Any] = {
                "type": obj_config.type.value,
                "instance": obj_config.instance,
                "name": obj_config.name,
                "commandable": obj_config.commandable,
            }
            if self.bacnet is not None:
                try:
                    bacnet_obj = self.bacnet[obj_config.name]
                    obj_info["presentValue"] = bacnet_obj.presentValue
                except Exception:
                    logger.debug("Could not read presentValue for %s", obj_config.name)
                    obj_info["presentValue"] = None
            objects.append(obj_info)
        return objects


def _create_object(obj_config: ObjectConfig) -> Any | None:
    """Call the appropriate BAC0 factory function to create an object.

    Returns the ObjectFactory instance (all instances share a class-level
    objects dict) so the caller can call add_objects_to_application().
    Returns None if the object type is unsupported.
    """
    factory_fn = OBJECT_FACTORIES.get(obj_config.type)
    if factory_fn is None:
        logger.warning("Unsupported object type: %s (skipping)", obj_config.type.value)
        return None

    kwargs: dict[str, Any] = {
        "name": obj_config.name,
        "description": obj_config.name,
    }

    # Output types (analog-output, binary-output) are inherently commandable
    # in BACpypes3. Passing is_commandable=True to BAC0 causes MRO conflicts
    # on newer versions. Only set it for input/value types.
    inherently_commandable = {ObjectType.ANALOG_OUTPUT, ObjectType.BINARY_OUTPUT}
    if obj_config.commandable and obj_config.type not in inherently_commandable:
        kwargs["is_commandable"] = True

    properties: dict[str, Any] = {}
    if obj_config.unit:
        properties["units"] = obj_config.unit
    if obj_config.inactive_text:
        properties["inactiveText"] = obj_config.inactive_text
    if obj_config.active_text:
        properties["activeText"] = obj_config.active_text

    if obj_config.type == ObjectType.MULTISTATE_VALUE and obj_config.states:
        properties["stateText"] = make_state_text(obj_config.states)

    if properties:
        kwargs["properties"] = properties

    if obj_config.value is not None:
        kwargs["presentValue"] = obj_config.value

    return factory_fn(**kwargs)


async def create_device(
    config: DeviceConfig,
    ip: str,
    port: int,
    subnet_mask: int = 24,
    global_network_profile: NetworkProfileName = NetworkProfileName.NONE,
) -> SimulatedDevice:
    """Create and initialize a BAC0 device from config.

    Args:
        config: Device configuration.
        ip: IP address to bind the device to.
        port: BACnet UDP port.
        subnet_mask: Subnet prefix length for the BACnet network.
        global_network_profile: Fallback network profile from global config.

    Returns:
        An initialized SimulatedDevice.
    """
    logger.info(
        "Creating device %d (%s) on %s:%d",
        config.device_id, config.name, ip, port,
    )

    # Determine lag profile
    profile_name = config.network_profile or global_network_profile
    lag_profile = get_lag_profile(profile_name, config.network_custom)

    device = SimulatedDevice(
        config=config,
        ip=ip,
        port=port,
        lag_profile=lag_profile,
    )

    # Create BAC0 device (synchronous - _initialized is set before returning)
    subnet_ip = f"{ip}/{subnet_mask}"
    bacnet = BAC0.lite(
        ip=subnet_ip,
        port=port,
        deviceId=config.device_id,
        localObjName=config.name,
    )

    # Clear the shared ObjectFactory state before creating objects for this
    # device.  BAC0 factory functions accumulate objects in class-level dicts
    # (ObjectFactory.objects / ObjectFactory.instances).  Without clearing,
    # objects from a previously created device would leak into this device's
    # add_objects_to_application() call.
    ObjectFactory.clear_objects()

    # Create all objects using factory pattern.
    # Factory functions return ObjectFactory instances that share a class-level
    # objects dict. Any instance can register all accumulated objects.
    factory_instance = None
    for obj_config in config.objects:
        result = _create_object(obj_config)
        if result is not None:
            factory_instance = result

    # Register all accumulated objects with the BAC0 application.
    if factory_instance is not None:
        factory_instance.add_objects_to_application(bacnet)

    # Set initial values for objects that need it
    for obj_config in config.objects:
        if obj_config.value is not None:
            try:
                bacnet[obj_config.name].presentValue = obj_config.value
            except Exception as e:
                logger.warning(
                    "Could not set initial value for %s: %s", obj_config.name, e
                )

    device.bacnet = bacnet
    device.initialized = True
    logger.info("Device %d (%s) initialized successfully", config.device_id, config.name)
    return device


async def shutdown_device(device: SimulatedDevice) -> None:
    """Gracefully shut down a BAC0 device."""
    if device.bacnet is not None:
        try:
            device.bacnet.disconnect()
            logger.info("Device %d disconnected", device.device_id)
        except Exception as e:
            logger.warning("Error disconnecting device %d: %s", device.device_id, e)
    device.initialized = False
