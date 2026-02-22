"""Tests for device creation, shutdown, and SimulatedDevice methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bacnet_sim.config import (
    DeviceConfig,
    NetworkCustomConfig,
    NetworkProfileName,
    ObjectConfig,
    ObjectType,
)
from bacnet_sim.devices import (
    SimulatedDevice,
    _apply_bacnet_lag,
    _create_object,
    create_device,
    shutdown_device,
)
from bacnet_sim.lag import LagProfile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_device_config(
    device_id: int = 1001,
    name: str = "TestDevice",
    objects: list[ObjectConfig] | None = None,
    network_profile: NetworkProfileName | None = None,
    network_custom: NetworkCustomConfig | None = None,
) -> DeviceConfig:
    """Build a minimal DeviceConfig for testing."""
    if objects is None:
        objects = [
            ObjectConfig(
                type=ObjectType.ANALOG_INPUT,
                instance=1,
                name="Zone Temp",
                unit="degreesFahrenheit",
                value=72.5,
            ),
        ]
    return DeviceConfig(
        device_id=device_id,
        name=name,
        objects=objects,
        network_profile=network_profile,
        network_custom=network_custom,
    )


def _make_device(
    config: DeviceConfig | None = None,
    bacnet: object | None = None,
    initialized: bool = True,
) -> SimulatedDevice:
    """Build a SimulatedDevice suitable for unit tests."""
    config = config or _simple_device_config()
    return SimulatedDevice(
        config=config,
        ip="172.18.0.10",
        port=47808,
        bacnet=bacnet,
        lag_profile=LagProfile(0, 0, 0),
        initialized=initialized,
    )


# ---------------------------------------------------------------------------
# SimulatedDevice dataclass tests
# ---------------------------------------------------------------------------

class TestSimulatedDevice:
    def test_device_id_property(self):
        device = _make_device()
        assert device.device_id == 1001

    def test_name_property(self):
        device = _make_device()
        assert device.name == "TestDevice"

    def test_get_object_returns_bacnet_object(self):
        mock_bacnet = MagicMock()
        mock_obj = MagicMock()
        mock_bacnet.__getitem__ = MagicMock(return_value=mock_obj)
        device = _make_device(bacnet=mock_bacnet)
        result = device.get_object("Zone Temp")
        mock_bacnet.__getitem__.assert_called_once_with("Zone Temp")
        assert result is mock_obj

    def test_get_object_raises_when_not_initialized(self):
        device = _make_device(bacnet=None, initialized=False)
        with pytest.raises(RuntimeError, match="not initialized"):
            device.get_object("Zone Temp")

    def test_list_objects_with_bacnet(self):
        mock_obj = MagicMock()
        mock_obj.presentValue = 72.5
        mock_bacnet = MagicMock()
        mock_bacnet.__getitem__ = MagicMock(return_value=mock_obj)
        device = _make_device(bacnet=mock_bacnet)

        objects = device.list_objects()
        assert len(objects) == 1
        assert objects[0]["name"] == "Zone Temp"
        assert objects[0]["type"] == "analog-input"
        assert objects[0]["presentValue"] == 72.5

    def test_list_objects_without_bacnet(self):
        device = _make_device(bacnet=None, initialized=False)
        objects = device.list_objects()
        assert len(objects) == 1
        assert "presentValue" not in objects[0]

    def test_list_objects_handles_read_error(self):
        mock_bacnet = MagicMock()
        mock_bacnet.__getitem__ = MagicMock(side_effect=Exception("read error"))
        device = _make_device(bacnet=mock_bacnet)

        objects = device.list_objects()
        assert objects[0]["presentValue"] is None


# ---------------------------------------------------------------------------
# _create_object tests
# ---------------------------------------------------------------------------

class TestCreateObject:
    def test_analog_input_basic(self):
        mock_ai = MagicMock(return_value=MagicMock())
        obj_config = ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Zone Temp",
            unit="degreesFahrenheit",
            value=72.5,
        )
        with patch.dict(
            "bacnet_sim.devices.OBJECT_FACTORIES",
            {ObjectType.ANALOG_INPUT: mock_ai},
        ):
            result = _create_object(obj_config)
        assert result is not None
        mock_ai.assert_called_once()
        call_kwargs = mock_ai.call_args[1]
        assert call_kwargs["name"] == "Zone Temp"
        assert call_kwargs["presentValue"] == 72.5
        assert call_kwargs["properties"]["units"] == "degreesFahrenheit"

    def test_binary_output_skips_is_commandable(self):
        """Binary outputs are inherently commandable; is_commandable should not be set."""
        mock_bo = MagicMock(return_value=MagicMock())
        obj_config = ObjectConfig(
            type=ObjectType.BINARY_OUTPUT,
            instance=1,
            name="Fan Command",
            commandable=True,
            inactive_text="Off",
            active_text="On",
        )
        with patch.dict(
            "bacnet_sim.devices.OBJECT_FACTORIES",
            {ObjectType.BINARY_OUTPUT: mock_bo},
        ):
            result = _create_object(obj_config)
        assert result is not None
        call_kwargs = mock_bo.call_args[1]
        assert "is_commandable" not in call_kwargs

    def test_commandable_analog_input(self):
        mock_ai = MagicMock(return_value=MagicMock())
        obj_config = ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Setpoint",
            commandable=True,
        )
        with patch.dict(
            "bacnet_sim.devices.OBJECT_FACTORIES",
            {ObjectType.ANALOG_INPUT: mock_ai},
        ):
            _create_object(obj_config)
        call_kwargs = mock_ai.call_args[1]
        assert call_kwargs["is_commandable"] is True

    @patch("bacnet_sim.devices.make_state_text")
    def test_multistate_value_with_states(self, mock_mst):
        mock_msv = MagicMock(return_value=MagicMock())
        mock_mst.return_value = ["Off", "Low", "High"]
        obj_config = ObjectConfig(
            type=ObjectType.MULTISTATE_VALUE,
            instance=1,
            name="Fan Speed",
            states=["Off", "Low", "High"],
        )
        with patch.dict(
            "bacnet_sim.devices.OBJECT_FACTORIES",
            {ObjectType.MULTISTATE_VALUE: mock_msv},
        ):
            _create_object(obj_config)
        mock_mst.assert_called_once_with(["Off", "Low", "High"])
        call_kwargs = mock_msv.call_args[1]
        assert "stateText" in call_kwargs["properties"]

    def test_character_string_no_properties(self):
        """Character-string with no unit or value should not pass properties kwarg."""
        mock_cs = MagicMock(return_value=MagicMock())
        obj_config = ObjectConfig(
            type=ObjectType.CHARACTER_STRING,
            instance=1,
            name="Status Text",
        )
        with patch.dict(
            "bacnet_sim.devices.OBJECT_FACTORIES",
            {ObjectType.CHARACTER_STRING: mock_cs},
        ):
            _create_object(obj_config)
        call_kwargs = mock_cs.call_args[1]
        assert "properties" not in call_kwargs
        assert "presentValue" not in call_kwargs

    def test_unsupported_type_returns_none(self):
        """An object type not in OBJECT_FACTORIES should return None."""
        obj_config = ObjectConfig(
            type=ObjectType.ANALOG_INPUT,
            instance=1,
            name="Missing",
        )
        with patch.dict(
            "bacnet_sim.devices.OBJECT_FACTORIES",
            {ObjectType.ANALOG_INPUT: None},
            clear=True,
        ):
            result = _create_object(obj_config)
        assert result is None


# ---------------------------------------------------------------------------
# create_device tests
# ---------------------------------------------------------------------------

class TestCreateDevice:
    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_basic_device_creation(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """create_device returns an initialized SimulatedDevice."""
        mock_bacnet = MagicMock()
        mock_obj = MagicMock()
        mock_bacnet.__getitem__ = MagicMock(return_value=mock_obj)
        mock_bac0_module.lite.return_value = mock_bacnet
        mock_create_obj.return_value = MagicMock()

        config = _simple_device_config()
        device = await create_device(config, ip="172.18.0.10", port=47808)

        assert device.initialized is True
        assert device.bacnet is mock_bacnet
        assert device.ip == "172.18.0.10"
        assert device.port == 47808
        assert device.device_id == 1001

        # BAC0.lite() was called with the right parameters
        mock_bac0_module.lite.assert_called_once_with(
            ip="172.18.0.10/24",
            port=47808,
            deviceId=1001,
            localObjName="TestDevice",
        )

        # ObjectFactory.clear_objects() was called before creating objects
        mock_factory_cls.clear_objects.assert_called_once()

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_device_with_custom_subnet(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        mock_bac0_module.lite.return_value = MagicMock()
        mock_create_obj.return_value = MagicMock()
        config = _simple_device_config()

        await create_device(config, ip="10.0.0.5", port=47808, subnet_mask=16)

        mock_bac0_module.lite.assert_called_once_with(
            ip="10.0.0.5/16",
            port=47808,
            deviceId=1001,
            localObjName="TestDevice",
        )

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_device_with_network_profile(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """Device-level network_profile takes precedence over global."""
        mock_bac0_module.lite.return_value = MagicMock()
        mock_create_obj.return_value = MagicMock()
        config = _simple_device_config(
            network_profile=NetworkProfileName.REMOTE_SITE,
        )

        device = await create_device(
            config,
            ip="172.18.0.10",
            port=47808,
            global_network_profile=NetworkProfileName.LOCAL_NETWORK,
        )

        assert device.lag_profile.min_delay_ms == 50
        assert device.lag_profile.max_delay_ms == 200
        assert device.lag_profile.drop_probability == 0.01

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_device_falls_back_to_global_profile(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """When device has no network_profile, the global one is used."""
        mock_bac0_module.lite.return_value = MagicMock()
        mock_create_obj.return_value = MagicMock()
        config = _simple_device_config()  # network_profile=None

        device = await create_device(
            config,
            ip="172.18.0.10",
            port=47808,
            global_network_profile=NetworkProfileName.REMOTE_SITE,
        )

        assert device.lag_profile.min_delay_ms == 50

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_objects_registered_with_bacnet(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """Factory instances are used to register objects with the BAC0 app."""
        mock_bacnet = MagicMock()
        mock_bac0_module.lite.return_value = mock_bacnet

        factory_instance = MagicMock()
        mock_create_obj.return_value = factory_instance

        config = _simple_device_config(
            objects=[
                ObjectConfig(
                    type=ObjectType.ANALOG_INPUT,
                    instance=1,
                    name="Temp",
                    value=72.0,
                ),
                ObjectConfig(
                    type=ObjectType.BINARY_INPUT,
                    instance=1,
                    name="Status",
                ),
            ]
        )

        await create_device(config, ip="172.18.0.10", port=47808)

        assert mock_create_obj.call_count == 2
        factory_instance.add_objects_to_application.assert_called_once_with(mock_bacnet)

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_no_objects_skips_registration(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """If _create_object returns None for all objects, skip registration."""
        mock_bac0_module.lite.return_value = MagicMock()
        mock_create_obj.return_value = None

        config = _simple_device_config()
        device = await create_device(config, ip="172.18.0.10", port=47808)

        assert device.initialized is True

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_initial_value_set_error_logged(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """Errors setting initial values are logged but don't prevent initialization."""
        mock_bacnet = MagicMock()
        mock_bacnet.__getitem__ = MagicMock(side_effect=Exception("write error"))
        mock_bac0_module.lite.return_value = mock_bacnet
        mock_create_obj.return_value = MagicMock()

        config = _simple_device_config()
        device = await create_device(config, ip="172.18.0.10", port=47808)

        # Device should still be initialized despite the value-setting error
        assert device.initialized is True

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_no_objects_config(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """Device with empty objects list should initialize successfully."""
        mock_bac0_module.lite.return_value = MagicMock()
        config = _simple_device_config(objects=[])

        device = await create_device(config, ip="172.18.0.10", port=47808)
        assert device.initialized is True


# ---------------------------------------------------------------------------
# shutdown_device tests
# ---------------------------------------------------------------------------

class TestShutdownDevice:
    @pytest.mark.asyncio
    async def test_successful_disconnect(self):
        mock_bacnet = MagicMock()
        device = _make_device(bacnet=mock_bacnet)
        assert device.initialized is True

        await shutdown_device(device)

        mock_bacnet.disconnect.assert_called_once()
        assert device.initialized is False

    @pytest.mark.asyncio
    async def test_disconnect_error_is_caught(self):
        """Errors during disconnect should be logged, not raised."""
        mock_bacnet = MagicMock()
        mock_bacnet.disconnect.side_effect = Exception("socket error")
        device = _make_device(bacnet=mock_bacnet)

        await shutdown_device(device)

        assert device.initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_when_bacnet_is_none(self):
        """Shutting down a device with no BAC0 instance should succeed."""
        device = _make_device(bacnet=None, initialized=False)

        await shutdown_device(device)

        assert device.initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_sets_initialized_false(self):
        mock_bacnet = MagicMock()
        device = _make_device(bacnet=mock_bacnet, initialized=True)

        await shutdown_device(device)

        assert device.initialized is False


# ---------------------------------------------------------------------------
# _apply_bacnet_lag tests
# ---------------------------------------------------------------------------

def _mock_bacnet_with_app():
    """Create a mock BAC0 instance with an Application that has do_*Request methods."""
    mock_app = MagicMock()
    mock_app.do_ReadPropertyRequest = AsyncMock()
    mock_app.do_WritePropertyRequest = AsyncMock()
    mock_app.do_ReadPropertyMultipleRequest = AsyncMock()
    mock_bacnet = MagicMock()
    mock_bacnet.this_application.app = mock_app
    return mock_bacnet, mock_app


class TestApplyBacnetLag:
    def test_wraps_all_three_methods(self):
        """All three do_*Request methods should be replaced."""
        bacnet, app = _mock_bacnet_with_app()
        orig_read = app.do_ReadPropertyRequest
        orig_write = app.do_WritePropertyRequest
        orig_multi = app.do_ReadPropertyMultipleRequest

        lag = LagProfile(0, 10, 0)
        _apply_bacnet_lag(bacnet, lag)

        assert app.do_ReadPropertyRequest is not orig_read
        assert app.do_WritePropertyRequest is not orig_write
        assert app.do_ReadPropertyMultipleRequest is not orig_multi

    def test_preserves_original_reference(self):
        """Wrapped methods should store the original via _bacnet_lag_original."""
        bacnet, app = _mock_bacnet_with_app()
        orig_read = app.do_ReadPropertyRequest

        lag = LagProfile(0, 10, 0)
        _apply_bacnet_lag(bacnet, lag)

        assert app.do_ReadPropertyRequest._bacnet_lag_original is orig_read

    @pytest.mark.asyncio
    async def test_calls_original_when_no_drop(self):
        """With no drop probability, the original handler is called."""
        bacnet, app = _mock_bacnet_with_app()
        orig_read = app.do_ReadPropertyRequest
        lag = LagProfile(0, 0, 0)  # no delay, no drop
        _apply_bacnet_lag(bacnet, lag)

        apdu = MagicMock()
        await app.do_ReadPropertyRequest(apdu)

        orig_read.assert_awaited_once_with(apdu)

    @pytest.mark.asyncio
    async def test_drops_request_when_drop_probability_is_one(self):
        """With 100% drop, the original handler should NOT be called."""
        bacnet, app = _mock_bacnet_with_app()
        orig_read = app.do_ReadPropertyRequest
        lag = LagProfile(0, 0, 1.0)  # 100% drop
        _apply_bacnet_lag(bacnet, lag)

        apdu = MagicMock()
        await app.do_ReadPropertyRequest(apdu)

        orig_read.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("bacnet_sim.lag.asyncio.sleep", new_callable=AsyncMock)
    async def test_delay_applied_before_handler(self, mock_sleep):
        """With delay configured, asyncio.sleep should be called."""
        bacnet, app = _mock_bacnet_with_app()
        lag = LagProfile(5, 10, 0)
        _apply_bacnet_lag(bacnet, lag)

        apdu = MagicMock()
        await app.do_ReadPropertyRequest(apdu)

        mock_sleep.assert_awaited_once()

    def test_skips_missing_methods(self):
        """If a do_*Request method doesn't exist, it should be skipped."""
        mock_app = MagicMock(spec=[])  # no methods at all
        mock_bacnet = MagicMock()
        mock_bacnet.this_application.app = mock_app

        lag = LagProfile(0, 10, 0)
        # Should not raise
        _apply_bacnet_lag(mock_bacnet, lag)

    def test_rewrap_unwraps_first(self):
        """Re-applying lag should unwrap the previous wrapper, not stack."""
        bacnet, app = _mock_bacnet_with_app()
        orig_read = app.do_ReadPropertyRequest

        lag1 = LagProfile(0, 10, 0)
        _apply_bacnet_lag(bacnet, lag1)

        lag2 = LagProfile(50, 200, 0.01)
        _apply_bacnet_lag(bacnet, lag2)

        # The original should still be the true original, not the first wrapper
        assert app.do_ReadPropertyRequest._bacnet_lag_original is orig_read

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_create_device_applies_lag_for_nonzero_profile(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """create_device should apply BACnet lag when lag profile has delay or drop."""
        bacnet, app = _mock_bacnet_with_app()
        mock_bac0_module.lite.return_value = bacnet
        mock_create_obj.return_value = MagicMock()

        config = _simple_device_config(
            network_profile=NetworkProfileName.REMOTE_SITE,
        )
        device = await create_device(config, ip="172.18.0.10", port=47808)

        # The do_ReadPropertyRequest should have been wrapped
        assert hasattr(app.do_ReadPropertyRequest, "_bacnet_lag_original")
        assert device.lag_profile.max_delay_ms == 200

    @pytest.mark.asyncio
    @patch("bacnet_sim.devices._create_object")
    @patch("bacnet_sim.devices.ObjectFactory")
    @patch("bacnet_sim.devices.BAC0")
    async def test_create_device_skips_lag_for_none_profile(
        self, mock_bac0_module, mock_factory_cls, mock_create_obj
    ):
        """create_device should NOT apply BACnet lag when profile is NONE."""
        bacnet, app = _mock_bacnet_with_app()
        orig_read = app.do_ReadPropertyRequest
        mock_bac0_module.lite.return_value = bacnet
        mock_create_obj.return_value = MagicMock()

        config = _simple_device_config()  # default: no network profile
        await create_device(config, ip="172.18.0.10", port=47808)

        # The handler should NOT have been wrapped
        assert app.do_ReadPropertyRequest is orig_read
