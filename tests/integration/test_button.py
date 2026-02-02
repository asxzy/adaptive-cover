"""Tests for button module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.adaptive_cover.button import ForceUpdateButton
from custom_components.adaptive_cover.const import (
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    DOMAIN,
    EntryType,
)

if TYPE_CHECKING:
    pass


class TestForceUpdateButton:
    """Tests for ForceUpdateButton."""

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.async_force_update_covers = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.async_force_update_covers = AsyncMock()
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
        button = ForceUpdateButton(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        assert button._name == "Test Room"
        assert button._attr_unique_id == "test_room_entry_force_update"
        assert button._is_room is True
        assert button._attr_icon == "mdi:refresh"
        assert "room_" in str(button._attr_device_info["identifiers"])

    def test_init_standalone(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test initialization for standalone cover."""
        button = ForceUpdateButton(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
            is_room=False,
        )

        assert button._name == "Test Cover"
        assert button._attr_unique_id == "test_cover_entry_force_update"
        assert button._is_room is False
        assert button._attr_name == "Force Update"
        # Device info should not have room_ prefix
        identifiers = list(button._attr_device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "test_cover_entry"

    @pytest.mark.asyncio
    async def test_async_press_calls_force_update(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test pressing button calls async_force_update_covers."""
        button = ForceUpdateButton(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        await button.async_press()

        mock_cover_coordinator.async_force_update_covers.assert_called_once()
        mock_cover_coordinator.logger.info.assert_called_with(
            "Force update button pressed"
        )

    @pytest.mark.asyncio
    async def test_async_press_room_calls_force_update(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test pressing button for room calls async_force_update_covers."""
        button = ForceUpdateButton(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        await button.async_press()

        mock_room_coordinator.async_force_update_covers.assert_called_once()

    def test_device_info_room(
        self, mock_room_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> None:
        """Test device info for room button."""
        button = ForceUpdateButton(
            config_entry=mock_room_config_entry,
            unique_id=mock_room_config_entry.entry_id,
            coordinator=mock_room_coordinator,
            is_room=True,
        )

        device_info = button._attr_device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "room_test_room_entry"
        assert device_info["name"] == "Room: Test Room"

    def test_device_info_standalone(
        self, mock_cover_config_entry: MagicMock, mock_cover_coordinator: MagicMock
    ) -> None:
        """Test device info for standalone button."""
        button = ForceUpdateButton(
            config_entry=mock_cover_config_entry,
            unique_id=mock_cover_config_entry.entry_id,
            coordinator=mock_cover_coordinator,
        )

        device_info = button._attr_device_info
        identifiers = list(device_info["identifiers"])[0]
        assert identifiers[0] == DOMAIN
        assert identifiers[1] == "test_cover_entry"
        assert device_info["name"] == "Test Cover"


class TestButtonAsyncSetupEntry:
    """Tests for button async_setup_entry function."""

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock RoomCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.async_force_update_covers = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_cover_coordinator(self) -> MagicMock:
        """Create mock AdaptiveDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.logger = MagicMock()
        coordinator.async_force_update_covers = AsyncMock()
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
    async def test_setup_room_entry_creates_force_update_button(
        self,
        hass,
        mock_room_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates force update button for room."""
        from custom_components.adaptive_cover.button import async_setup_entry

        hass.data[DOMAIN] = {mock_room_config_entry.entry_id: mock_room_coordinator}

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_room_config_entry, add_entities)

        assert len(entities_added) == 1
        assert entities_added[0]._is_room is True
        assert "force_update" in entities_added[0]._attr_unique_id

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_with_entities_creates_button(
        self,
        hass,
        mock_cover_config_entry_with_entities: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates button for standalone cover with entities."""
        from custom_components.adaptive_cover.button import async_setup_entry

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
        assert entities_added[0]._is_room is False

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_no_entities_no_button(
        self,
        hass,
        mock_cover_config_entry_no_entities: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates no button for cover without entities."""
        from custom_components.adaptive_cover.button import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_config_entry_no_entities.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_config_entry_no_entities, add_entities)

        assert len(entities_added) == 0

    @pytest.mark.asyncio
    async def test_setup_cover_in_room_no_button(
        self,
        hass,
        mock_cover_in_room_config_entry: MagicMock,
        mock_cover_coordinator: MagicMock,
    ) -> None:
        """Test async_setup_entry creates no button for cover in room (room handles it)."""
        from custom_components.adaptive_cover.button import async_setup_entry

        hass.data[DOMAIN] = {
            mock_cover_in_room_config_entry.entry_id: mock_cover_coordinator
        }

        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_cover_in_room_config_entry, add_entities)

        assert len(entities_added) == 0
