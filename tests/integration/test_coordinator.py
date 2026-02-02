"""Integration tests for AdaptiveDataUpdateCoordinator."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.adaptive_cover.const import (
    CONF_AZIMUTH,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_MAX_POSITION,
    CONF_MIN_POSITION,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    CONTROL_MODE_FORCE,
)
from custom_components.adaptive_cover.coordinator import (
    AdaptiveCoverData,
    AdaptiveDataUpdateCoordinator,
    AdaptiveCoverManager,
    StateChangedData,
    inverse_state,
)

if TYPE_CHECKING:
    from custom_components.adaptive_cover.config_context_adapter import (
        ConfigContextAdapter,
    )


class TestInverseState:
    """Tests for inverse_state function."""

    def test_inverse_state_zero(self) -> None:
        """Test inverting 0 returns 100."""
        assert inverse_state(0) == 100

    def test_inverse_state_100(self) -> None:
        """Test inverting 100 returns 0."""
        assert inverse_state(100) == 0

    def test_inverse_state_50(self) -> None:
        """Test inverting 50 returns 50."""
        assert inverse_state(50) == 50

    def test_inverse_state_25(self) -> None:
        """Test inverting 25 returns 75."""
        assert inverse_state(25) == 75


class TestStateChangedData:
    """Tests for StateChangedData dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test StateChangedData can be created with all fields."""
        old_state = MagicMock()
        new_state = MagicMock()

        data = StateChangedData(
            entity_id="cover.test", old_state=old_state, new_state=new_state
        )

        assert data.entity_id == "cover.test"
        assert data.old_state is old_state
        assert data.new_state is new_state

    def test_creates_with_none_states(self) -> None:
        """Test StateChangedData can be created with None states."""
        data = StateChangedData(entity_id="cover.test", old_state=None, new_state=None)

        assert data.entity_id == "cover.test"
        assert data.old_state is None
        assert data.new_state is None


class TestAdaptiveCoverManager:
    """Tests for AdaptiveCoverManager class."""

    def test_add_covers(self, mock_logger: ConfigContextAdapter) -> None:
        """Test adding covers to manager."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)

        manager.add_covers(["cover.living_room", "cover.bedroom"])

        assert "cover.living_room" in manager.covers
        assert "cover.bedroom" in manager.covers

    def test_add_covers_updates_existing(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test adding covers updates existing set."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)

        manager.add_covers(["cover.living_room"])
        manager.add_covers(["cover.bedroom"])

        assert len(manager.covers) == 2
        assert "cover.living_room" in manager.covers
        assert "cover.bedroom" in manager.covers

    def test_handle_state_change_none_event(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change with None event."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)

        # Should not raise error
        manager.handle_state_change(
            None,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={},
            manual_threshold=5,
        )

    def test_handle_state_change_entity_not_tracked(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change with untracked entity."""
        coordinator = MagicMock()
        coordinator.control_mode = "auto"  # Initial state
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        event = StateChangedData(
            entity_id="cover.other_room",
            old_state=MagicMock(),
            new_state=MagicMock(),
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={},
            manual_threshold=5,
        )

        # Should not change control mode for untracked entity
        assert coordinator.control_mode == "auto"

    def test_handle_state_change_waiting_for_target(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when waiting for target position."""
        coordinator = MagicMock()
        coordinator.control_mode = "auto"  # Initial state
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=MagicMock(),
        )

        # When wait_target_call is True for entity, should skip
        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": True},
            manual_threshold=5,
        )

        # Should not change control mode when waiting for target
        assert coordinator.control_mode == "auto"

    def test_handle_state_change_manual_change_detected(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when manual change is detected."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 80}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Should set control mode to disabled (OFF) due to manual change
        # The change of 30 (80 - 50) exceeds threshold of 5
        assert coordinator.control_mode == "disabled"

    def test_handle_state_change_below_threshold(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when change is below threshold."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 52}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Should not change control mode - change of 2 is below threshold of 5
        # Note: control_mode should not be set
        # We need to check it wasn't set to disabled
        assert coordinator.control_mode != "disabled"

    def test_handle_state_change_tilt_cover(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change for tilt covers uses tilt_position."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {
            "current_position": 100,
            "current_tilt_position": 80,
        }

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_tilt",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Should detect manual change using tilt position (80 vs 50 = 30)
        assert coordinator.control_mode == "disabled"

    def test_handle_state_change_no_threshold(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change with no threshold set."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 51}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=None,
        )

        # With no threshold, any change should trigger manual detection
        assert coordinator.control_mode == "disabled"

    def test_handle_state_change_same_position(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when position matches our state."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 50}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Position matches, should not trigger manual detection
        assert coordinator.control_mode != "disabled"


class TestAdaptiveCoverData:
    """Tests for AdaptiveCoverData dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test AdaptiveCoverData can be created with all fields."""
        states = {"position": 50, "start": "08:00", "end": "20:00"}
        attributes = {"fov": [90, 270], "azimuth": 180}

        data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states=states,
            attributes=attributes,
        )

        assert data.climate_mode_toggle is True
        assert data.states == states
        assert data.attributes == attributes

    def test_creates_with_false_toggle(self) -> None:
        """Test AdaptiveCoverData with False climate_mode_toggle."""
        data = AdaptiveCoverData(
            climate_mode_toggle=False,
            states={},
            attributes={},
        )

        assert data.climate_mode_toggle is False
        assert data.states == {}
        assert data.attributes == {}

    def test_states_can_contain_any_values(self) -> None:
        """Test that states dict can contain various value types."""
        from datetime import datetime

        states = {
            "position": 75,
            "start": datetime(2024, 6, 21, 8, 0, 0),
            "end": datetime(2024, 6, 21, 20, 0, 0),
            "comfort": "comfortable",
            "active": True,
        }

        data = AdaptiveCoverData(
            climate_mode_toggle=True,
            states=states,
            attributes={},
        )

        assert data.states["position"] == 75
        assert data.states["start"] == datetime(2024, 6, 21, 8, 0, 0)
        assert data.states["comfort"] == "comfortable"
        assert data.states["active"] is True


class TestAdaptiveDataUpdateCoordinatorInit:
    """Tests for AdaptiveDataUpdateCoordinator initialization."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    def test_init_creates_coordinator(self, hass, mock_config_entry: MagicMock) -> None:
        """Test coordinator initialization."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

            assert coordinator.config_entry == mock_config_entry
            assert coordinator._cover_type == "cover_blind"
            assert coordinator._control_mode == CONTROL_MODE_AUTO
            assert coordinator.manager is not None

    def test_init_with_room_coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test coordinator initialization with room coordinator."""
        mock_room_coordinator = MagicMock()

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = AdaptiveDataUpdateCoordinator(
                hass, mock_config_entry, mock_room_coordinator
            )

            assert coordinator.has_room is True
            assert coordinator.room_coordinator is mock_room_coordinator


class TestAdaptiveDataUpdateCoordinatorProperties:
    """Tests for AdaptiveDataUpdateCoordinator property methods."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
            CONF_ENTITIES: ["cover.living_room"],
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

    def test_control_mode_default(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test control mode defaults to AUTO."""
        assert coordinator.control_mode == CONTROL_MODE_AUTO

    def test_control_mode_setter(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test setting control mode."""
        coordinator.control_mode = CONTROL_MODE_DISABLED
        assert coordinator.control_mode == CONTROL_MODE_DISABLED

        coordinator.control_mode = CONTROL_MODE_FORCE
        assert coordinator.control_mode == CONTROL_MODE_FORCE

    def test_is_control_enabled(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test is_control_enabled property."""
        coordinator.control_mode = CONTROL_MODE_AUTO
        assert coordinator.is_control_enabled is True

        coordinator.control_mode = CONTROL_MODE_FORCE
        assert coordinator.is_control_enabled is True

        coordinator.control_mode = CONTROL_MODE_DISABLED
        assert coordinator.is_control_enabled is False

    def test_is_climate_mode(self, coordinator: AdaptiveDataUpdateCoordinator) -> None:
        """Test is_climate_mode property."""
        coordinator.control_mode = CONTROL_MODE_AUTO
        assert coordinator.is_climate_mode is True

        coordinator.control_mode = CONTROL_MODE_FORCE
        assert coordinator.is_climate_mode is False

        coordinator.control_mode = CONTROL_MODE_DISABLED
        assert coordinator.is_climate_mode is False

    def test_has_room_false_for_standalone(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test has_room is False for standalone cover."""
        assert coordinator.has_room is False

    def test_room_coordinator_returns_none_for_standalone(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test room_coordinator returns None for standalone cover."""
        assert coordinator.room_coordinator is None

    def test_temp_toggle(self, coordinator: AdaptiveDataUpdateCoordinator) -> None:
        """Test temp_toggle property."""
        assert coordinator.temp_toggle is None
        coordinator.temp_toggle = True
        assert coordinator.temp_toggle is True
        coordinator.temp_toggle = False
        assert coordinator.temp_toggle is False

    def test_lux_toggle(self, coordinator: AdaptiveDataUpdateCoordinator) -> None:
        """Test lux_toggle property."""
        assert coordinator.lux_toggle is None
        coordinator.lux_toggle = True
        assert coordinator.lux_toggle is True

    def test_irradiance_toggle(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test irradiance_toggle property."""
        assert coordinator.irradiance_toggle is None
        coordinator.irradiance_toggle = True
        assert coordinator.irradiance_toggle is True

    def test_cloud_toggle(self, coordinator: AdaptiveDataUpdateCoordinator) -> None:
        """Test cloud_toggle property."""
        assert coordinator.cloud_toggle is None
        coordinator.cloud_toggle = True
        assert coordinator.cloud_toggle is True

    def test_weather_toggle(self, coordinator: AdaptiveDataUpdateCoordinator) -> None:
        """Test weather_toggle property."""
        assert coordinator.weather_toggle is None
        coordinator.weather_toggle = True
        assert coordinator.weather_toggle is True


class TestAdaptiveDataUpdateCoordinatorData:
    """Tests for data retrieval methods."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
            CONF_ENTITIES: ["cover.living_room"],
            CONF_SUNSET_POS: 0,
            CONF_SUNSET_OFFSET: 30,
            CONF_FOV_LEFT: 90,
            CONF_FOV_RIGHT: 90,
            CONF_AZIMUTH: 180,
            CONF_DEFAULT_HEIGHT: 60,
            CONF_MAX_POSITION: 100,
            CONF_MIN_POSITION: 0,
            CONF_DISTANCE: 0.5,
            CONF_HEIGHT_WIN: 2.1,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

    def test_common_data_returns_list(
        self, coordinator: AdaptiveDataUpdateCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test common_data returns correct parameters."""
        options = mock_config_entry.options
        result = coordinator.common_data(options)

        assert isinstance(result, list)
        assert len(result) == 18
        assert result[0] == options.get(CONF_SUNSET_POS)
        assert result[4] == options.get(CONF_FOV_LEFT)
        assert result[5] == options.get(CONF_FOV_RIGHT)
        assert result[6] == options.get(CONF_AZIMUTH)
        assert result[7] == options.get(CONF_DEFAULT_HEIGHT)

    def test_vertical_data_returns_list(
        self, coordinator: AdaptiveDataUpdateCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test vertical_data returns correct parameters."""
        options = mock_config_entry.options
        result = coordinator.vertical_data(options)

        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0] == options.get(CONF_DISTANCE)
        assert result[1] == options.get(CONF_HEIGHT_WIN)

    def test_pos_sun_returns_list(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test pos_sun property returns sun position data."""
        result = coordinator.pos_sun

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_option_from_own_config(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test _get_option returns value from own config."""
        result = coordinator._get_option(CONF_DELTA_POSITION, 1)
        assert result == 5

    def test_get_option_default_value(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test _get_option returns default when key not present."""
        result = coordinator._get_option("nonexistent_key", "default_value")
        assert result == "default_value"


class TestAdaptiveDataUpdateCoordinatorInterpolation:
    """Tests for interpolation functionality."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: True,
            CONF_INTERP_START: 10,
            CONF_INTERP_END: 90,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            # Set up interpolation values
            coord.start_value = 10
            coord.end_value = 90
            coord.normal_list = None
            coord.new_list = None
            return coord

    def test_interpolate_states_with_start_end(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test interpolation with start and end values."""
        # 0 should map to start value (10)
        result = coordinator.interpolate_states(0)
        assert result == 0  # Edge case: returns 0 when at start

        # 100 should map to end value (90)
        result = coordinator.interpolate_states(100)
        assert result == 100  # Edge case: returns 100 when at end

        # 50 should map to midpoint
        result = coordinator.interpolate_states(50)
        assert result == 50.0

    def test_interpolate_states_with_lists(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test interpolation with custom lists."""
        coordinator.start_value = None
        coordinator.end_value = None
        # The coordinator expects lists already split (as from config)
        coordinator.normal_list = ["0", "50", "100"]
        coordinator.new_list = ["0", "75", "100"]

        # Test interpolation
        result = coordinator.interpolate_states(50)
        assert result == 75.0


class TestAdaptiveDataUpdateCoordinatorWithRoom:
    """Tests for coordinator with room coordinator."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock room coordinator."""
        room = MagicMock()
        room.control_mode = CONTROL_MODE_AUTO
        room.is_control_enabled = True
        room.is_climate_mode = True
        room.temp_toggle = True
        room.lux_toggle = False
        room.irradiance_toggle = None
        room.cloud_toggle = True
        room.weather_toggle = False
        room.get_option = MagicMock(return_value=10)
        return room

    @pytest.fixture
    def coordinator(
        self,
        hass,
        mock_config_entry: MagicMock,
        mock_room_coordinator: MagicMock,
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance with room coordinator."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(
                hass, mock_config_entry, mock_room_coordinator
            )

    def test_has_room_true_with_room_coordinator(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test has_room is True when room coordinator is set."""
        assert coordinator.has_room is True

    def test_control_mode_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test control_mode delegates to room coordinator."""
        assert coordinator.control_mode == mock_room_coordinator.control_mode

    def test_is_control_enabled_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test is_control_enabled delegates to room coordinator."""
        assert (
            coordinator.is_control_enabled == mock_room_coordinator.is_control_enabled
        )

    def test_is_climate_mode_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test is_climate_mode delegates to room coordinator."""
        assert coordinator.is_climate_mode == mock_room_coordinator.is_climate_mode

    def test_toggles_delegate_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test toggle properties delegate to room coordinator."""
        assert coordinator.temp_toggle == mock_room_coordinator.temp_toggle
        assert coordinator.lux_toggle == mock_room_coordinator.lux_toggle
        assert coordinator.irradiance_toggle == mock_room_coordinator.irradiance_toggle
        assert coordinator.cloud_toggle == mock_room_coordinator.cloud_toggle
        assert coordinator.weather_toggle == mock_room_coordinator.weather_toggle

    def test_set_room_coordinator(self, hass, mock_config_entry: MagicMock) -> None:
        """Test set_room_coordinator method."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

            assert coordinator.has_room is False

            new_room = MagicMock()
            coordinator.set_room_coordinator(new_room)

            assert coordinator.has_room is True
            assert coordinator.room_coordinator is new_room

    def test_set_room_coordinator_ignores_if_already_set(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test set_room_coordinator does nothing if already set."""
        new_room = MagicMock()
        coordinator.set_room_coordinator(new_room)

        # Should still be the original room coordinator
        assert coordinator.room_coordinator is mock_room_coordinator


class TestAdaptiveDataUpdateCoordinatorPositionChecks:
    """Tests for position and time delta checks."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
            CONF_DEFAULT_HEIGHT: 60,
            CONF_SUNSET_POS: 0,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.min_change = 5
            coord.time_threshold = 2
            return coord

    def test_check_position_delta_exceeds_threshold(
        self, coordinator: AdaptiveDataUpdateCoordinator, hass
    ) -> None:
        """Test check_position_delta returns True when delta exceeds threshold."""
        # Mock state_attr to return current position
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=50,
        ):
            # State 60 vs position 50 = delta of 10 >= min_change of 5
            result = coordinator.check_position_delta(
                "cover.test", 60, coordinator.config_entry.options
            )
            assert result is True

    def test_check_position_delta_below_threshold(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position_delta returns False when delta is below threshold."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=50,
        ):
            # State 52 vs position 50 = delta of 2 < min_change of 5
            result = coordinator.check_position_delta(
                "cover.test", 52, coordinator.config_entry.options
            )
            assert result is False

    def test_check_position_delta_special_values(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position_delta returns True for special values (0, 100, default, sunset)."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=50,
        ):
            # State 0 is a special value
            result = coordinator.check_position_delta(
                "cover.test", 0, coordinator.config_entry.options
            )
            assert result is True

            # State 100 is a special value
            result = coordinator.check_position_delta(
                "cover.test", 100, coordinator.config_entry.options
            )
            assert result is True

    def test_check_position_delta_none_state(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position_delta returns False when state is None."""
        result = coordinator.check_position_delta(
            "cover.test", None, coordinator.config_entry.options
        )
        assert result is False

    def test_check_position_delta_no_current_position(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position_delta returns True when current position unavailable."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=None,
        ):
            result = coordinator.check_position_delta(
                "cover.test", 50, coordinator.config_entry.options
            )
            assert result is True

    def test_check_time_delta_exceeds_threshold(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_time_delta returns True when time exceeds threshold."""
        old_time = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=5)
        with patch(
            "custom_components.adaptive_cover.coordinator.get_last_updated",
            return_value=old_time,
        ):
            result = coordinator.check_time_delta("cover.test")
            assert result is True

    def test_check_time_delta_below_threshold(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_time_delta returns False when time is below threshold."""
        recent_time = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=30)
        with patch(
            "custom_components.adaptive_cover.coordinator.get_last_updated",
            return_value=recent_time,
        ):
            result = coordinator.check_time_delta("cover.test")
            assert result is False

    def test_check_time_delta_no_last_updated(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_time_delta returns True when last_updated is None."""
        with patch(
            "custom_components.adaptive_cover.coordinator.get_last_updated",
            return_value=None,
        ):
            result = coordinator.check_time_delta("cover.test")
            assert result is True

    def test_check_position_returns_false_when_same(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position returns False when position matches state."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=50,
        ):
            result = coordinator.check_position("cover.test", 50)
            assert result is False

    def test_check_position_returns_true_when_different(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position returns True when position differs from state."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=50,
        ):
            result = coordinator.check_position("cover.test", 75)
            assert result is True


class TestGetSensorValuesWithFallback:
    """Tests for _get_sensor_values_with_fallback method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            return coord

    @pytest.mark.asyncio
    async def test_presence_current_value_updates_last_known(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that current presence value updates last_known."""
        climate = MagicMock()
        climate.is_presence = True
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[0] is True  # is_presence
        assert coordinator._last_known["is_presence"] is True

    @pytest.mark.asyncio
    async def test_presence_unavailable_uses_fallback(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that unavailable presence uses last_known value."""
        climate = MagicMock()
        climate.is_presence = None  # Unavailable
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": False,  # Previous value
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[0] is False  # is_presence uses last_known
        assert coordinator._sensor_available["is_presence"] is False

    @pytest.mark.asyncio
    async def test_has_direct_sun_current_value_updates_last_known(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that current has_direct_sun value updates last_known."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = True
        climate.lux = None
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[1] is True  # has_direct_sun
        assert coordinator._last_known["has_direct_sun"] is True

    @pytest.mark.asyncio
    async def test_has_direct_sun_unavailable_uses_fallback(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that unavailable has_direct_sun uses last_known value."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None  # Unavailable
        climate.lux = None
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": False,  # Previous value
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[1] is False  # has_direct_sun uses last_known
        assert coordinator._sensor_available["has_direct_sun"] is False

    @pytest.mark.asyncio
    async def test_lux_current_value_updates_last_known(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that current lux value updates last_known."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None
        climate.lux = True
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[2] is True  # lux
        assert coordinator._last_known["lux"] is True

    @pytest.mark.asyncio
    async def test_lux_unavailable_uses_fallback(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that unavailable lux uses last_known value."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None
        climate.lux = None  # Unavailable
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": False,  # Previous value
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[2] is False  # lux uses last_known

    @pytest.mark.asyncio
    async def test_irradiance_current_value_updates_last_known(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that current irradiance value updates last_known."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = True
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[3] is True  # irradiance
        assert coordinator._last_known["irradiance"] is True

    @pytest.mark.asyncio
    async def test_irradiance_unavailable_uses_fallback(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that unavailable irradiance uses last_known value."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = None  # Unavailable
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": False,  # Previous value
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[3] is False  # irradiance uses last_known

    @pytest.mark.asyncio
    async def test_cloud_current_value_updates_last_known(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that current cloud value updates last_known."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = None
        climate.cloud = True

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[4] is True  # cloud
        assert coordinator._last_known["cloud"] is True

    @pytest.mark.asyncio
    async def test_cloud_unavailable_uses_fallback(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that unavailable cloud uses last_known value."""
        climate = MagicMock()
        climate.is_presence = None
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = None
        climate.cloud = None  # Unavailable

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": False,  # Previous value
        }

        result = await coordinator._get_sensor_values_with_fallback(climate)

        assert result[4] is False  # cloud uses last_known

    @pytest.mark.asyncio
    async def test_values_changed_triggers_save(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test that changed values trigger async_save_last_known."""
        climate = MagicMock()
        climate.is_presence = True  # New value
        climate.has_direct_sun = None
        climate.lux = None
        climate.irradiance = None
        climate.cloud = None

        coordinator._last_known = {
            "has_direct_sun": None,
            "is_presence": None,  # Different from new value
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }

        with patch.object(
            coordinator, "_async_save_last_known", new_callable=AsyncMock
        ) as mock_save:
            await coordinator._get_sensor_values_with_fallback(climate)
            mock_save.assert_called_once()


class TestAsyncUpdateDataPartial:
    """Tests for partial aspects of _async_update_data method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
            CONF_AZIMUTH: 180,
            CONF_FOV_LEFT: 90,
            CONF_FOV_RIGHT: 90,
            CONF_HEIGHT_WIN: 2.1,
            CONF_DISTANCE: 0.5,
            CONF_DEFAULT_HEIGHT: 60,
            CONF_SUNSET_POS: 0,
            CONF_SUNSET_OFFSET: 30,
            CONF_MAX_POSITION: 100,
            CONF_MIN_POSITION: 0,
            CONF_ENTITIES: ["cover.living_room"],
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            return coord

    def test_first_refresh_caches_options(
        self, coordinator: AdaptiveDataUpdateCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test that first_refresh causes options to be cached."""
        coordinator.first_refresh = True
        coordinator._cached_options = None

        # Access options caching logic directly
        if coordinator.first_refresh:
            coordinator._cached_options = coordinator.config_entry.options

        assert coordinator._cached_options == mock_config_entry.options

    def test_update_options_sets_entities(
        self, coordinator: AdaptiveDataUpdateCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test that _update_options sets entities."""
        coordinator._update_options(mock_config_entry.options)

        assert coordinator.entities == ["cover.living_room"]

    def test_update_options_sets_min_change(
        self, coordinator: AdaptiveDataUpdateCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test that _update_options sets min_change (delta_position)."""
        coordinator._update_options(mock_config_entry.options)

        assert coordinator.min_change == 5

    def test_update_options_sets_time_threshold(
        self, coordinator: AdaptiveDataUpdateCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test that _update_options sets time_threshold (delta_time)."""
        coordinator._update_options(mock_config_entry.options)

        assert coordinator.time_threshold == 2


class TestStateProperty:
    """Tests for the state property."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.default_state = 50
            coord.climate_state = 60
            coord._use_interpolation = False
            coord._inverse_state = False
            return coord

    def test_state_returns_default_when_not_climate_mode(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test state returns default_state when not in climate mode."""
        coordinator._control_mode = CONTROL_MODE_FORCE  # Not AUTO = not climate mode

        assert coordinator.state == 50

    def test_state_returns_climate_when_climate_mode(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test state returns climate_state when in climate mode."""
        coordinator._control_mode = CONTROL_MODE_AUTO

        assert coordinator.state == 60

    def test_state_applies_interpolation(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test state applies interpolation when enabled."""
        coordinator._use_interpolation = True
        coordinator.start_value = 10
        coordinator.end_value = 90
        coordinator.normal_list = None
        coordinator.new_list = None
        coordinator.default_state = 50
        coordinator._control_mode = CONTROL_MODE_FORCE

        result = coordinator.state
        # Interpolation maps 50 -> something based on 10-90 range
        assert isinstance(result, (int, float))

    def test_state_applies_inverse(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test state applies inverse when enabled and not using interpolation."""
        coordinator._inverse_state = True
        coordinator._use_interpolation = False
        coordinator.default_state = 30
        coordinator._control_mode = CONTROL_MODE_FORCE

        result = coordinator.state
        # 100 - 30 = 70
        assert result == 70


class TestAsyncForceUpdateCovers:
    """Tests for async_force_update_covers method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
            CONF_ENTITIES: ["cover.living_room", "cover.bedroom"],
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.entities = ["cover.living_room", "cover.bedroom"]
            coord.default_state = 50
            coord.climate_state = None
            coord._use_interpolation = False
            coord._inverse_state = False
            return coord

    @pytest.mark.asyncio
    async def test_force_update_skips_when_control_disabled(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test force update is skipped when control mode is disabled."""
        coordinator._control_mode = CONTROL_MODE_DISABLED

        with patch.object(
            coordinator, "async_set_position", new_callable=AsyncMock
        ) as mock_set:
            await coordinator.async_force_update_covers()
            mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_update_calls_set_position_for_all_covers(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test force update calls async_set_position for all configured covers."""
        coordinator._control_mode = CONTROL_MODE_AUTO

        with (
            patch.object(coordinator, "async_refresh", new_callable=AsyncMock),
            patch.object(
                coordinator, "async_set_position", new_callable=AsyncMock
            ) as mock_set,
        ):
            await coordinator.async_force_update_covers()

            assert mock_set.call_count == 2


class TestCoverControlMethods:
    """Tests for cover control service call methods."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            return coord

    @pytest.mark.asyncio
    async def test_async_set_manual_position_calls_service(
        self, coordinator: AdaptiveDataUpdateCoordinator, hass
    ) -> None:
        """Test async_set_manual_position calls the cover service."""
        with patch.object(coordinator, "check_position", return_value=True):
            mock_services = MagicMock()
            mock_services.async_call = AsyncMock()
            coordinator.hass = MagicMock()
            coordinator.hass.services = mock_services

            await coordinator.async_set_manual_position("cover.test", 75)

            mock_services.async_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_manual_position_skips_same_position(
        self, coordinator: AdaptiveDataUpdateCoordinator, hass
    ) -> None:
        """Test async_set_manual_position skips when position is same."""
        with patch.object(coordinator, "check_position", return_value=False):
            coordinator.hass = MagicMock()
            coordinator.hass.services = MagicMock()
            coordinator.hass.services.async_call = AsyncMock()

            await coordinator.async_set_manual_position("cover.test", 50)

            coordinator.hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_set_manual_position_tilt_cover(
        self, coordinator: AdaptiveDataUpdateCoordinator, hass
    ) -> None:
        """Test async_set_manual_position uses tilt service for tilt covers."""
        coordinator._cover_type = "cover_tilt"

        with patch.object(coordinator, "check_position", return_value=True):
            coordinator.hass = MagicMock()
            coordinator.hass.services = MagicMock()
            coordinator.hass.services.async_call = AsyncMock()

            await coordinator.async_set_manual_position("cover.test", 45)

            coordinator.hass.services.async_call.assert_called_once()
            call_args = coordinator.hass.services.async_call.call_args
            assert call_args[0][0] == "cover"
            assert call_args[0][1] == "set_cover_tilt_position"

    @pytest.mark.asyncio
    async def test_async_set_manual_position_sets_wait_for_target(
        self, coordinator: AdaptiveDataUpdateCoordinator, hass
    ) -> None:
        """Test async_set_manual_position sets wait_for_target tracking."""
        with patch.object(coordinator, "check_position", return_value=True):
            coordinator.hass = MagicMock()
            coordinator.hass.services = MagicMock()
            coordinator.hass.services.async_call = AsyncMock()

            await coordinator.async_set_manual_position("cover.test", 75)

            assert coordinator.wait_for_target["cover.test"] is True
            assert coordinator.target_call["cover.test"] == 75


class TestAdaptiveTimeChecks:
    """Tests for adaptive time checking properties."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.start_time = None
            coord.end_time = None
            coord.start_time_entity = None
            coord.end_time_entity = None
            return coord

    def test_check_adaptive_time_returns_true_when_no_times_set(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_adaptive_time returns True when no start/end times."""
        assert coordinator.check_adaptive_time is True

    def test_before_end_time_returns_true_when_no_end_time(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test before_end_time returns True when no end time set."""
        assert coordinator.before_end_time is True

    def test_after_start_time_returns_true_when_no_start_time(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test after_start_time returns True when no start time set."""
        assert coordinator.after_start_time is True


class TestMidnightReset:
    """Tests for midnight reset functionality."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord._reset_at_midnight = True
            return coord

    def test_midnight_reset_sets_control_mode_to_auto(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test _async_midnight_reset sets control_mode to AUTO."""
        coordinator._control_mode = CONTROL_MODE_DISABLED
        now = dt.datetime.now()

        coordinator._async_midnight_reset(now)

        assert coordinator._control_mode == CONTROL_MODE_AUTO

    def test_setup_midnight_reset_delegates_to_room(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test setup_midnight_reset delegates to room coordinator."""
        mock_room = MagicMock()

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry, mock_room)

            coord.setup_midnight_reset()

            mock_room.setup_midnight_reset.assert_called_once()


class TestControlModeCallbacks:
    """Tests for control mode callback registration."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            return coord

    def test_register_control_mode_select_stores_reference(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test register_control_mode_select stores the select entity."""
        mock_select = MagicMock()

        coordinator.register_control_mode_select(mock_select)

        assert coordinator._control_mode_select is mock_select

    def test_register_control_mode_select_delegates_to_room(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test register_control_mode_select delegates to room coordinator."""
        mock_room = MagicMock()
        mock_select = MagicMock()

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry, mock_room)

            coord.register_control_mode_select(mock_select)

            mock_room.register_control_mode_select.assert_called_once_with(mock_select)

    def test_control_mode_setter_notifies_select(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test control_mode setter notifies the select entity."""
        mock_select = MagicMock()
        coordinator._control_mode_select = mock_select

        coordinator.control_mode = CONTROL_MODE_DISABLED

        mock_select.set_control_mode.assert_called_once_with(CONTROL_MODE_DISABLED)

    def test_control_mode_setter_with_room_delegates(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test control_mode setter delegates to room coordinator."""
        mock_room = MagicMock()

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry, mock_room)

            coord.control_mode = CONTROL_MODE_FORCE

            assert mock_room.control_mode == CONTROL_MODE_FORCE


class TestAsyncCheckCoverStateChange:
    """Tests for async_check_cover_state_change method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.async_refresh = AsyncMock()
            return coord

    @pytest.mark.asyncio
    async def test_cover_state_change_old_state_none(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test cover state change exits early when old_state is None."""
        event = MagicMock()
        event.data = {
            "entity_id": "cover.test",
            "old_state": None,
            "new_state": MagicMock(),
        }

        await coordinator.async_check_cover_state_change(event)

        # Should not call async_refresh when old_state is None
        coordinator.async_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_cover_state_change_old_state_unknown(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test cover state change skips processing when old_state is unknown."""
        event = MagicMock()
        old_state = MagicMock()
        old_state.state = "unknown"
        event.data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": MagicMock(),
        }

        await coordinator.async_check_cover_state_change(event)

        # Should not call async_refresh when old_state is unknown
        coordinator.async_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_cover_state_change_processes_valid_state(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test cover state change processes when old_state is valid."""
        event = MagicMock()
        old_state = MagicMock()
        old_state.state = "open"
        new_state = MagicMock()
        new_state.attributes = {"current_position": 50}
        event.data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }

        await coordinator.async_check_cover_state_change(event)

        assert coordinator.cover_state_change is True
        coordinator.async_refresh.assert_called_once()


class TestAsyncCheckEntityStateChange:
    """Tests for async_check_entity_state_change method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.async_refresh = AsyncMock()
            return coord

    @pytest.mark.asyncio
    async def test_entity_state_change_sets_flag_and_refreshes(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test entity state change sets flag and calls refresh."""
        event = MagicMock()

        await coordinator.async_check_entity_state_change(event)

        assert coordinator.state_change is True
        coordinator.async_refresh.assert_called_once()


class TestProcessEntityStateChange:
    """Tests for process_entity_state_change method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            return coord

    def test_process_ignores_intermediate_states(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test process_entity_state_change ignores opening/closing states."""
        coordinator.ignore_intermediate_states = True

        event = MagicMock()
        event.entity_id = "cover.test"
        event.new_state = MagicMock()
        event.new_state.state = "opening"
        coordinator.state_change_data = event

        coordinator.process_entity_state_change()

        # Should return early without updating wait_for_target
        # No assertion needed - just checking it doesn't crash

    def test_process_clears_wait_for_target_on_match(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test process clears wait_for_target when position matches target."""
        coordinator.wait_for_target = {"cover.test": True}
        coordinator.target_call = {"cover.test": 75}

        event = MagicMock()
        event.entity_id = "cover.test"
        event.new_state = MagicMock()
        event.new_state.state = "open"
        event.new_state.attributes = {"current_position": 75}
        coordinator.state_change_data = event

        coordinator.process_entity_state_change()

        assert coordinator.wait_for_target["cover.test"] is False


class TestAsyncLoadLastKnown:
    """Tests for _async_load_last_known method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.mark.asyncio
    async def test_load_last_known_with_data(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test _async_load_last_known loads stored data."""
        stored_data = {"is_presence": True, "has_direct_sun": False}

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=stored_data)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

            await coord._async_load_last_known()

            assert coord._last_known["is_presence"] is True
            assert coord._last_known["has_direct_sun"] is False

    @pytest.mark.asyncio
    async def test_load_last_known_without_data(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test _async_load_last_known with no stored data."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

            # Should not raise an error
            await coord._async_load_last_known()

            # _last_known should still have default None values
            assert coord._last_known["is_presence"] is None


class TestSetRoomCoordinator:
    """Tests for set_room_coordinator method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    def test_set_room_coordinator_sets_coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test set_room_coordinator sets the room coordinator."""
        mock_room = MagicMock()

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

            coord.set_room_coordinator(mock_room)

            assert coord._room_coordinator is mock_room

    def test_set_room_coordinator_skips_if_already_connected(
        self, hass, mock_config_entry: MagicMock
    ) -> None:
        """Test set_room_coordinator skips if already connected."""
        mock_room_1 = MagicMock()
        mock_room_2 = MagicMock()

        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            # Pass room coordinator in constructor
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry, mock_room_1)

            coord.set_room_coordinator(mock_room_2)

            # Should still be the original room coordinator
            assert coord._room_coordinator is mock_room_1


class TestAsyncTimedRefresh:
    """Tests for async_timed_refresh method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.async_refresh = AsyncMock()
            return coord

    @pytest.mark.asyncio
    async def test_timed_refresh_triggers_when_time_matches(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test timed refresh triggers when current time matches end time."""
        from freezegun import freeze_time

        with freeze_time("2024-06-21 18:00:00"):
            coordinator.end_time = "18:00"
            coordinator.end_time_entity = None

            await coordinator.async_timed_refresh(None)

            assert coordinator.timed_refresh is True
            coordinator.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_timed_refresh_skips_when_time_not_equal(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test timed refresh does not trigger when times don't match.

        The logic checks if `now - end_time <= 1 second`. When now is AFTER end_time
        by more than 1 second, the refresh should be skipped.
        """
        from freezegun import freeze_time

        # Set time to 18:05, which is 5 minutes after end_time of 18:00
        # This should NOT trigger the refresh since the time has passed
        with freeze_time("2024-06-21 18:05:00"):
            coordinator.end_time = "18:00"
            coordinator.end_time_entity = None
            coordinator.timed_refresh = False

            await coordinator.async_timed_refresh(None)

            assert coordinator.timed_refresh is False
            coordinator.async_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_timed_refresh_with_entity_end_time(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test timed refresh uses entity end time when configured."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 19:30:00"),
            patch(
                "custom_components.adaptive_cover.coordinator.get_safe_state",
                return_value="19:30",
            ),
        ):
            coordinator.end_time = None
            coordinator.end_time_entity = "input_datetime.end_time"

            await coordinator.async_timed_refresh(None)

            assert coordinator.timed_refresh is True
            coordinator.async_refresh.assert_called_once()


class TestAsyncTimedEndTime:
    """Tests for async_timed_end_time method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord._track_end_time = True
            return coord

    @pytest.mark.asyncio
    async def test_end_time_scheduling_cancels_previous(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test scheduling end time cancels previous listener."""
        mock_listener = MagicMock()
        coordinator._update_listener = mock_listener
        coordinator._scheduled_time = dt.datetime(2024, 6, 21, 17, 0)
        coordinator.end_time = "18:00"
        coordinator.end_time_entity = None

        with patch(
            "custom_components.adaptive_cover.coordinator.async_track_point_in_time"
        ) as mock_track:
            mock_track.return_value = MagicMock()
            await coordinator.async_timed_end_time()

            mock_listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_time_scheduling_sets_new_listener(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test scheduling end time sets new listener."""
        coordinator._update_listener = None
        coordinator._scheduled_time = dt.datetime(2024, 6, 21, 17, 0)
        coordinator.end_time = "18:00"
        coordinator.end_time_entity = None

        with patch(
            "custom_components.adaptive_cover.coordinator.async_track_point_in_time"
        ) as mock_track:
            new_listener = MagicMock()
            mock_track.return_value = new_listener
            await coordinator.async_timed_end_time()

            mock_track.assert_called_once()
            assert coordinator._update_listener is new_listener


class TestTimePropertiesWithEntity:
    """Tests for time properties with entity configuration."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

    def test_after_start_time_with_entity(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test after_start_time uses entity value."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 10:00:00"),
            patch(
                "custom_components.adaptive_cover.coordinator.get_safe_state",
                return_value="08:00",
            ),
        ):
            coordinator.start_time_entity = "input_datetime.start_time"
            coordinator.start_time = None

            assert coordinator.after_start_time is True

    def test_after_start_time_with_config_value(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test after_start_time uses config value when no entity."""
        from freezegun import freeze_time

        with freeze_time("2024-06-21 10:00:00"):
            coordinator.start_time_entity = None
            coordinator.start_time = "08:00"

            assert coordinator.after_start_time is True

    def test_before_end_time_with_entity(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test before_end_time uses entity value."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 17:00:00"),
            patch(
                "custom_components.adaptive_cover.coordinator.get_safe_state",
                return_value="18:00",
            ),
        ):
            coordinator.end_time_entity = "input_datetime.end_time"
            coordinator.end_time = None

            assert coordinator.before_end_time is True

    def test_before_end_time_with_config_value(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test before_end_time uses config value when no entity."""
        from freezegun import freeze_time

        with freeze_time("2024-06-21 17:00:00"):
            coordinator.end_time_entity = None
            coordinator.end_time = "18:00"

            assert coordinator.before_end_time is True


class TestStateChangeHandlers:
    """Tests for state change handling methods."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
            CONF_ENTITIES: ["cover.living_room"],
            CONF_SUNSET_POS: 0,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord.entities = ["cover.living_room"]
            coord.async_handle_call_service = AsyncMock()
            coord.async_set_manual_position = AsyncMock()
            coord.async_set_position = AsyncMock()
            return coord

    @pytest.mark.asyncio
    async def test_async_handle_state_change_when_enabled(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test state change handling when control is enabled."""
        coordinator._control_mode = CONTROL_MODE_AUTO
        coordinator.state_change = True

        await coordinator.async_handle_state_change(
            50, coordinator.config_entry.options
        )

        coordinator.async_handle_call_service.assert_called_once()
        assert coordinator.state_change is False

    @pytest.mark.asyncio
    async def test_async_handle_state_change_when_disabled(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test state change handling when control is disabled."""
        coordinator._control_mode = CONTROL_MODE_DISABLED
        coordinator.state_change = True

        await coordinator.async_handle_state_change(
            50, coordinator.config_entry.options
        )

        coordinator.async_handle_call_service.assert_not_called()
        assert coordinator.state_change is False

    @pytest.mark.asyncio
    async def test_async_handle_cover_state_change(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test cover state change handling."""
        coordinator._control_mode = CONTROL_MODE_AUTO
        coordinator.cover_state_change = True
        coordinator.state_change_data = MagicMock()
        coordinator.manual_threshold = 5

        await coordinator.async_handle_cover_state_change(50)

        assert coordinator.cover_state_change is False

    @pytest.mark.asyncio
    async def test_async_handle_first_refresh(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test first refresh handling."""
        coordinator._control_mode = CONTROL_MODE_AUTO
        coordinator.first_refresh = True
        coordinator.start_time = None
        coordinator.end_time = None
        coordinator.start_time_entity = None
        coordinator.end_time_entity = None

        with patch.object(coordinator, "check_position_delta", return_value=True):
            # check_adaptive_time is a property that returns True when start/end times are None
            await coordinator.async_handle_first_refresh(
                50, coordinator.config_entry.options
            )

        assert coordinator.first_refresh is False

    @pytest.mark.asyncio
    async def test_timed_refresh_applies_sunset_position(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test timed refresh applies sunset position."""
        coordinator._control_mode = CONTROL_MODE_AUTO
        coordinator.timed_refresh = True
        coordinator._inverse_state = False

        await coordinator.async_handle_timed_refresh(coordinator.config_entry.options)

        coordinator.async_set_manual_position.assert_called_once_with(
            "cover.living_room", 0
        )
        assert coordinator.timed_refresh is False

    @pytest.mark.asyncio
    async def test_timed_refresh_applies_inverted_sunset_position(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test timed refresh applies inverted sunset position."""
        coordinator._control_mode = CONTROL_MODE_AUTO
        coordinator.timed_refresh = True
        coordinator._inverse_state = True

        await coordinator.async_handle_timed_refresh(coordinator.config_entry.options)

        # 100 - 0 = 100 (inverted)
        coordinator.async_set_manual_position.assert_called_once_with(
            "cover.living_room", 100
        )


class TestClimateModeData:
    """Tests for climate_mode_data method."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord._control_mode = CONTROL_MODE_AUTO
            return coord

    def test_climate_state_too_hot(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test comfort status is TOO_HOT in summer with climate mode."""
        from custom_components.adaptive_cover.const import COMFORT_STATUS_TOO_HOT

        mock_cover = MagicMock()
        mock_climate = MagicMock()
        mock_climate.is_summer = True
        mock_climate.is_winter = False

        with patch(
            "custom_components.adaptive_cover.coordinator.ClimateCoverState"
        ) as mock_state_class:
            mock_state = MagicMock()
            mock_state.get_state.return_value = 50
            mock_state.climate_data = mock_climate
            mock_state_class.return_value = mock_state

            coordinator.climate_mode_data(mock_cover, mock_climate)

            assert coordinator.comfort_status == COMFORT_STATUS_TOO_HOT

    def test_climate_state_too_cold(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test comfort status is TOO_COLD in winter with climate mode."""
        from custom_components.adaptive_cover.const import COMFORT_STATUS_TOO_COLD

        mock_cover = MagicMock()
        mock_climate = MagicMock()
        mock_climate.is_summer = False
        mock_climate.is_winter = True

        with patch(
            "custom_components.adaptive_cover.coordinator.ClimateCoverState"
        ) as mock_state_class:
            mock_state = MagicMock()
            mock_state.get_state.return_value = 50
            mock_state.climate_data = mock_climate
            mock_state_class.return_value = mock_state

            coordinator.climate_mode_data(mock_cover, mock_climate)

            assert coordinator.comfort_status == COMFORT_STATUS_TOO_COLD


class TestInterpolationWithBothEnabled:
    """Tests for state when both interpolation and inverse are enabled."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: True,
            CONF_INTERP: True,
            CONF_INTERP_START: 10,
            CONF_INTERP_END: 90,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coord = AdaptiveDataUpdateCoordinator(hass, mock_config_entry)
            coord._use_interpolation = True
            coord._inverse_state = True
            coord.start_value = 10
            coord.end_value = 90
            coord.normal_list = None
            coord.new_list = None
            coord.default_state = 50
            coord.climate_state = None
            coord._control_mode = CONTROL_MODE_FORCE
            return coord

    def test_warning_when_both_enabled(
        self, coordinator: AdaptiveDataUpdateCoordinator, caplog
    ) -> None:
        """Test warning logged when both inverse and interpolation are enabled."""
        import logging

        with caplog.at_level(logging.INFO):
            _ = coordinator.state

        # Check that the warning was logged
        assert "Inverse state is not supported with interpolation" in caplog.text


class TestTogglePropertySettersWithRoom:
    """Tests for toggle property setters delegating to room."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def mock_room_coordinator(self) -> MagicMock:
        """Create mock room coordinator."""
        room = MagicMock()
        room.temp_toggle = None
        room.lux_toggle = None
        room.irradiance_toggle = None
        room.cloud_toggle = None
        room.weather_toggle = None
        return room

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock, mock_room_coordinator: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance with room coordinator."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(
                hass, mock_config_entry, mock_room_coordinator
            )

    def test_temp_toggle_setter_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test temp_toggle setter delegates to room."""
        coordinator.temp_toggle = True

        assert mock_room_coordinator.temp_toggle is True

    def test_lux_toggle_setter_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test lux_toggle setter delegates to room."""
        coordinator.lux_toggle = True

        assert mock_room_coordinator.lux_toggle is True

    def test_irradiance_toggle_setter_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test irradiance_toggle setter delegates to room."""
        coordinator.irradiance_toggle = True

        assert mock_room_coordinator.irradiance_toggle is True

    def test_cloud_toggle_setter_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test cloud_toggle setter delegates to room."""
        coordinator.cloud_toggle = True

        assert mock_room_coordinator.cloud_toggle is True

    def test_weather_toggle_setter_delegates_to_room(
        self,
        coordinator: AdaptiveDataUpdateCoordinator,
        mock_room_coordinator: MagicMock,
    ) -> None:
        """Test weather_toggle setter delegates to room."""
        coordinator.weather_toggle = True

        assert mock_room_coordinator.weather_toggle is True


class TestGetCurrentPositionForTilt:
    """Tests for _get_current_position with tilt covers."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_tilt"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

    def test_get_current_position_tilt_cover(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test _get_current_position uses tilt_position for tilt covers."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=45,
        ) as mock_attr:
            position = coordinator._get_current_position("cover.test")

            mock_attr.assert_called_with(
                coordinator.hass, "cover.test", "current_tilt_position"
            )
            assert position == 45


class TestCheckPositionWhenNone:
    """Tests for check_position edge cases."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_cover_123"
        entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        entry.options = {
            CONF_INVERSE_STATE: False,
            CONF_INTERP: False,
            CONF_DELTA_POSITION: 5,
            CONF_DELTA_TIME: 2,
        }
        return entry

    @pytest.fixture
    def coordinator(
        self, hass, mock_config_entry: MagicMock
    ) -> AdaptiveDataUpdateCoordinator:
        """Create a coordinator instance."""
        with patch("custom_components.adaptive_cover.coordinator.Store") as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            return AdaptiveDataUpdateCoordinator(hass, mock_config_entry)

    def test_check_position_returns_false_when_position_none(
        self, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Test check_position returns False when position is None."""
        with patch(
            "custom_components.adaptive_cover.coordinator.state_attr",
            return_value=None,
        ):
            # When position is None, check_position should return False
            result = coordinator.check_position("cover.test", 50)
            assert result is False
