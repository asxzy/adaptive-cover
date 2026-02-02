"""Tests for binary_sensor module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest


from custom_components.adaptive_cover.binary_sensor import AdaptiveCoverBinarySensor
from custom_components.adaptive_cover.const import (
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    DOMAIN,
    EntryType,
)
from custom_components.adaptive_cover.coordinator import AdaptiveCoverData
from custom_components.adaptive_cover.room_coordinator import RoomData

if TYPE_CHECKING:
    pass


class TestAdaptiveCoverBinarySensor:
    """Tests for AdaptiveCoverBinarySensor."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={
                "state": 50,
                "sun_motion": True,
                "is_presence": True,
                "has_direct_sun": True,
                "is_presence_available": True,
                "has_direct_sun_available": True,
            },
            attributes={"azimuth": 180, "fov": [90, 270]},
        )
        return coordinator

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": True},
            last_known={"is_presence": True, "has_direct_sun": True},
        )
        # Required for super().available check
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        return entry

    def test_init_standalone_cover(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for standalone cover."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Sun Infront",
            state=False,
            key="sun_motion",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_cover_coordinator,
        )

        assert sensor._key == "sun_motion"
        assert sensor._name == "Test Cover"
        assert sensor._attr_unique_id == "test_cover_entry_Sun Infront"
        assert sensor._is_room is False

    def test_init_room_entry(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test initialization for room entry."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor._key == "is_presence"
        assert sensor._is_room is True
        assert "room_" in str(sensor._attr_device_info["identifiers"])

    def test_init_cover_in_room(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for cover inside a room."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Sun Infront",
            state=False,
            key="sun_motion",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        assert sensor._room_id == "room_123"
        # Cover in room should have full name
        assert sensor._attr_name == "Test Cover Sun Infront"
        assert sensor._attr_has_entity_name is False

    def test_is_on_cover_coordinator(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test is_on property with cover coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Sun Infront",
            state=False,
            key="sun_motion",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_cover_coordinator,
        )

        assert sensor.is_on is True

    def test_is_on_room_coordinator_presence(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test is_on property for presence with room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.is_on is True

    def test_is_on_room_coordinator_has_direct_sun(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test is_on property for has_direct_sun with room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Weather Has Direct Sun",
            state=False,
            key="has_direct_sun",
            device_class=BinarySensorDeviceClass.LIGHT,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.is_on is True

    def test_is_on_room_coordinator_no_data(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test is_on returns None when room coordinator has no data."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        mock_room_coordinator.data = None

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.is_on is None

    def test_available_cover_coordinator(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test available property with cover coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Weather Has Direct Sun",
            state=False,
            key="has_direct_sun",
            device_class=BinarySensorDeviceClass.LIGHT,
            coordinator=mock_cover_coordinator,
        )

        # Mock super().available to return True
        # The sensor should be available when data has the key
        assert sensor.available is True

    def test_available_room_coordinator_presence(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available property for presence with room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        # Should be available since sensor_available is True
        assert sensor.available is True

    def test_available_room_coordinator_no_data(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns False when room coordinator has no data."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        mock_room_coordinator.data = None
        mock_room_coordinator.last_update_success = True  # Needed for super().available

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.available is False

    def test_extra_state_attributes_cover_coordinator(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes with cover coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Weather Has Direct Sun",
            state=False,
            key="has_direct_sun",
            device_class=BinarySensorDeviceClass.LIGHT,
            coordinator=mock_cover_coordinator,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "sensor_available" in attrs
        assert "current_value" in attrs

    def test_extra_state_attributes_room_coordinator(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes with room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "sensor_available" in attrs
        assert "current_value" in attrs

    def test_extra_state_attributes_sun_motion_returns_none(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes returns None for sun_motion key."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Sun Infront",
            state=False,
            key="sun_motion",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_cover_coordinator,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is None

    def test_extra_state_attributes_room_no_data(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes returns None when room has no data."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        mock_room_coordinator.data = None

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is None

    def test_is_on_room_unknown_key(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test is_on returns None for unknown key on room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Unknown",
            state=False,
            key="unknown_key",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.is_on is None


class TestBinarySensorAsyncSetupEntry:
    """Tests for binary_sensor async_setup_entry function."""

    @pytest.fixture
    def mock_room_coordinator(self, mock_room_config_entry: MagicMock) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": True},
            last_known={"is_presence": True, "has_direct_sun": True},
        )
        coordinator.last_update_success = True
        coordinator._child_coordinators = []
        coordinator.config_entry = mock_room_config_entry
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={
                "state": 50,
                "sun_motion": True,
                "is_presence": True,
                "has_direct_sun": True,
                "is_presence_available": True,
                "has_direct_sun_available": True,
            },
            attributes={"azimuth": 180, "fov": [90, 270]},
        )
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_cover_in_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover in room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_room_entry"
        entry.data = {
            "name": "Test Cover in Room",
            CONF_ENTRY_TYPE: EntryType.COVER,
            CONF_ROOM_ID: "room_123",
        }
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_setup_room_entry_creates_binary_sensors(
        self,
        hass,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates binary sensors for room."""
        from custom_components.adaptive_cover.binary_sensor import async_setup_entry

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        # Room gets: is_presence and has_direct_sun
        assert len(entities_added) == 2
        keys = {e._key for e in entities_added}
        assert keys == {"is_presence", "has_direct_sun"}
        assert all(e._is_room is True for e in entities_added)

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_creates_binary_sensors(
        self,
        hass,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all binary sensors for standalone cover."""
        from custom_components.adaptive_cover.binary_sensor import async_setup_entry

        hass.data[DOMAIN] = {mock_cover_config_entry.entry_id: mock_cover_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_config_entry, add_entities)

        # Standalone covers get sun_motion + is_presence + has_direct_sun
        assert len(entities_added) == 3
        keys = {e._key for e in entities_added}
        assert keys == {"sun_motion", "is_presence", "has_direct_sun"}

    @pytest.mark.asyncio
    async def test_setup_cover_in_room_creates_sun_motion_sensor(
        self,
        hass,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates sun motion sensor for cover in room (no room loaded)."""
        from custom_components.adaptive_cover.binary_sensor import async_setup_entry

        # Ensure cover coordinator doesn't have room_coordinator reference
        mock_cover_coordinator.room_coordinator = None

        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        # Cover in room without room_coordinator loaded gets only sun_motion
        assert len(entities_added) == 1
        assert entities_added[0]._key == "sun_motion"
        assert entities_added[0]._room_id == "room_123"


class TestBinarySensorAvailabilityEdgeCases:
    """Tests for availability edge cases."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": True},
            last_known={"is_presence": True, "has_direct_sun": True},
        )
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={
                "state": 50,
                "sun_motion": True,
                "is_presence": True,
                "has_direct_sun": True,
                "is_presence_available": True,
                "has_direct_sun_available": True,
            },
            attributes={"azimuth": 180, "fov": [90, 270]},
        )
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {}
        return entry

    def test_available_super_unavailable_returns_false(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test available returns False when super().available is False."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        # Set last_update_success to False to make super().available return False
        mock_room_coordinator.last_update_success = False

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Room Occupied",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        # Should return False because super().available is False
        assert sensor.available is False

    def test_available_room_has_direct_sun_with_last_known_fallback(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test has_direct_sun availability uses last known value as fallback."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        # Sensor unavailable but has last known value
        mock_room_coordinator.data = RoomData(
            control_mode="auto",
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": False},
            last_known={"is_presence": True, "has_direct_sun": True},
        )

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Weather Has Direct Sun",
            state=False,
            key="has_direct_sun",
            device_class=BinarySensorDeviceClass.LIGHT,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        # Should be available because we have a last known value
        assert sensor.available is True

    def test_available_room_unknown_key_returns_true(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test availability returns True for unknown keys in room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Unknown",
            state=False,
            key="unknown_key",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        # Unknown key should return True (default)
        assert sensor.available is True

    def test_available_cover_is_presence_none(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test cover availability returns False when is_presence is None."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        # Set is_presence to None
        mock_cover_coordinator.data.states["is_presence"] = None
        mock_cover_coordinator.last_update_success = True

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Presence",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_cover_coordinator,
        )

        # Should be unavailable when is_presence is None
        assert sensor.available is False

    def test_available_cover_has_direct_sun_none(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test cover availability returns False when has_direct_sun is None."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        # Set has_direct_sun to None
        mock_cover_coordinator.data.states["has_direct_sun"] = None
        mock_cover_coordinator.last_update_success = True

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Direct Sun",
            state=False,
            key="has_direct_sun",
            device_class=BinarySensorDeviceClass.LIGHT,
            coordinator=mock_cover_coordinator,
        )

        # Should be unavailable when has_direct_sun is None
        assert sensor.available is False


class TestBinarySensorExtraAttributesEdgeCases:
    """Tests for extra state attributes edge cases."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.data = RoomData(
            control_mode="auto",
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            sensor_available={"is_presence": True, "has_direct_sun": True},
            last_known={"is_presence": True, "has_direct_sun": True},
        )
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={
                "state": 50,
                "sun_motion": True,
                "is_presence": True,
                "has_direct_sun": True,
                "is_presence_available": True,
                "has_direct_sun_available": True,
            },
            attributes={"azimuth": 180, "fov": [90, 270]},
        )
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {}
        return entry

    def test_extra_attrs_room_has_direct_sun(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes for has_direct_sun in room coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Weather Has Direct Sun",
            state=False,
            key="has_direct_sun",
            device_class=BinarySensorDeviceClass.LIGHT,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "sensor_available" in attrs
        assert attrs["sensor_available"] is True
        assert "using_last_known" in attrs
        assert "current_value" in attrs

    def test_extra_attrs_room_unknown_key_returns_none(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes returns None for unknown key in room."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            binary_name="Unknown",
            state=False,
            key="unknown_key",
            device_class=BinarySensorDeviceClass.MOTION,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is None

    def test_extra_attrs_cover_is_presence(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test extra_state_attributes for is_presence in cover coordinator."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AdaptiveCoverBinarySensor(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            binary_name="Presence",
            state=False,
            key="is_presence",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            coordinator=mock_cover_coordinator,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "sensor_available" in attrs
        assert "using_last_known" in attrs
        assert "current_value" in attrs
