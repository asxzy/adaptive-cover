"""Tests for proxy sensor classes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from custom_components.adaptive_cover.binary_sensor import (
    CoverRoomDirectSunProxySensor,
    CoverRoomOccupiedProxySensor,
    ProxyBinarySensorEntity,
    RoomCoverSunInfrontProxySensor,
)
from custom_components.adaptive_cover.const import (
    CONF_CLOUD_ENTITY,
    CONF_ENTRY_TYPE,
    CONF_PRESENCE_ENTITY,
    CONF_ROOM_ID,
    CONF_TEMP_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
    SIGNAL_COVER_REGISTERED,
    EntryType,
)
from custom_components.adaptive_cover.coordinator import AdaptiveCoverData
from custom_components.adaptive_cover.room_coordinator import RoomData
from custom_components.adaptive_cover.sensor import (
    CoverRoomCloudProxySensor,
    CoverRoomComfortProxySensor,
    ProxySensorEntity,
    RoomCoverPositionProxySensor,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# =============================================================================
# Proxy Sensor Base Class Tests
# =============================================================================


class TestProxySensorEntity:
    """Tests for ProxySensorEntity base class."""

    @pytest.fixture
    def mock_source_coordinator(self) -> MagicMock:
        """Create a mock source coordinator."""
        coordinator = MagicMock()
        coordinator.data = MagicMock()
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_device_info(self) -> dict:
        """Create mock device info."""
        from homeassistant.helpers.device_registry import DeviceInfo

        return DeviceInfo(
            identifiers={(DOMAIN, "test_device")},
            name="Test Device",
        )

    def test_init(
        self, mock_source_coordinator: MagicMock, mock_device_info: dict
    ) -> None:
        """Test ProxySensorEntity initialization."""
        sensor = ProxySensorEntity(
            source_coordinator=mock_source_coordinator,
            device_info=mock_device_info,
            unique_id="test_unique_id",
            name="Test Sensor",
        )

        assert sensor._source_coordinator == mock_source_coordinator
        assert sensor._attr_device_info == mock_device_info
        assert sensor._attr_unique_id == "test_unique_id"
        assert sensor._attr_name == "Test Sensor"
        assert sensor._unsub is None

    @pytest.mark.asyncio
    async def test_async_added_to_hass_subscribes(
        self, mock_source_coordinator: MagicMock, mock_device_info: dict
    ) -> None:
        """Test that async_added_to_hass subscribes to coordinator."""
        mock_unsub = MagicMock()
        mock_source_coordinator.async_add_listener.return_value = mock_unsub

        sensor = ProxySensorEntity(
            source_coordinator=mock_source_coordinator,
            device_info=mock_device_info,
            unique_id="test_id",
            name="Test",
        )

        await sensor.async_added_to_hass()

        mock_source_coordinator.async_add_listener.assert_called_once()
        assert sensor._unsub == mock_unsub

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass_unsubscribes(
        self, mock_source_coordinator: MagicMock, mock_device_info: dict
    ) -> None:
        """Test that async_will_remove_from_hass unsubscribes."""
        mock_unsub = MagicMock()
        mock_source_coordinator.async_add_listener.return_value = mock_unsub

        sensor = ProxySensorEntity(
            source_coordinator=mock_source_coordinator,
            device_info=mock_device_info,
            unique_id="test_id",
            name="Test",
        )

        await sensor.async_added_to_hass()
        await sensor.async_will_remove_from_hass()

        mock_unsub.assert_called_once()
        assert sensor._unsub is None

    @pytest.mark.asyncio
    async def test_async_will_remove_handles_no_subscription(
        self, mock_source_coordinator: MagicMock, mock_device_info: dict
    ) -> None:
        """Test that async_will_remove_from_hass handles no subscription gracefully."""
        sensor = ProxySensorEntity(
            source_coordinator=mock_source_coordinator,
            device_info=mock_device_info,
            unique_id="test_id",
            name="Test",
        )

        # Should not raise error
        await sensor.async_will_remove_from_hass()


class TestProxyBinarySensorEntity:
    """Tests for ProxyBinarySensorEntity base class."""

    @pytest.fixture
    def mock_source_coordinator(self) -> MagicMock:
        """Create a mock source coordinator."""
        coordinator = MagicMock()
        coordinator.data = MagicMock()
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_device_info(self) -> dict:
        """Create mock device info."""
        from homeassistant.helpers.device_registry import DeviceInfo

        return DeviceInfo(
            identifiers={(DOMAIN, "test_device")},
            name="Test Device",
        )

    def test_init(
        self, mock_source_coordinator: MagicMock, mock_device_info: dict
    ) -> None:
        """Test ProxyBinarySensorEntity initialization."""
        sensor = ProxyBinarySensorEntity(
            source_coordinator=mock_source_coordinator,
            device_info=mock_device_info,
            unique_id="test_unique_id",
            name="Test Binary Sensor",
        )

        assert sensor._source_coordinator == mock_source_coordinator
        assert sensor._attr_device_info == mock_device_info
        assert sensor._attr_unique_id == "test_unique_id"
        assert sensor._attr_name == "Test Binary Sensor"

    @pytest.mark.asyncio
    async def test_async_added_to_hass_subscribes(
        self, mock_source_coordinator: MagicMock, mock_device_info: dict
    ) -> None:
        """Test that async_added_to_hass subscribes to coordinator."""
        mock_unsub = MagicMock()
        mock_source_coordinator.async_add_listener.return_value = mock_unsub

        sensor = ProxyBinarySensorEntity(
            source_coordinator=mock_source_coordinator,
            device_info=mock_device_info,
            unique_id="test_id",
            name="Test",
        )

        await sensor.async_added_to_hass()

        mock_source_coordinator.async_add_listener.assert_called_once()
        assert sensor._unsub == mock_unsub


# =============================================================================
# Cover-to-Room Proxy Sensor Tests
# =============================================================================


class TestCoverRoomCloudProxySensor:
    """Tests for CoverRoomCloudProxySensor."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            cloud_coverage=45.0,
            comfort_status="comfortable",
            sensor_available={},
            last_known={},
        )
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    def test_init(self, mock_room_coordinator: MagicMock) -> None:
        """Test CoverRoomCloudProxySensor initialization."""
        sensor = CoverRoomCloudProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Living Room Blinds",
            room_id="room_456",
        )

        assert sensor._attr_unique_id == "cover_123_room_proxy_cloud"
        assert sensor._attr_name == "Cloud Coverage (Room)"
        assert "cover_123" in str(sensor._attr_device_info["identifiers"])
        assert sensor._attr_device_info["via_device"] == (DOMAIN, "room_room_456")

    def test_native_value(self, mock_room_coordinator: MagicMock) -> None:
        """Test native_value returns cloud coverage from room."""
        sensor = CoverRoomCloudProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.native_value == 45.0

    def test_native_value_no_data(self, mock_room_coordinator: MagicMock) -> None:
        """Test native_value returns None when no data."""
        mock_room_coordinator.data = None

        sensor = CoverRoomCloudProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.native_value is None

    def test_available(self, mock_room_coordinator: MagicMock) -> None:
        """Test available returns True when cloud data exists."""
        sensor = CoverRoomCloudProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.available is True

    def test_available_no_cloud_data(self, mock_room_coordinator: MagicMock) -> None:
        """Test available returns False when no cloud data."""
        mock_room_coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            cloud_coverage=None,  # No cloud data
            comfort_status="comfortable",
            sensor_available={},
            last_known={},
        )

        sensor = CoverRoomCloudProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.available is False


class TestCoverRoomComfortProxySensor:
    """Tests for CoverRoomComfortProxySensor."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.comfort_status = "too_hot"
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            cloud_coverage=45.0,
            comfort_status="too_hot",
            sensor_available={},
            last_known={},
        )
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    def test_init(self, mock_room_coordinator: MagicMock) -> None:
        """Test CoverRoomComfortProxySensor initialization."""
        sensor = CoverRoomComfortProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Living Room Blinds",
            room_id="room_456",
        )

        assert sensor._attr_unique_id == "cover_123_room_proxy_comfort"
        assert sensor._attr_name == "Comfort Status (Room)"

    def test_native_value(self, mock_room_coordinator: MagicMock) -> None:
        """Test native_value returns comfort status from room."""
        sensor = CoverRoomComfortProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.native_value == "too_hot"

    def test_available(self, mock_room_coordinator: MagicMock) -> None:
        """Test available returns True when data exists."""
        sensor = CoverRoomComfortProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.available is True

    def test_available_no_data(self, mock_room_coordinator: MagicMock) -> None:
        """Test available returns False when no data."""
        mock_room_coordinator.data = None

        sensor = CoverRoomComfortProxySensor(
            room_coordinator=mock_room_coordinator,
            cover_entry_id="cover_123",
            cover_name="Blinds",
            room_id="room_456",
        )

        assert sensor.available is False


class TestCoverRoomOccupiedProxySensor:
    """Tests for CoverRoomOccupiedProxySensor (binary sensor)."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True},
            last_known={"is_presence": True},
        )
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock cover coordinator."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "cover_123"
        return coordinator

    def test_init(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test CoverRoomOccupiedProxySensor initialization."""
        sensor = CoverRoomOccupiedProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Living Room Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor._attr_unique_id == "cover_123_room_proxy_occupied"
        assert sensor._attr_name == "Living Room Blinds Room Occupied (Room)"

    def test_is_on(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test is_on returns room's occupied status."""
        sensor = CoverRoomOccupiedProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor.is_on is True

    def test_is_on_no_data(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test is_on returns None when no data."""
        mock_room_coordinator.data = None

        sensor = CoverRoomOccupiedProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor.is_on is None

    def test_available(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test available with sensor data."""
        sensor = CoverRoomOccupiedProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor.available is True


class TestCoverRoomDirectSunProxySensor:
    """Tests for CoverRoomDirectSunProxySensor (binary sensor)."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"has_direct_sun": True},
            last_known={"has_direct_sun": True},
        )
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock cover coordinator."""
        coordinator = MagicMock()
        return coordinator

    def test_init(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test CoverRoomDirectSunProxySensor initialization."""
        sensor = CoverRoomDirectSunProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Living Room Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor._attr_unique_id == "cover_123_room_proxy_direct_sun"
        assert sensor._attr_name == "Living Room Blinds Has Direct Sun (Room)"

    def test_is_on(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test is_on returns room's direct sun status."""
        sensor = CoverRoomDirectSunProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor.is_on is True

    def test_is_on_no_data(
        self, mock_room_coordinator: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test is_on returns None when no data."""
        mock_room_coordinator.data = None

        sensor = CoverRoomDirectSunProxySensor(
            source_coordinator=mock_room_coordinator,
            cover_coordinator=mock_cover_coordinator,
            cover_name="Blinds",
            cover_id="cover_123",
            room_id="room_456",
        )

        assert sensor.is_on is None


# =============================================================================
# Room-to-Cover Proxy Sensor Tests
# =============================================================================


class TestRoomCoverPositionProxySensor:
    """Tests for RoomCoverPositionProxySensor."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock cover coordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"state": 75},
            attributes={},
        )
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"name": "Kitchen Blinds"}
        coordinator.config_entry.entry_id = "cover_789"
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_room_coordinator(self, mock_cover_coordinator: MagicMock) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"name": "Kitchen"}
        coordinator.config_entry.entry_id = "room_123"
        coordinator._child_coordinators = [mock_cover_coordinator]
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    def test_init(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test RoomCoverPositionProxySensor initialization."""
        sensor = RoomCoverPositionProxySensor(
            cover_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
        )

        assert sensor._attr_unique_id == "room_room_123_proxy_cover_789_position"
        assert sensor._attr_name == "Kitchen Blinds Position"
        assert "room_room_123" in str(sensor._attr_device_info["identifiers"])

    def test_native_value(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test native_value returns cover position."""
        sensor = RoomCoverPositionProxySensor(
            cover_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
        )

        assert sensor.native_value == 75

    def test_native_value_no_data(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test native_value returns None when no data."""
        mock_cover_coordinator.data = None

        sensor = RoomCoverPositionProxySensor(
            cover_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
        )

        assert sensor.native_value is None

    def test_available(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns True when cover is registered and has data."""
        sensor = RoomCoverPositionProxySensor(
            cover_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
        )

        assert sensor.available is True

    def test_available_cover_not_registered(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns False when cover not registered with room."""
        mock_room_coordinator._child_coordinators = []  # No covers registered

        sensor = RoomCoverPositionProxySensor(
            cover_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
        )

        assert sensor.available is False

    def test_available_no_position(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns False when no position data."""
        mock_cover_coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"state": None},
            attributes={},
        )

        sensor = RoomCoverPositionProxySensor(
            cover_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
        )

        assert sensor.available is False


class TestRoomCoverSunInfrontProxySensor:
    """Tests for RoomCoverSunInfrontProxySensor (binary sensor)."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock cover coordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"sun_motion": True},
            attributes={},
        )
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"name": "Kitchen Blinds"}
        coordinator.config_entry.entry_id = "cover_789"
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"name": "Kitchen"}
        coordinator.config_entry.entry_id = "room_123"
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    def test_init(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test RoomCoverSunInfrontProxySensor initialization."""
        sensor = RoomCoverSunInfrontProxySensor(
            source_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
            cover_name="Kitchen Blinds",
            cover_id="cover_789",
            room_id="room_123",
        )

        assert sensor._attr_unique_id == "room_room_123_proxy_cover_789_sun_infront"
        assert sensor._attr_name == "Kitchen Blinds Sun Infront"

    def test_is_on(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test is_on returns cover's sun infront status."""
        sensor = RoomCoverSunInfrontProxySensor(
            source_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
            cover_name="Kitchen Blinds",
            cover_id="cover_789",
            room_id="room_123",
        )

        assert sensor.is_on is True

    def test_is_on_no_data(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test is_on returns None when no data."""
        mock_cover_coordinator.data = None

        sensor = RoomCoverSunInfrontProxySensor(
            source_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
            cover_name="Kitchen Blinds",
            cover_id="cover_789",
            room_id="room_123",
        )

        assert sensor.is_on is None

    def test_available(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns True when sun_motion data exists."""
        sensor = RoomCoverSunInfrontProxySensor(
            source_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
            cover_name="Kitchen Blinds",
            cover_id="cover_789",
            room_id="room_123",
        )

        assert sensor.available is True

    def test_available_no_sun_motion(
        self, mock_cover_coordinator: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns False when no sun_motion data."""
        mock_cover_coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"sun_motion": None},
            attributes={},
        )

        sensor = RoomCoverSunInfrontProxySensor(
            source_coordinator=mock_cover_coordinator,
            room_coordinator=mock_room_coordinator,
            cover_name="Kitchen Blinds",
            cover_id="cover_789",
            room_id="room_123",
        )

        assert sensor.available is False


# =============================================================================
# Integration Tests for async_setup_entry with Proxy Sensors
# =============================================================================


class TestSensorAsyncSetupEntryProxySensors:
    """Tests for sensor async_setup_entry creating proxy sensors."""

    @pytest.fixture
    def mock_room_coordinator(self, mock_room_config_entry: MagicMock) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            cloud_coverage=45.0,
            comfort_status="comfortable",
            sensor_available={},
            last_known={},
        )
        coordinator.comfort_status = "comfortable"
        coordinator._child_coordinators = []
        coordinator.last_update_success = True
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        coordinator.config_entry = mock_room_config_entry
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock cover coordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={
                "state": 50,
                "start": datetime(2024, 6, 21, 8, 0, 0),
                "end": datetime(2024, 6, 21, 20, 0, 0),
            },
            attributes={},
        )
        coordinator.control_mode = "auto"
        coordinator.room_coordinator = None
        return coordinator

    @pytest.fixture
    def mock_cover_in_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover in room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_in_room"
        entry.data = {
            "name": "Test Cover in Room",
            CONF_ENTRY_TYPE: EntryType.COVER,
            CONF_ROOM_ID: "room_123",
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {
            CONF_CLOUD_ENTITY: "sensor.cloud",
            CONF_TEMP_ENTITY: "sensor.inside_temp",
        }
        entry.async_on_unload = MagicMock()
        return entry

    @pytest.mark.asyncio
    async def test_cover_in_room_creates_proxy_sensors(
        self,
        hass: HomeAssistant,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test cover in room creates proxy sensors for room data."""
        from custom_components.adaptive_cover.sensor import async_setup_entry

        # Set up room coordinator
        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator,
            "room_room_123": mock_room_coordinator,
        }
        mock_cover_coordinator.room_coordinator = mock_room_coordinator

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        # Cover in room should get: position, start, end + cloud proxy, comfort proxy
        entity_types = [type(e).__name__ for e in entities_added]
        assert "CoverRoomCloudProxySensor" in entity_types
        assert "CoverRoomComfortProxySensor" in entity_types

    @pytest.mark.asyncio
    async def test_room_creates_position_proxy_for_registered_covers(
        self,
        hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test room creates position proxy sensors for registered covers."""
        from custom_components.adaptive_cover.sensor import async_setup_entry

        # Create a mock cover coordinator that's registered with room
        mock_child_cover = MagicMock()
        mock_child_cover.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"state": 50},
            attributes={},
        )
        mock_child_cover.config_entry = MagicMock()
        mock_child_cover.config_entry.data = {"name": "Child Cover"}
        mock_child_cover.config_entry.entry_id = "child_cover_123"
        mock_child_cover.async_add_listener = MagicMock(return_value=MagicMock())

        mock_room_coordinator._child_coordinators = [mock_child_cover]

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        # Room should create a position proxy for the registered cover
        entity_types = [type(e).__name__ for e in entities_added]
        assert "RoomCoverPositionProxySensor" in entity_types


class TestBinarySensorAsyncSetupEntryProxySensors:
    """Tests for binary_sensor async_setup_entry creating proxy sensors."""

    @pytest.fixture
    def mock_room_coordinator(self, mock_room_config_entry: MagicMock) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": True},
            last_known={"is_presence": True, "has_direct_sun": True},
        )
        coordinator._child_coordinators = []
        coordinator.last_update_success = True
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        coordinator.config_entry = mock_room_config_entry
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock cover coordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"sun_motion": True},
            attributes={},
        )
        coordinator.room_coordinator = None
        return coordinator

    @pytest.fixture
    def mock_cover_in_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover in room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_in_room"
        entry.data = {
            "name": "Test Cover in Room",
            CONF_ENTRY_TYPE: EntryType.COVER,
            CONF_ROOM_ID: "room_123",
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {
            CONF_PRESENCE_ENTITY: "binary_sensor.presence",
            CONF_WEATHER_ENTITY: "weather.home",
        }
        entry.async_on_unload = MagicMock()
        return entry

    @pytest.mark.asyncio
    async def test_cover_in_room_creates_binary_proxy_sensors(
        self,
        hass: HomeAssistant,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test cover in room creates binary proxy sensors for room data."""
        from custom_components.adaptive_cover.binary_sensor import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator,
            "room_room_123": mock_room_coordinator,
        }
        mock_cover_coordinator.room_coordinator = mock_room_coordinator

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        # Cover in room should get: sun_infront + occupied proxy + direct sun proxy
        entity_types = [type(e).__name__ for e in entities_added]
        assert "CoverRoomOccupiedProxySensor" in entity_types
        assert "CoverRoomDirectSunProxySensor" in entity_types

    @pytest.mark.asyncio
    async def test_room_creates_sun_infront_proxy_for_registered_covers(
        self,
        hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test room creates sun infront proxy sensors for registered covers."""
        from custom_components.adaptive_cover.binary_sensor import async_setup_entry

        # Create a mock cover coordinator that's registered with room
        mock_child_cover = MagicMock()
        mock_child_cover.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"sun_motion": True},
            attributes={},
        )
        mock_child_cover.config_entry = MagicMock()
        mock_child_cover.config_entry.data = {"name": "Child Cover"}
        mock_child_cover.config_entry.entry_id = "child_cover_123"
        mock_child_cover.async_add_listener = MagicMock(return_value=MagicMock())

        mock_room_coordinator._child_coordinators = [mock_child_cover]

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        # Room should create a sun infront proxy for the registered cover
        entity_types = [type(e).__name__ for e in entities_added]
        assert "RoomCoverSunInfrontProxySensor" in entity_types


# =============================================================================
# Dynamic Proxy Sensor Creation Tests
# =============================================================================


class TestDynamicProxySensorCreation:
    """Tests for dynamic proxy sensor creation via dispatcher signals."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": True},
            last_known={"is_presence": True, "has_direct_sun": True},
        )
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"name": "Test Room"}
        coordinator.config_entry.entry_id = "room_123"
        coordinator._child_coordinators = []
        coordinator.last_update_success = True
        coordinator.comfort_status = "comfortable"
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        entry.async_on_unload = MagicMock()
        return entry

    @pytest.mark.asyncio
    async def test_sensor_setup_registers_dispatcher_listener(
        self,
        hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test sensor async_setup_entry registers dispatcher listener for SIGNAL_COVER_REGISTERED."""
        from custom_components.adaptive_cover.sensor import async_setup_entry

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        with patch(
            "custom_components.adaptive_cover.sensor.async_dispatcher_connect"
        ) as mock_dispatcher:
            mock_dispatcher.return_value = MagicMock()

            await async_setup_entry(hass, mock_room_config_entry, add_entities)

            # Should register dispatcher listener for SIGNAL_COVER_REGISTERED
            mock_dispatcher.assert_called()
            call_args = mock_dispatcher.call_args
            expected_signal = (
                f"{SIGNAL_COVER_REGISTERED}_{mock_room_config_entry.entry_id}"
            )
            assert call_args[0][1] == expected_signal

    @pytest.mark.asyncio
    async def test_binary_sensor_setup_registers_dispatcher_listener(
        self,
        hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test binary_sensor async_setup_entry registers dispatcher listener."""
        from custom_components.adaptive_cover.binary_sensor import async_setup_entry

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        with patch(
            "custom_components.adaptive_cover.binary_sensor.async_dispatcher_connect"
        ) as mock_dispatcher:
            mock_dispatcher.return_value = MagicMock()

            await async_setup_entry(hass, mock_room_config_entry, add_entities)

            # Should register dispatcher listener for SIGNAL_COVER_REGISTERED
            mock_dispatcher.assert_called()
            call_args = mock_dispatcher.call_args
            expected_signal = (
                f"{SIGNAL_COVER_REGISTERED}_{mock_room_config_entry.entry_id}"
            )
            assert call_args[0][1] == expected_signal
