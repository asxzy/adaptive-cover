"""Tests for switch module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.adaptive_cover.const import (
    CONF_CLIMATE_MODE,
    CONF_CLOUD_ENTITY,
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_IRRADIANCE_ENTITY,
    CONF_LUX_ENTITY,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_ROOM_ID,
    CONF_WEATHER_ENTITY,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    CONTROL_MODE_FORCE,
    DOMAIN,
    EntryType,
)
from custom_components.adaptive_cover.switch import AdaptiveCoverSwitch

if TYPE_CHECKING:
    pass


class TestAdaptiveCoverSwitch:
    """Tests for AdaptiveCoverSwitch."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.temp_toggle = None
        coordinator.lux_toggle = None
        coordinator.irradiance_toggle = None
        coordinator.cloud_toggle = None
        coordinator.weather_toggle = None
        return coordinator

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.async_notify_children = AsyncMock()
        coordinator.temp_toggle = None
        coordinator.lux_toggle = None
        coordinator.irradiance_toggle = None
        coordinator.cloud_toggle = None
        coordinator.weather_toggle = None
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

    def test_init_room(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test initialization for room entry."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            switch_name="Outside Temperature",
            initial_state=False,
            key="temp_toggle",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert switch._name == "Test Room"
        assert switch._attr_unique_id == "test_room_entry_Outside Temperature"
        assert switch._is_room is True
        assert switch._key == "temp_toggle"
        assert "room_" in str(switch._attr_device_info["identifiers"])

    def test_init_standalone(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for standalone cover."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        assert switch._name == "Test Cover"
        assert switch._attr_unique_id == "test_cover_entry_Lux"
        assert switch._is_room is False
        assert switch._initial_state is True

    def test_init_with_room_id(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for cover with room_id."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Weather",
            initial_state=True,
            key="weather_toggle",
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        assert switch._room_id == "room_123"
        assert switch._attr_name == "Test Cover Weather"
        assert switch._attr_has_entity_name is False

    def test_available_auto_mode(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test available is True in AUTO mode."""
        mock_cover_coordinator.control_mode = CONTROL_MODE_AUTO

        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        assert switch.available is True

    def test_available_disabled_mode(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test available is False in DISABLED mode."""
        mock_cover_coordinator.control_mode = CONTROL_MODE_DISABLED

        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        assert switch.available is False

    def test_available_force_mode(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test available is False in FORCE mode."""
        mock_cover_coordinator.control_mode = CONTROL_MODE_FORCE

        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        assert switch.available is False

    @pytest.mark.asyncio
    async def test_turn_on(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test turn_on sets coordinator attribute."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=False,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        # Mock schedule_update_ha_state
        switch.schedule_update_ha_state = MagicMock()

        await switch.async_turn_on()

        assert switch._attr_is_on is True
        assert mock_cover_coordinator.lux_toggle is True
        assert mock_cover_coordinator.state_change is True
        mock_cover_coordinator.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_with_added_flag(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test turn_on with added flag skips refresh."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=False,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        # Mock schedule_update_ha_state
        switch.schedule_update_ha_state = MagicMock()

        await switch.async_turn_on(added=True)

        assert switch._attr_is_on is True
        assert mock_cover_coordinator.lux_toggle is True
        # async_refresh should NOT be called when added=True
        mock_cover_coordinator.async_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_turn_off(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test turn_off sets coordinator attribute."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        # Mock schedule_update_ha_state
        switch.schedule_update_ha_state = MagicMock()

        await switch.async_turn_off()

        assert switch._attr_is_on is False
        assert mock_cover_coordinator.lux_toggle is False
        assert mock_cover_coordinator.state_change is True
        mock_cover_coordinator.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_with_added_flag(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test turn_off with added flag skips refresh."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        # Mock schedule_update_ha_state
        switch.schedule_update_ha_state = MagicMock()

        await switch.async_turn_off(added=True)

        assert switch._attr_is_on is False
        assert mock_cover_coordinator.lux_toggle is False
        # async_refresh should NOT be called when added=True
        mock_cover_coordinator.async_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_turn_on_room_notifies_children(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test turn_on for room notifies children."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            switch_name="Weather",
            initial_state=False,
            key="weather_toggle",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        # Mock schedule_update_ha_state
        switch.schedule_update_ha_state = MagicMock()

        await switch.async_turn_on()

        assert switch._attr_is_on is True
        assert mock_room_coordinator.weather_toggle is True
        mock_room_coordinator.async_refresh.assert_called_once()
        mock_room_coordinator.async_notify_children.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_room_notifies_children(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test turn_off for room notifies children."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            switch_name="Cloud Coverage",
            initial_state=True,
            key="cloud_toggle",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        # Mock schedule_update_ha_state
        switch.schedule_update_ha_state = MagicMock()

        await switch.async_turn_off()

        assert switch._attr_is_on is False
        assert mock_room_coordinator.cloud_toggle is False
        mock_room_coordinator.async_refresh.assert_called_once()
        mock_room_coordinator.async_notify_children.assert_called_once()

    def test_device_info_room(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test device info for room switch."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        device_info = switch._attr_device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "room_test_room_entry"
        assert device_info["name"] == "Room: Test Room"

    def test_device_info_standalone(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test device info for standalone switch."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        device_info = switch._attr_device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "test_cover_entry"
        assert device_info["name"] == "Test Cover"

    def test_device_info_with_via_device(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test device info with via_device for cover in room."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Weather",
            initial_state=True,
            key="weather_toggle",
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        device_info = switch._attr_device_info
        assert "via_device" in device_info
        assert device_info["via_device"] == (DOMAIN, "room_room_123")

    def test_different_switch_keys(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test different switch keys are handled correctly."""
        keys = [
            ("temp_toggle", "Outside Temperature"),
            ("lux_toggle", "Lux"),
            ("irradiance_toggle", "Irradiance"),
            ("cloud_toggle", "Cloud Coverage"),
            ("weather_toggle", "Weather"),
        ]

        for key, name in keys:
            switch = AdaptiveCoverSwitch(
                config_entry=mock_cover_config_entry,
                unique_id=mock_cover_config_entry.entry_id,
                switch_name=name,
                initial_state=True,
                key=key,
                coordinator=mock_cover_coordinator,
            )

            assert switch._key == key
            assert switch._attr_translation_key == key


class TestSwitchAsyncSetupEntry:
    """Tests for switch async_setup_entry function."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.async_notify_children = AsyncMock()
        coordinator.temp_toggle = None
        coordinator.lux_toggle = None
        coordinator.irradiance_toggle = None
        coordinator.cloud_toggle = None
        coordinator.weather_toggle = None
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.temp_toggle = None
        coordinator.lux_toggle = None
        coordinator.irradiance_toggle = None
        coordinator.cloud_toggle = None
        coordinator.weather_toggle = None
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_room_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for room with all sensor entities."""
        entry = MagicMock()
        entry.entry_id = "test_room_entry"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        # Room entries always have climate_mode=True automatically
        # Need to provide entities for each switch to be created
        entry.options = {
            CONF_OUTSIDETEMP_ENTITY: "sensor.outside_temp",  # temp_switch
            CONF_LUX_ENTITY: "sensor.lux",  # lux_switch
            CONF_IRRADIANCE_ENTITY: "sensor.irradiance",  # irradiance_switch
            CONF_CLOUD_ENTITY: "sensor.cloud",  # cloud_switch
            CONF_WEATHER_ENTITY: "weather.home",  # weather_switch & temp_switch
        }
        return entry

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for standalone cover with climate mode."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        # Standalone covers need climate_mode enabled and entities configured
        entry.options = {
            CONF_ENTITIES: ["cover.living_room"],
            CONF_CLIMATE_MODE: True,
            CONF_OUTSIDETEMP_ENTITY: "sensor.outside_temp",
            CONF_LUX_ENTITY: "sensor.lux",
            CONF_IRRADIANCE_ENTITY: "sensor.irradiance",
            CONF_CLOUD_ENTITY: "sensor.cloud",
            CONF_WEATHER_ENTITY: "weather.home",
        }
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
        entry.options = {CONF_ENTITIES: ["cover.living_room"]}
        return entry

    @pytest.mark.asyncio
    async def test_setup_room_entry_creates_switches(
        self,
        hass,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all 5 toggle switches for room."""
        from custom_components.adaptive_cover.switch import async_setup_entry

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        # Should create 5 switches: temp, lux, irradiance, cloud, weather
        assert len(entities_added) == 5
        keys = {e._key for e in entities_added}
        assert keys == {
            "temp_toggle",
            "lux_toggle",
            "irradiance_toggle",
            "cloud_toggle",
            "weather_toggle",
        }
        # All should be marked as room
        assert all(e._is_room is True for e in entities_added)

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_creates_switches(
        self,
        hass,
        mock_cover_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all 5 toggle switches for standalone cover."""
        from custom_components.adaptive_cover.switch import async_setup_entry

        hass.data[DOMAIN] = {mock_cover_config_entry.entry_id: mock_cover_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_config_entry, add_entities)

        # Should create 5 switches
        assert len(entities_added) == 5
        keys = {e._key for e in entities_added}
        assert keys == {
            "temp_toggle",
            "lux_toggle",
            "irradiance_toggle",
            "cloud_toggle",
            "weather_toggle",
        }
        # All should NOT be marked as room
        assert all(e._is_room is False for e in entities_added)

    @pytest.mark.asyncio
    async def test_setup_cover_in_room_no_switches(
        self,
        hass,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates no switches for cover in room (room handles it)."""
        from custom_components.adaptive_cover.switch import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        assert len(entities_added) == 0


class TestAdaptiveCoverSwitchCoordinatorUpdates:
    """Tests for AdaptiveCoverSwitch coordinator update handling."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.temp_toggle = None
        coordinator.lux_toggle = None
        coordinator.irradiance_toggle = None
        coordinator.cloud_toggle = None
        coordinator.weather_toggle = None
        return coordinator

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.async_notify_children = AsyncMock()
        coordinator.temp_toggle = None
        coordinator.lux_toggle = None
        coordinator.irradiance_toggle = None
        coordinator.cloud_toggle = None
        coordinator.weather_toggle = None
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

    def test_handle_coordinator_update_calls_async_write_ha_state(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test _handle_coordinator_update calls async_write_ha_state."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        switch.async_write_ha_state.assert_called_once()

    def test_availability_changes_with_control_mode(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test availability changes when coordinator control_mode changes."""
        mock_cover_coordinator.control_mode = CONTROL_MODE_AUTO
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )

        # Initially available in AUTO mode
        assert switch.available is True

        # Change to DISABLED - should become unavailable
        mock_cover_coordinator.control_mode = CONTROL_MODE_DISABLED
        assert switch.available is False

        # Change back to AUTO - should become available again
        mock_cover_coordinator.control_mode = CONTROL_MODE_AUTO
        assert switch.available is True

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_on_state(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass restores ON state."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=False,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )
        switch.schedule_update_ha_state = MagicMock()

        mock_state = MagicMock()
        mock_state.state = STATE_ON
        switch.async_get_last_state = AsyncMock(return_value=mock_state)

        # Mock super().async_added_to_hass() to avoid needing full hass setup
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "custom_components.adaptive_cover.switch.CoordinatorEntity.async_added_to_hass",
                AsyncMock(),
            )
            await switch.async_added_to_hass()

        assert switch._attr_is_on is True
        assert mock_cover_coordinator.lux_toggle is True

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_off_state(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass restores OFF state."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )
        switch.schedule_update_ha_state = MagicMock()

        mock_state = MagicMock()
        mock_state.state = STATE_OFF
        switch.async_get_last_state = AsyncMock(return_value=mock_state)

        # Mock super().async_added_to_hass() to avoid needing full hass setup
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "custom_components.adaptive_cover.switch.CoordinatorEntity.async_added_to_hass",
                AsyncMock(),
            )
            await switch.async_added_to_hass()

        assert switch._attr_is_on is False
        assert mock_cover_coordinator.lux_toggle is False

    @pytest.mark.asyncio
    async def test_async_added_to_hass_uses_initial_state_when_no_last_state(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass uses initial_state when no last state."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            switch_name="Lux",
            initial_state=True,
            key="lux_toggle",
            coordinator=mock_cover_coordinator,
        )
        switch.schedule_update_ha_state = MagicMock()
        switch.async_get_last_state = AsyncMock(return_value=None)

        # Mock super().async_added_to_hass() to avoid needing full hass setup
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "custom_components.adaptive_cover.switch.CoordinatorEntity.async_added_to_hass",
                AsyncMock(),
            )
            await switch.async_added_to_hass()

        # Should use initial_state=True
        assert switch._attr_is_on is True
        assert mock_cover_coordinator.lux_toggle is True

    @pytest.mark.asyncio
    async def test_async_added_to_hass_room_coordinator_restores_state(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass restores state for room coordinator."""
        switch = AdaptiveCoverSwitch(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            switch_name="Cloud Coverage",
            initial_state=False,
            key="cloud_toggle",
            coordinator=mock_room_coordinator,
            is_room=True,
        )
        switch.schedule_update_ha_state = MagicMock()

        mock_state = MagicMock()
        mock_state.state = STATE_ON
        switch.async_get_last_state = AsyncMock(return_value=mock_state)

        # Mock super().async_added_to_hass() to avoid needing full hass setup
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "custom_components.adaptive_cover.switch.CoordinatorEntity.async_added_to_hass",
                AsyncMock(),
            )
            await switch.async_added_to_hass()

        assert switch._attr_is_on is True
        assert mock_room_coordinator.cloud_toggle is True
        # Should NOT call async_refresh or notify_children (added=True flag)
        mock_room_coordinator.async_refresh.assert_not_called()
        mock_room_coordinator.async_notify_children.assert_not_called()
