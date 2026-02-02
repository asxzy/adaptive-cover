"""Tests for sensor module."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_cover.const import (
    CONF_CLOUD_ENTITY,
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    CONF_TEMP_ENTITY,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    DOMAIN,
    EntryType,
)
from custom_components.adaptive_cover.coordinator import AdaptiveCoverData
from custom_components.adaptive_cover.room_coordinator import RoomData
from custom_components.adaptive_cover.sensor import (
    AdaptiveCoverCloudSensorEntity,
    AdaptiveCoverControlSensorEntity,
    AdaptiveCoverSensorEntity,
    AdaptiveCoverTimeSensorEntity,
    AdaptiveRoomComfortStatusSensorEntity,
    async_setup_entry,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestAdaptiveCoverSensorEntity:
    """Tests for AdaptiveCoverSensorEntity (position sensor)."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"state": 50, "start": datetime.now(), "end": datetime.now()},
            attributes={"azimuth": 180, "fov": [90, 270]},
        )
        coordinator.control_mode = CONTROL_MODE_AUTO
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
    def mock_hass(self, hass: HomeAssistant) -> HomeAssistant:
        """Return Home Assistant instance."""
        return hass

    def test_init_standalone(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test initialization for standalone cover."""
        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor._name == "Test Cover"
        assert sensor._attr_unique_id == "test_cover_entry_Cover Position"
        assert sensor._attr_name == "Cover Position"
        assert sensor._room_id is None

    def test_init_cover_in_room(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test initialization for cover in room."""
        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        assert sensor._room_id == "room_123"
        assert sensor._attr_name == "Test Cover Cover Position"
        assert sensor._attr_has_entity_name is False

    def test_native_value(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns position from states."""
        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value == 50

    def test_native_value_no_data(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_cover_coordinator.data = None

        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value is None

    def test_available_disabled_mode(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test available is False when control mode is disabled."""
        mock_cover_coordinator.control_mode = CONTROL_MODE_DISABLED

        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.available is False

    def test_available_no_data(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test available is False when data is None."""
        mock_cover_coordinator.data = None

        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.available is False

    def test_available_no_state(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test available is False when state is None."""
        mock_cover_coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"state": None},
            attributes={},
        )

        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.available is False

    def test_device_info(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test device_info returns correct identifiers."""
        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        device_info = sensor.device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "test_cover_entry"
        assert device_info["name"] == "Test Cover"

    def test_device_info_with_room(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test device_info includes via_device when in room."""
        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        device_info = sensor.device_info
        assert "via_device" in device_info
        assert device_info["via_device"] == (DOMAIN, "room_room_123")

    def test_extra_state_attributes(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns coordinator attributes."""
        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["azimuth"] == 180
        assert attrs["fov"] == [90, 270]

    def test_extra_state_attributes_no_data(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no data."""
        mock_cover_coordinator.data = None

        sensor = AdaptiveCoverSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.extra_state_attributes is None


class TestAdaptiveCoverTimeSensorEntity:
    """Tests for AdaptiveCoverTimeSensorEntity (start/end sun)."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
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
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_hass(self, hass: HomeAssistant) -> HomeAssistant:
        """Return Home Assistant instance."""
        return hass

    def test_native_value_start(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns start time."""
        sensor = AdaptiveCoverTimeSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            sensor_name="Start Sun",
            key="start",
            icon="mdi:sun-clock-outline",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value == datetime(2024, 6, 21, 8, 0, 0)

    def test_native_value_end(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns end time."""
        sensor = AdaptiveCoverTimeSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            sensor_name="End Sun",
            key="end",
            icon="mdi:sun-clock",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value == datetime(2024, 6, 21, 20, 0, 0)

    def test_native_value_no_data(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_cover_coordinator.data = None

        sensor = AdaptiveCoverTimeSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            sensor_name="Start Sun",
            key="start",
            icon="mdi:sun-clock-outline",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value is None


class TestAdaptiveCoverControlSensorEntity:
    """Tests for AdaptiveCoverControlSensorEntity (comfort status)."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"comfort_status": "comfortable"},
            attributes={},
        )
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_hass(self, hass: HomeAssistant) -> HomeAssistant:
        """Return Home Assistant instance."""
        return hass

    def test_native_value(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns comfort_status."""
        sensor = AdaptiveCoverControlSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value == "comfortable"

    def test_native_value_no_data(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_cover_coordinator.data = None

        sensor = AdaptiveCoverControlSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value is None


class TestAdaptiveRoomComfortStatusSensorEntity:
    """Tests for AdaptiveRoomComfortStatusSensorEntity."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        coordinator = MagicMock()
        coordinator.comfort_status = "comfortable"
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_hass(self, hass: HomeAssistant) -> HomeAssistant:
        """Return Home Assistant instance."""
        return hass

    def test_native_value(
        self,
        mock_hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns aggregated comfort_status."""
        sensor = AdaptiveRoomComfortStatusSensorEntity(
            unique_id=mock_room_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_room_config_entry,
            name="Test Room",
            coordinator=mock_room_coordinator,
        )

        assert sensor.native_value == "comfortable"


class TestAdaptiveCoverCloudSensorEntity:
    """Tests for AdaptiveCoverCloudSensorEntity."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"cloud_coverage": 25.0},
            attributes={},
        )
        return coordinator

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
            last_known={"cloud": 30.0},
        )
        # Required for super().available check
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_hass(self, hass: HomeAssistant) -> HomeAssistant:
        """Return Home Assistant instance."""
        return hass

    def test_native_value_cover_coordinator(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test native_value with cover coordinator."""
        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.native_value == 25.0

    def test_native_value_room_coordinator(
        self,
        mock_hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test native_value with room coordinator."""
        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_room_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_room_config_entry,
            name="Test Room",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.native_value == 30.0

    def test_native_value_room_no_data(
        self,
        mock_hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when room has no data."""
        mock_room_coordinator.data = None

        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_room_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_room_config_entry,
            name="Test Room",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.native_value is None

    def test_available_cover_coordinator(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test available with cover coordinator."""
        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.available is True

    def test_available_cover_coordinator_no_cloud(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test available returns False when no cloud data."""
        mock_cover_coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={},
            attributes={},
        )

        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        assert sensor.available is False

    def test_available_room_coordinator(
        self,
        mock_hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test available with room coordinator."""
        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_room_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_room_config_entry,
            name="Test Room",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.available is True

    def test_available_room_coordinator_no_cloud(
        self,
        mock_hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test available returns False when room has no cloud data."""
        mock_room_coordinator.data = RoomData(
            control_mode="auto",
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=True,
            has_direct_sun=True,
            last_known={},
        )
        # Ensure last_update_success is still set
        mock_room_coordinator.last_update_success = True

        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_room_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_room_config_entry,
            name="Test Room",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert sensor.available is False

    def test_device_info_room(
        self,
        mock_hass: HomeAssistant,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test device_info for room cloud sensor."""
        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_room_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_room_config_entry,
            name="Test Room",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        device_info = sensor.device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "room_test_room_entry"

    def test_device_info_standalone(
        self,
        mock_hass: HomeAssistant,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test device_info for standalone cloud sensor."""
        sensor = AdaptiveCoverCloudSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
        )

        device_info = sensor.device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "test_cover_entry"


class TestSensorAsyncSetupEntry:
    """Tests for sensor async_setup_entry function."""

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
            last_known={"cloud": 30.0},
        )
        coordinator.comfort_status = "comfortable"
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
                "start": datetime(2024, 6, 21, 8, 0, 0),
                "end": datetime(2024, 6, 21, 20, 0, 0),
                "comfort_status": "comfortable",
                "cloud_coverage": 25.0,
            },
            attributes={"azimuth": 180, "fov": [90, 270]},
        )
        coordinator.control_mode = CONTROL_MODE_AUTO
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {
            CONF_TEMP_ENTITY: "sensor.inside_temp",
        }
        return entry

    @pytest.fixture
    def mock_room_config_entry_with_cloud(self) -> MagicMock:
        """Create mock ConfigEntry for room with cloud entity."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {
            CONF_CLOUD_ENTITY: "sensor.cloud",
            CONF_TEMP_ENTITY: "sensor.inside_temp",
        }
        return entry

    @pytest.fixture
    def mock_standalone_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for standalone cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {
            CONF_TEMP_ENTITY: "sensor.inside_temp",
        }
        return entry

    @pytest.fixture
    def mock_standalone_cover_with_cloud_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for standalone cover with cloud entity."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {
            CONF_CLOUD_ENTITY: "sensor.cloud",
            CONF_TEMP_ENTITY: "sensor.inside_temp",
        }
        return entry

    @pytest.fixture
    def mock_cover_in_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover in room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_in_room_entry"
        entry.data = {
            "name": "Test Cover in Room",
            CONF_ENTRY_TYPE: EntryType.COVER,
            CONF_ROOM_ID: "room_123",
        }
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_setup_room_entry_creates_sensors_and_comfort_status(
        self,
        hass,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates sensors for room."""
        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        # Room gets: Comfort Status (no cloud, no outside temp)
        assert len(entities_added) == 1

        entity_types = [type(e).__name__ for e in entities_added]
        assert "AdaptiveRoomComfortStatusSensorEntity" in entity_types

    @pytest.mark.asyncio
    async def test_setup_room_entry_with_cloud_creates_cloud_sensor(
        self,
        hass,
        mock_room_config_entry_with_cloud: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates cloud sensor for room with cloud entity."""
        hass.data[DOMAIN] = {
            mock_room_config_entry_with_cloud.entry_id: mock_room_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry_with_cloud, add_entities)

        # Room with cloud gets: Cloud, Comfort Status
        assert len(entities_added) == 2

        entity_types = [type(e).__name__ for e in entities_added]
        assert "AdaptiveCoverCloudSensorEntity" in entity_types

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_creates_position_sensor(
        self,
        hass,
        mock_standalone_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates position sensor for standalone cover."""
        hass.data[DOMAIN] = {
            mock_standalone_cover_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_standalone_cover_config_entry, add_entities)

        # Standalone cover gets: Position, Start Sun, End Sun, Comfort Status (no cloud)
        assert len(entities_added) == 4

        entity_types = [type(e).__name__ for e in entities_added]
        assert "AdaptiveCoverSensorEntity" in entity_types
        assert "AdaptiveCoverTimeSensorEntity" in entity_types
        assert "AdaptiveCoverControlSensorEntity" in entity_types

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_with_cloud_creates_cloud_sensor(
        self,
        hass,
        mock_standalone_cover_with_cloud_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates cloud sensor for standalone cover with cloud."""
        hass.data[DOMAIN] = {
            mock_standalone_cover_with_cloud_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(
            hass, mock_standalone_cover_with_cloud_config_entry, add_entities
        )

        # Standalone cover with cloud gets: Position, Start, End, Comfort, Cloud
        assert len(entities_added) == 5

        entity_types = [type(e).__name__ for e in entities_added]
        assert "AdaptiveCoverCloudSensorEntity" in entity_types

    @pytest.mark.asyncio
    async def test_setup_cover_in_room_creates_sensors(
        self,
        hass,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates sensors for cover in room."""
        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        # Cover in room gets: Position, Start, End time sensors
        # (no proxy sensors without room_coordinator in hass.data)
        assert len(entities_added) == 3

        entity_types = [type(e).__name__ for e in entities_added]
        assert "AdaptiveCoverSensorEntity" in entity_types
        assert "AdaptiveCoverTimeSensorEntity" in entity_types

        # Verify position sensor knows it's in a room
        position_sensors = [
            e for e in entities_added if type(e).__name__ == "AdaptiveCoverSensorEntity"
        ]
        assert position_sensors[0]._room_id == "room_123"


class TestTimeSensorEntityDeviceInfoWithRoom:
    """Tests for time sensor device info with room_id."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
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
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_hass(self, hass) -> MagicMock:
        """Return Home Assistant instance."""
        return hass

    def test_time_sensor_device_info_with_room_id(
        self,
        mock_hass,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test device_info includes via_device when room_id is set."""
        sensor = AdaptiveCoverTimeSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            sensor_name="Start Sun",
            key="start",
            icon="mdi:sun-clock-outline",
            coordinator=mock_cover_coordinator,
            room_id="room_456",
        )

        device_info = sensor.device_info
        assert "via_device" in device_info
        assert device_info["via_device"] == (DOMAIN, "room_room_456")

    def test_time_sensor_name_includes_cover_name_with_room_id(
        self,
        mock_hass,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test sensor name includes cover name when room_id is set."""
        sensor = AdaptiveCoverTimeSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            sensor_name="Start Sun",
            key="start",
            icon="mdi:sun-clock-outline",
            coordinator=mock_cover_coordinator,
            room_id="room_456",
        )

        assert sensor._attr_name == "Test Cover Start Sun"
        assert sensor._attr_has_entity_name is False


class TestControlSensorEntityWithRoom:
    """Tests for control sensor device info with room_id."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states={"comfort_status": "comfortable"},
            attributes={},
        )
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_hass(self, hass) -> MagicMock:
        """Return Home Assistant instance."""
        return hass

    def test_control_sensor_device_info_with_room_id(
        self,
        mock_hass,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test device_info includes via_device when room_id is set."""
        sensor = AdaptiveCoverControlSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
            room_id="room_789",
        )

        device_info = sensor.device_info
        assert "via_device" in device_info
        assert device_info["via_device"] == (DOMAIN, "room_room_789")

    def test_control_sensor_name_includes_cover_name_with_room_id(
        self,
        mock_hass,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test sensor name includes cover name when room_id is set."""
        sensor = AdaptiveCoverControlSensorEntity(
            unique_id=mock_cover_config_entry.entry_id,
            hass=mock_hass,
            config_entry=mock_cover_config_entry,
            name="Test Cover",
            coordinator=mock_cover_coordinator,
            room_id="room_789",
        )

        assert sensor._attr_name == "Test Cover Comfort Status"
        assert sensor._attr_has_entity_name is False
