"""Tests for Adaptive Cover __init__.py module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.adaptive_cover import (
    ALL_PLATFORMS,
    COVER_IN_ROOM_PLATFORMS,
    ROOM_PLATFORMS,
    STANDALONE_COVER_PLATFORMS,
    async_setup_entry,
    async_unload_entry,
    _async_setup_room_entry,
    _async_setup_cover_entry,
    _async_update_listener,
)
from custom_components.adaptive_cover.const import (
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    DOMAIN,
    EntryType,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestPlatformConstants:
    """Tests for platform constants."""

    def test_room_platforms(self) -> None:
        """Test ROOM_PLATFORMS contains expected platforms."""
        from homeassistant.const import Platform

        assert Platform.SENSOR in ROOM_PLATFORMS
        assert Platform.SELECT in ROOM_PLATFORMS
        assert Platform.SWITCH in ROOM_PLATFORMS
        assert Platform.BINARY_SENSOR in ROOM_PLATFORMS
        assert Platform.BUTTON in ROOM_PLATFORMS
        assert len(ROOM_PLATFORMS) == 5

    def test_cover_in_room_platforms(self) -> None:
        """Test COVER_IN_ROOM_PLATFORMS contains expected platforms."""
        from homeassistant.const import Platform

        assert Platform.SENSOR in COVER_IN_ROOM_PLATFORMS
        assert Platform.BINARY_SENSOR in COVER_IN_ROOM_PLATFORMS
        assert Platform.BUTTON in COVER_IN_ROOM_PLATFORMS
        assert len(COVER_IN_ROOM_PLATFORMS) == 3

    def test_standalone_cover_platforms(self) -> None:
        """Test STANDALONE_COVER_PLATFORMS contains expected platforms."""
        from homeassistant.const import Platform

        assert Platform.SENSOR in STANDALONE_COVER_PLATFORMS
        assert Platform.SELECT in STANDALONE_COVER_PLATFORMS
        assert Platform.SWITCH in STANDALONE_COVER_PLATFORMS
        assert Platform.BINARY_SENSOR in STANDALONE_COVER_PLATFORMS
        assert Platform.BUTTON in STANDALONE_COVER_PLATFORMS
        assert len(STANDALONE_COVER_PLATFORMS) == 5

    def test_all_platforms(self) -> None:
        """Test ALL_PLATFORMS contains all platform types."""
        from homeassistant.const import Platform

        assert Platform.SENSOR in ALL_PLATFORMS
        assert Platform.SELECT in ALL_PLATFORMS
        assert Platform.SWITCH in ALL_PLATFORMS
        assert Platform.BINARY_SENSOR in ALL_PLATFORMS
        assert Platform.BUTTON in ALL_PLATFORMS
        assert len(ALL_PLATFORMS) == 5


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.fixture
    def mock_room_entry(self) -> MagicMock:
        """Create mock room config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.fixture
    def mock_cover_entry(self) -> MagicMock:
        """Create mock cover config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {CONF_ENTITIES: []}
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.mark.asyncio
    async def test_setup_entry_routes_to_room_setup(
        self, hass: HomeAssistant, mock_room_entry: MagicMock
    ) -> None:
        """Test async_setup_entry routes room entries correctly."""
        with patch(
            "custom_components.adaptive_cover._async_setup_room_entry",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_setup:
            result = await async_setup_entry(hass, mock_room_entry)

            mock_setup.assert_called_once_with(hass, mock_room_entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_setup_entry_routes_to_cover_setup(
        self, hass: HomeAssistant, mock_cover_entry: MagicMock
    ) -> None:
        """Test async_setup_entry routes cover entries correctly."""
        with patch(
            "custom_components.adaptive_cover._async_setup_cover_entry",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_setup:
            result = await async_setup_entry(hass, mock_cover_entry)

            mock_setup.assert_called_once_with(hass, mock_cover_entry)
            assert result is True


class TestAsyncSetupRoomEntry:
    """Tests for _async_setup_room_entry function."""

    @pytest.fixture
    def mock_room_entry(self) -> MagicMock:
        """Create mock room config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.mark.asyncio
    async def test_setup_room_entry_creates_coordinator(
        self, hass: HomeAssistant, mock_room_entry: MagicMock
    ) -> None:
        """Test _async_setup_room_entry creates RoomCoordinator."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.RoomCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.async_discover_existing_covers = AsyncMock()
            mock_coordinator.async_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ) as mock_track,
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ) as mock_forward,
                patch("custom_components.adaptive_cover.async_dispatcher_send"),
            ):
                mock_track.return_value = MagicMock()

                result = await _async_setup_room_entry(hass, mock_room_entry)

                assert result is True
                mock_coordinator_class.assert_called_once()
                mock_coordinator.async_config_entry_first_refresh.assert_called_once()
                mock_forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_room_entry_stores_coordinator(
        self, hass: HomeAssistant, mock_room_entry: MagicMock
    ) -> None:
        """Test _async_setup_room_entry stores coordinator in hass.data."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.RoomCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.async_discover_existing_covers = AsyncMock()
            mock_coordinator.async_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ),
                patch("custom_components.adaptive_cover.async_dispatcher_send"),
            ):
                await _async_setup_room_entry(hass, mock_room_entry)

                # Check coordinator is stored with both keys
                assert f"room_{mock_room_entry.entry_id}" in hass.data[DOMAIN]
                assert mock_room_entry.entry_id in hass.data[DOMAIN]


class TestAsyncSetupCoverEntry:
    """Tests for _async_setup_cover_entry function."""

    @pytest.fixture
    def mock_cover_entry(self) -> MagicMock:
        """Create mock cover config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {CONF_ENTITIES: ["cover.test"]}
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.fixture
    def mock_cover_entry_with_room(self) -> MagicMock:
        """Create mock cover config entry that belongs to a room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_456"
        entry.data = {
            "name": "Test Cover in Room",
            CONF_ENTRY_TYPE: EntryType.COVER,
            CONF_ROOM_ID: "test_room_123",
        }
        entry.options = {CONF_ENTITIES: ["cover.test"]}
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.mark.asyncio
    async def test_setup_standalone_cover_entry(
        self, hass: HomeAssistant, mock_cover_entry: MagicMock
    ) -> None:
        """Test _async_setup_cover_entry for standalone cover."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.AdaptiveDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ) as mock_forward,
            ):
                result = await _async_setup_cover_entry(hass, mock_cover_entry)

                assert result is True
                mock_coordinator_class.assert_called_once()
                # Should forward to STANDALONE_COVER_PLATFORMS
                mock_forward.assert_called_once_with(
                    mock_cover_entry, STANDALONE_COVER_PLATFORMS
                )

    @pytest.mark.asyncio
    async def test_setup_cover_entry_with_room_loaded(
        self, hass: HomeAssistant, mock_cover_entry_with_room: MagicMock
    ) -> None:
        """Test _async_setup_cover_entry when room is already loaded."""
        hass.data.setdefault(DOMAIN, {})

        # Set up existing room coordinator
        mock_room_coordinator = MagicMock()
        mock_room_coordinator.config_entry.options = {}
        mock_room_coordinator.register_cover = MagicMock()
        mock_room_coordinator.async_refresh = AsyncMock()
        hass.data[DOMAIN]["room_test_room_123"] = mock_room_coordinator

        with patch(
            "custom_components.adaptive_cover.AdaptiveDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ) as mock_forward,
            ):
                result = await _async_setup_cover_entry(
                    hass, mock_cover_entry_with_room
                )

                assert result is True
                # Should pass room coordinator to cover coordinator
                mock_coordinator_class.assert_called_once()
                call_args = mock_coordinator_class.call_args
                assert call_args[0][2] == mock_room_coordinator
                # Should register with room
                mock_room_coordinator.register_cover.assert_called_once()
                # Should forward to COVER_IN_ROOM_PLATFORMS
                mock_forward.assert_called_once_with(
                    mock_cover_entry_with_room, COVER_IN_ROOM_PLATFORMS
                )

    @pytest.mark.asyncio
    async def test_setup_cover_entry_room_not_loaded_waits_with_timeout(
        self, hass: HomeAssistant, mock_cover_entry_with_room: MagicMock
    ) -> None:
        """Test _async_setup_cover_entry waits for room with timeout."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.AdaptiveDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ) as mock_forward,
                patch(
                    "custom_components.adaptive_cover._async_wait_for_room",
                    new_callable=AsyncMock,
                    return_value=None,  # Simulate timeout
                ),
            ):
                result = await _async_setup_cover_entry(
                    hass, mock_cover_entry_with_room
                )

                assert result is True
                # Should fall back to standalone mode with STANDALONE_COVER_PLATFORMS
                mock_forward.assert_called_once_with(
                    mock_cover_entry_with_room, STANDALONE_COVER_PLATFORMS
                )

    @pytest.mark.asyncio
    async def test_setup_cover_entry_stores_coordinator(
        self, hass: HomeAssistant, mock_cover_entry: MagicMock
    ) -> None:
        """Test _async_setup_cover_entry stores coordinator in hass.data."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.AdaptiveDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ),
            ):
                await _async_setup_cover_entry(hass, mock_cover_entry)

                assert mock_cover_entry.entry_id in hass.data[DOMAIN]
                assert hass.data[DOMAIN][mock_cover_entry.entry_id] == mock_coordinator


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    @pytest.fixture
    def mock_room_entry(self) -> MagicMock:
        """Create mock room config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        entry.runtime_data = None
        return entry

    @pytest.fixture
    def mock_cover_entry(self) -> MagicMock:
        """Create mock cover config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {}
        entry.runtime_data = None
        return entry

    @pytest.fixture
    def mock_cover_entry_with_room(self) -> MagicMock:
        """Create mock cover config entry with room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_456"
        entry.data = {
            "name": "Test Cover in Room",
            CONF_ENTRY_TYPE: EntryType.COVER,
            CONF_ROOM_ID: "test_room_123",
        }
        entry.options = {}
        entry.runtime_data = None
        return entry

    @pytest.mark.asyncio
    async def test_unload_room_entry(
        self, hass: HomeAssistant, mock_room_entry: MagicMock
    ) -> None:
        """Test async_unload_entry for room entry."""
        hass.data[DOMAIN] = {
            mock_room_entry.entry_id: MagicMock(),
            f"room_{mock_room_entry.entry_id}": MagicMock(),
        }

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_room_entry)

            assert result is True
            mock_unload.assert_called_once_with(mock_room_entry, ROOM_PLATFORMS)
            # Should remove both keys
            assert mock_room_entry.entry_id not in hass.data[DOMAIN]
            assert f"room_{mock_room_entry.entry_id}" not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_standalone_cover_entry(
        self, hass: HomeAssistant, mock_cover_entry: MagicMock
    ) -> None:
        """Test async_unload_entry for standalone cover entry."""
        hass.data[DOMAIN] = {mock_cover_entry.entry_id: MagicMock()}

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_cover_entry)

            assert result is True
            mock_unload.assert_called_once_with(
                mock_cover_entry, STANDALONE_COVER_PLATFORMS
            )
            assert mock_cover_entry.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_cover_entry_with_room(
        self, hass: HomeAssistant, mock_cover_entry_with_room: MagicMock
    ) -> None:
        """Test async_unload_entry for cover entry belonging to room."""
        mock_cover_coordinator = MagicMock()
        mock_room_coordinator = MagicMock()
        hass.data[DOMAIN] = {
            mock_cover_entry_with_room.entry_id: mock_cover_coordinator,
            "room_test_room_123": mock_room_coordinator,
        }

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_cover_entry_with_room)

            assert result is True
            mock_unload.assert_called_once_with(
                mock_cover_entry_with_room, COVER_IN_ROOM_PLATFORMS
            )
            # Should unregister from room
            mock_room_coordinator.unregister_cover.assert_called_once_with(
                mock_cover_coordinator
            )
            assert mock_cover_entry_with_room.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_entry_failure(
        self, hass: HomeAssistant, mock_cover_entry: MagicMock
    ) -> None:
        """Test async_unload_entry returns False on failure."""
        hass.data[DOMAIN] = {mock_cover_entry.entry_id: MagicMock()}

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_cover_entry)

            assert result is False
            mock_unload.assert_called_once()
            # Should NOT remove from hass.data on failure
            assert mock_cover_entry.entry_id in hass.data[DOMAIN]


class TestAsyncUpdateListener:
    """Tests for _async_update_listener function."""

    @pytest.fixture
    def mock_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {"name": "Test Entry"}
        entry.options = {}
        entry.runtime_data = None
        return entry

    @pytest.mark.asyncio
    async def test_update_listener_reloads_entry(
        self, hass: HomeAssistant, mock_entry: MagicMock
    ) -> None:
        """Test _async_update_listener reloads the entry."""
        mock_coordinator = MagicMock()
        mock_coordinator.room_coordinator = None
        hass.data[DOMAIN] = {mock_entry.entry_id: mock_coordinator}

        with patch.object(
            hass.config_entries,
            "async_reload",
            new_callable=AsyncMock,
        ) as mock_reload:
            await _async_update_listener(hass, mock_entry)

            mock_reload.assert_called_once_with(mock_entry.entry_id)

    @pytest.mark.asyncio
    async def test_update_listener_captures_old_room_id(
        self, hass: HomeAssistant, mock_entry: MagicMock
    ) -> None:
        """Test _async_update_listener captures old room_id for unload."""
        mock_room_coordinator = MagicMock()
        mock_room_coordinator.config_entry.entry_id = "old_room_123"

        mock_coordinator = MagicMock()
        mock_coordinator.room_coordinator = mock_room_coordinator

        hass.data[DOMAIN] = {mock_entry.entry_id: mock_coordinator}

        with patch.object(
            hass.config_entries,
            "async_reload",
            new_callable=AsyncMock,
        ):
            await _async_update_listener(hass, mock_entry)

            # Should store old room_id in runtime_data
            assert mock_entry.runtime_data == {"_old_room_id": "old_room_123"}


class TestAsyncInitializeIntegration:
    """Tests for async_initialize_integration function."""

    @pytest.mark.asyncio
    async def test_initialize_integration_returns_true(
        self, hass: HomeAssistant
    ) -> None:
        """Test async_initialize_integration returns True."""
        from custom_components.adaptive_cover import async_initialize_integration

        result = await async_initialize_integration(hass)
        assert result is True

    @pytest.mark.asyncio
    async def test_initialize_integration_with_config_entry(
        self, hass: HomeAssistant
    ) -> None:
        """Test async_initialize_integration with config_entry parameter."""
        from custom_components.adaptive_cover import async_initialize_integration

        mock_entry = MagicMock()
        result = await async_initialize_integration(hass, config_entry=mock_entry)
        assert result is True


class TestRoomSignalDispatch:
    """Tests for room signal dispatch and cover discovery."""

    @pytest.fixture
    def mock_room_entry(self) -> MagicMock:
        """Create mock room config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {}
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.mark.asyncio
    async def test_room_fires_signal_after_setup(
        self, hass: HomeAssistant, mock_room_entry: MagicMock
    ) -> None:
        """Test room fires SIGNAL_ROOM_LOADED after setup completes."""
        from custom_components.adaptive_cover.const import SIGNAL_ROOM_LOADED

        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.RoomCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.async_discover_existing_covers = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ),
                patch(
                    "custom_components.adaptive_cover.async_dispatcher_send"
                ) as mock_dispatcher,
            ):
                await _async_setup_room_entry(hass, mock_room_entry)

                # Should fire room loaded signal
                mock_dispatcher.assert_called_once_with(
                    hass, f"{SIGNAL_ROOM_LOADED}_{mock_room_entry.entry_id}"
                )

    @pytest.mark.asyncio
    async def test_room_discovers_existing_covers_on_reload(
        self, hass: HomeAssistant, mock_room_entry: MagicMock
    ) -> None:
        """Test room discovers existing covers on reload."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.RoomCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.async_discover_existing_covers = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event"
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ),
                patch("custom_components.adaptive_cover.async_dispatcher_send"),
            ):
                await _async_setup_room_entry(hass, mock_room_entry)

                # Should call async_discover_existing_covers
                mock_coordinator.async_discover_existing_covers.assert_called_once()


class TestCoverUnloadWithOldRoomId:
    """Tests for cover unload with old room_id from runtime_data."""

    @pytest.fixture
    def mock_cover_entry_moved_from_room(self) -> MagicMock:
        """Create mock cover entry that was moved out of a room."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {
            "name": "Test Cover",
            CONF_ENTRY_TYPE: EntryType.COVER,
            # No CONF_ROOM_ID in current data
        }
        entry.options = {}
        # Has old room_id from before move
        entry.runtime_data = {"_old_room_id": "old_room_456"}
        return entry

    @pytest.mark.asyncio
    async def test_unload_cover_uses_old_room_id(
        self, hass: HomeAssistant, mock_cover_entry_moved_from_room: MagicMock
    ) -> None:
        """Test unload uses old_room_id from runtime_data."""
        mock_cover_coordinator = MagicMock()
        mock_room_coordinator = MagicMock()
        hass.data[DOMAIN] = {
            mock_cover_entry_moved_from_room.entry_id: mock_cover_coordinator,
            "room_old_room_456": mock_room_coordinator,
        }

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_cover_entry_moved_from_room)

            assert result is True
            # Should use COVER_IN_ROOM_PLATFORMS based on old_room_id
            mock_unload.assert_called_once_with(
                mock_cover_entry_moved_from_room, COVER_IN_ROOM_PLATFORMS
            )
            # Should unregister from old room
            mock_room_coordinator.unregister_cover.assert_called_once_with(
                mock_cover_coordinator
            )


class TestEntityTracking:
    """Tests for entity tracking setup."""

    @pytest.fixture
    def mock_room_entry_with_entities(self) -> MagicMock:
        """Create mock room config entry with optional entities."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Test Room", CONF_ENTRY_TYPE: EntryType.ROOM}
        entry.options = {
            "temp_entity": "sensor.temperature",
            "presence_entity": "binary_sensor.motion",
            "weather_entity": "weather.home",
        }
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.mark.asyncio
    async def test_room_entry_tracks_optional_entities(
        self, hass: HomeAssistant, mock_room_entry_with_entities: MagicMock
    ) -> None:
        """Test room entry tracks optional entities configured in options."""

        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.RoomCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.async_discover_existing_covers = AsyncMock()
            mock_coordinator.async_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            tracked_entities = []

            def capture_track_call(hass, entities, callback):
                tracked_entities.extend(entities)
                return MagicMock()

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event",
                    side_effect=capture_track_call,
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ),
                patch("custom_components.adaptive_cover.async_dispatcher_send"),
            ):
                await _async_setup_room_entry(hass, mock_room_entry_with_entities)

                # Should track sun.sun plus all configured entities
                assert "sun.sun" in tracked_entities
                assert "sensor.temperature" in tracked_entities
                assert "binary_sensor.motion" in tracked_entities
                assert "weather.home" in tracked_entities

    @pytest.fixture
    def mock_cover_entry_with_optional_entities(self) -> MagicMock:
        """Create mock cover config entry with optional entities."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", CONF_ENTRY_TYPE: EntryType.COVER}
        entry.options = {
            CONF_ENTITIES: ["cover.living_room"],
            "temp_entity": "sensor.temp",
            "presence_entity": "binary_sensor.presence",
        }
        entry.async_on_unload = MagicMock()
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        return entry

    @pytest.mark.asyncio
    async def test_cover_entry_tracks_optional_entities(
        self, hass: HomeAssistant, mock_cover_entry_with_optional_entities: MagicMock
    ) -> None:
        """Test cover entry tracks optional entities for standalone covers."""
        hass.data.setdefault(DOMAIN, {})

        with patch(
            "custom_components.adaptive_cover.AdaptiveDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            tracked_entities_calls = []

            def capture_track_call(hass, entities, callback):
                tracked_entities_calls.append(list(entities))
                return MagicMock()

            with (
                patch(
                    "custom_components.adaptive_cover.async_track_state_change_event",
                    side_effect=capture_track_call,
                ),
                patch.object(
                    hass.config_entries,
                    "async_forward_entry_setups",
                    new_callable=AsyncMock,
                ),
            ):
                await _async_setup_cover_entry(
                    hass, mock_cover_entry_with_optional_entities
                )

                # Should have two track calls: one for state entities, one for cover entities
                assert len(tracked_entities_calls) == 2
                # First call should include sun.sun and optional entities
                state_entities = tracked_entities_calls[0]
                assert "sun.sun" in state_entities
                assert "sensor.temp" in state_entities
                assert "binary_sensor.presence" in state_entities
                # Second call should include cover entities
                cover_entities = tracked_entities_calls[1]
                assert "cover.living_room" in cover_entities
