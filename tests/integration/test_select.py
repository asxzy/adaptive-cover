"""Tests for select module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.adaptive_cover.const import (
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    CONTROL_MODE_FORCE,
    DOMAIN,
    EntryType,
)
from custom_components.adaptive_cover.select import ControlModeSelect

if TYPE_CHECKING:
    pass


class TestControlModeSelect:
    """Tests for ControlModeSelect."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.register_control_mode_select = MagicMock()
        coordinator.setup_midnight_reset = MagicMock()
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
        coordinator.register_control_mode_select = MagicMock()
        coordinator.setup_midnight_reset = MagicMock()
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
        select = ControlModeSelect(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            coordinator=mock_room_coordinator,
        )

        assert select._name == "Test Room"
        assert select._attr_unique_id == "test_room_entry_control_mode"
        assert select._entry_type == EntryType.ROOM
        assert select._attr_name == "Control Mode"
        assert "room_" in str(select._attr_device_info["identifiers"])

    def test_init_standalone(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for standalone cover."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        assert select._name == "Test Cover"
        assert select._attr_unique_id == "test_cover_entry_control_mode"
        assert select._entry_type == EntryType.COVER
        assert select._attr_name == "Control Mode"

    def test_init_with_room_id(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for cover with room_id."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        assert select._room_id == "room_123"
        # Cover in room should have full name
        assert select._attr_name == "Test Cover Control Mode"
        assert select._attr_has_entity_name is False

    def test_options_list(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test that options are disabled/force/auto."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        assert select._attr_options == [
            CONTROL_MODE_DISABLED,
            CONTROL_MODE_FORCE,
            CONTROL_MODE_AUTO,
        ]

    def test_initial_option(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initial option is AUTO."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        assert select._attr_current_option == CONTROL_MODE_AUTO

    @pytest.mark.asyncio
    async def test_select_option_updates_coordinator(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test selecting option updates coordinator.control_mode."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock the async_write_ha_state method since we're not in hass context
        select.async_write_ha_state = MagicMock()

        await select.async_select_option(CONTROL_MODE_DISABLED)

        assert select._attr_current_option == CONTROL_MODE_DISABLED
        assert mock_cover_coordinator.control_mode == CONTROL_MODE_DISABLED
        assert mock_cover_coordinator.state_change is True
        mock_cover_coordinator.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_option_room_notifies_children(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test selecting option for room notifies children."""
        select = ControlModeSelect(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            coordinator=mock_room_coordinator,
        )

        # Mock the async_write_ha_state method
        select.async_write_ha_state = MagicMock()

        await select.async_select_option(CONTROL_MODE_FORCE)

        assert select._attr_current_option == CONTROL_MODE_FORCE
        assert mock_room_coordinator.control_mode == CONTROL_MODE_FORCE
        mock_room_coordinator.async_refresh.assert_called_once()
        mock_room_coordinator.async_notify_children.assert_called_once()

    def test_set_control_mode_programmatic(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test set_control_mode method."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock async_write_ha_state
        select.async_write_ha_state = MagicMock()

        select.set_control_mode(CONTROL_MODE_DISABLED)

        assert select._attr_current_option == CONTROL_MODE_DISABLED
        select.async_write_ha_state.assert_called_once()

    def test_set_control_mode_invalid(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test set_control_mode with invalid mode doesn't change option."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock async_write_ha_state
        select.async_write_ha_state = MagicMock()

        select.set_control_mode("invalid_mode")

        # Should remain at AUTO since invalid mode is ignored
        assert select._attr_current_option == CONTROL_MODE_AUTO
        # async_write_ha_state should not be called for invalid mode
        select.async_write_ha_state.assert_not_called()

    def test_device_info_room(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test device info for room select."""
        select = ControlModeSelect(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            coordinator=mock_room_coordinator,
        )

        device_info = select._attr_device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "room_test_room_entry"
        assert device_info["name"] == "Room: Test Room"

    def test_device_info_standalone(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test device info for standalone select."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        device_info = select._attr_device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "test_cover_entry"
        assert device_info["name"] == "Test Cover"

    def test_device_info_with_via_device(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test device info with via_device for cover in room."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
            room_id="room_123",
        )

        device_info = select._attr_device_info
        assert "via_device" in device_info
        assert device_info["via_device"] == (DOMAIN, "room_room_123")


class TestSelectAsyncSetupEntry:
    """Tests for select async_setup_entry function."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        from custom_components.adaptive_cover.room_coordinator import RoomCoordinator

        coordinator = MagicMock(spec=RoomCoordinator)
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.async_notify_children = AsyncMock()
        # This will be called by ControlModeSelect.__init__
        coordinator.register_control_mode_select = MagicMock()
        coordinator.setup_midnight_reset = MagicMock()
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.register_control_mode_select = MagicMock()
        coordinator.setup_midnight_reset = MagicMock()
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
    def mock_cover_config_entry_with_entities(self) -> MagicMock:
        """Create mock ConfigEntry for standalone cover with entities."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {CONF_ENTITIES: ["cover.living_room"]}
        return entry

    @pytest.fixture
    def mock_cover_config_entry_no_entities(self) -> MagicMock:
        """Create mock ConfigEntry for standalone cover without entities."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {CONF_ENTITIES: []}
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
    async def test_setup_room_entry_creates_control_mode_select(
        self,
        hass,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates control mode select for room."""
        from custom_components.adaptive_cover.select import async_setup_entry

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        assert len(entities_added) == 1
        assert entities_added[0]._entry_type == EntryType.ROOM
        # register_control_mode_select is called in async_added_to_hass
        # which happens after the entity is added to HA

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_with_entities_creates_select(
        self,
        hass,
        mock_cover_config_entry_with_entities: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates control mode select for standalone with entities."""
        from custom_components.adaptive_cover.select import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_config_entry_with_entities.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(
            hass, mock_cover_config_entry_with_entities, add_entities
        )

        assert len(entities_added) == 1
        assert entities_added[0]._entry_type == EntryType.COVER
        # register_control_mode_select is called in async_added_to_hass
        # which happens after the entity is added to HA

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_no_entities_no_select(
        self,
        hass,
        mock_cover_config_entry_no_entities: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates no select for cover without entities."""
        from custom_components.adaptive_cover.select import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_config_entry_no_entities.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_config_entry_no_entities, add_entities)

        assert len(entities_added) == 0

    @pytest.mark.asyncio
    async def test_setup_cover_in_room_no_select(
        self,
        hass,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates no select for cover in room (room handles it)."""
        from custom_components.adaptive_cover.select import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        assert len(entities_added) == 0


class TestControlModeSelectAsyncAddedToHass:
    """Tests for ControlModeSelect async_added_to_hass method."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.control_mode = CONTROL_MODE_AUTO
        coordinator.async_refresh = AsyncMock()
        coordinator.register_control_mode_select = MagicMock()
        coordinator.setup_midnight_reset = MagicMock()
        return coordinator

    @pytest.fixture
    def mock_cover_config_entry(self) -> MagicMock:
        """Create mock ConfigEntry for cover."""
        entry = MagicMock()
        entry.entry_id = "test_cover_entry"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_async_added_to_hass_registers_with_coordinator(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass registers with coordinator."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock the async_get_last_state to return None
        select.async_get_last_state = AsyncMock(return_value=None)

        await select.async_added_to_hass()

        mock_cover_coordinator.register_control_mode_select.assert_called_once_with(
            select
        )
        mock_cover_coordinator.setup_midnight_reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_state(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass restores last known state."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock the async_get_last_state to return a state
        mock_state = MagicMock()
        mock_state.state = CONTROL_MODE_FORCE
        select.async_get_last_state = AsyncMock(return_value=mock_state)

        await select.async_added_to_hass()

        # Should restore to FORCE
        assert select._attr_current_option == CONTROL_MODE_FORCE
        assert mock_cover_coordinator.control_mode == CONTROL_MODE_FORCE

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_unavailable_to_auto(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass restores unavailable state to AUTO."""
        from homeassistant.const import STATE_UNAVAILABLE

        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock the async_get_last_state to return UNAVAILABLE
        mock_state = MagicMock()
        mock_state.state = STATE_UNAVAILABLE
        select.async_get_last_state = AsyncMock(return_value=mock_state)

        await select.async_added_to_hass()

        # Should default to AUTO
        assert select._attr_current_option == CONTROL_MODE_AUTO
        assert mock_cover_coordinator.control_mode == CONTROL_MODE_AUTO

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_invalid_to_auto(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test async_added_to_hass restores invalid state to AUTO."""
        select = ControlModeSelect(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        # Mock the async_get_last_state to return an invalid state
        mock_state = MagicMock()
        mock_state.state = "invalid_state"
        select.async_get_last_state = AsyncMock(return_value=mock_state)

        await select.async_added_to_hass()

        # Should default to AUTO
        assert select._attr_current_option == CONTROL_MODE_AUTO
        assert mock_cover_coordinator.control_mode == CONTROL_MODE_AUTO
