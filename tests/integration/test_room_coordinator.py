"""Tests for RoomCoordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.adaptive_cover.const import (
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    CONTROL_MODE_FORCE,
)
from custom_components.adaptive_cover.room_coordinator import RoomCoordinator, RoomData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestRoomData:
    """Tests for RoomData dataclass."""

    def test_room_data_creation(self) -> None:
        """Test RoomData can be created with all fields."""
        data = RoomData(
            control_mode=CONTROL_MODE_AUTO,
            temp_toggle=True,
            lux_toggle=False,
            irradiance_toggle=None,
            cloud_toggle=True,
            weather_toggle=False,
            is_presence=True,
            has_direct_sun=True,
        )

        assert data.control_mode == CONTROL_MODE_AUTO
        assert data.temp_toggle is True
        assert data.lux_toggle is False
        assert data.irradiance_toggle is None
        assert data.cloud_toggle is True
        assert data.weather_toggle is False
        assert data.is_presence is True
        assert data.has_direct_sun is True
        assert data.climate_data_args is None
        assert data.sensor_available == {}
        assert data.last_known == {}

    def test_room_data_with_climate_data_args(self) -> None:
        """Test RoomData with climate data args."""
        climate_args = ["hass", "logger", "sensor.temp"]
        data = RoomData(
            control_mode=CONTROL_MODE_AUTO,
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=None,
            has_direct_sun=None,
            climate_data_args=climate_args,
        )

        assert data.climate_data_args == climate_args

    def test_room_data_with_sensor_available(self) -> None:
        """Test RoomData with sensor availability."""
        sensor_available = {"is_presence": True, "has_direct_sun": False}
        data = RoomData(
            control_mode=CONTROL_MODE_FORCE,
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=None,
            has_direct_sun=None,
            sensor_available=sensor_available,
        )

        assert data.sensor_available == sensor_available

    def test_room_data_with_last_known(self) -> None:
        """Test RoomData with last known values."""
        last_known = {"is_presence": True, "cloud": 50.0}
        data = RoomData(
            control_mode=CONTROL_MODE_DISABLED,
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=None,
            has_direct_sun=None,
            last_known=last_known,
        )

        assert data.last_known == last_known


class TestRoomCoordinatorProperties:
    """Tests for RoomCoordinator properties."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {
            "climate_mode": True,
            "reset_at_midnight": True,
            "delta_position": 5,
            "delta_time": 3,
        }
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    def test_control_mode_default(self, room_coordinator: RoomCoordinator) -> None:
        """Test control mode defaults to AUTO."""
        assert room_coordinator.control_mode == CONTROL_MODE_AUTO

    def test_control_mode_setter(self, room_coordinator: RoomCoordinator) -> None:
        """Test setting control mode."""
        room_coordinator.control_mode = CONTROL_MODE_DISABLED
        assert room_coordinator.control_mode == CONTROL_MODE_DISABLED

        room_coordinator.control_mode = CONTROL_MODE_FORCE
        assert room_coordinator.control_mode == CONTROL_MODE_FORCE

        room_coordinator.control_mode = CONTROL_MODE_AUTO
        assert room_coordinator.control_mode == CONTROL_MODE_AUTO

    def test_control_mode_invalid_value(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test that invalid control mode values are ignored."""
        room_coordinator.control_mode = CONTROL_MODE_AUTO
        room_coordinator.control_mode = "invalid_mode"
        # Should still be AUTO since invalid values are ignored
        assert room_coordinator.control_mode == CONTROL_MODE_AUTO

    def test_is_control_enabled(self, room_coordinator: RoomCoordinator) -> None:
        """Test is_control_enabled property."""
        room_coordinator.control_mode = CONTROL_MODE_AUTO
        assert room_coordinator.is_control_enabled is True

        room_coordinator.control_mode = CONTROL_MODE_FORCE
        assert room_coordinator.is_control_enabled is True

        room_coordinator.control_mode = CONTROL_MODE_DISABLED
        assert room_coordinator.is_control_enabled is False

    def test_is_climate_mode(self, room_coordinator: RoomCoordinator) -> None:
        """Test is_climate_mode property."""
        room_coordinator.control_mode = CONTROL_MODE_AUTO
        assert room_coordinator.is_climate_mode is True

        room_coordinator.control_mode = CONTROL_MODE_FORCE
        assert room_coordinator.is_climate_mode is False

        room_coordinator.control_mode = CONTROL_MODE_DISABLED
        assert room_coordinator.is_climate_mode is False

    def test_delta_position(self, room_coordinator: RoomCoordinator) -> None:
        """Test delta_position property."""
        assert room_coordinator.delta_position == 5

    def test_delta_time(self, room_coordinator: RoomCoordinator) -> None:
        """Test delta_time property."""
        assert room_coordinator.delta_time == 3

    def test_temp_toggle(self, room_coordinator: RoomCoordinator) -> None:
        """Test temp_toggle property."""
        assert room_coordinator.temp_toggle is None

        room_coordinator.temp_toggle = True
        assert room_coordinator.temp_toggle is True

        room_coordinator.temp_toggle = False
        assert room_coordinator.temp_toggle is False

    def test_lux_toggle(self, room_coordinator: RoomCoordinator) -> None:
        """Test lux_toggle property."""
        assert room_coordinator.lux_toggle is None

        room_coordinator.lux_toggle = True
        assert room_coordinator.lux_toggle is True

    def test_irradiance_toggle(self, room_coordinator: RoomCoordinator) -> None:
        """Test irradiance_toggle property."""
        assert room_coordinator.irradiance_toggle is None

        room_coordinator.irradiance_toggle = True
        assert room_coordinator.irradiance_toggle is True

    def test_cloud_toggle(self, room_coordinator: RoomCoordinator) -> None:
        """Test cloud_toggle property."""
        assert room_coordinator.cloud_toggle is None

        room_coordinator.cloud_toggle = True
        assert room_coordinator.cloud_toggle is True

    def test_weather_toggle(self, room_coordinator: RoomCoordinator) -> None:
        """Test weather_toggle property."""
        assert room_coordinator.weather_toggle is None

        room_coordinator.weather_toggle = True
        assert room_coordinator.weather_toggle is True

    def test_get_option(self, room_coordinator: RoomCoordinator) -> None:
        """Test get_option method."""
        assert room_coordinator.get_option("delta_position") == 5
        assert room_coordinator.get_option("nonexistent", "default") == "default"


class TestRoomCoordinatorCoverManagement:
    """Tests for RoomCoordinator cover management."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {}
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    def test_register_cover(self, room_coordinator: RoomCoordinator) -> None:
        """Test registering a cover coordinator."""
        mock_cover = MagicMock()

        room_coordinator.register_cover(mock_cover)

        assert mock_cover in room_coordinator._child_coordinators
        assert len(room_coordinator._child_coordinators) == 1

    def test_register_cover_duplicate(self, room_coordinator: RoomCoordinator) -> None:
        """Test registering same cover twice doesn't duplicate."""
        mock_cover = MagicMock()

        room_coordinator.register_cover(mock_cover)
        room_coordinator.register_cover(mock_cover)

        assert len(room_coordinator._child_coordinators) == 1

    def test_unregister_cover(self, room_coordinator: RoomCoordinator) -> None:
        """Test unregistering a cover coordinator."""
        mock_cover = MagicMock()
        room_coordinator.register_cover(mock_cover)

        room_coordinator.unregister_cover(mock_cover)

        assert mock_cover not in room_coordinator._child_coordinators
        assert len(room_coordinator._child_coordinators) == 0

    def test_unregister_nonexistent_cover(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test unregistering a cover that was never registered."""
        mock_cover = MagicMock()

        # Should not raise error
        room_coordinator.unregister_cover(mock_cover)

        assert len(room_coordinator._child_coordinators) == 0

    def test_start_sun_no_covers(self, room_coordinator: RoomCoordinator) -> None:
        """Test start_sun with no covers returns None."""
        assert room_coordinator.start_sun is None

    def test_end_sun_no_covers(self, room_coordinator: RoomCoordinator) -> None:
        """Test end_sun with no covers returns None."""
        assert room_coordinator.end_sun is None

    def test_comfort_status_no_covers(self, room_coordinator: RoomCoordinator) -> None:
        """Test comfort_status with no covers returns None."""
        assert room_coordinator.comfort_status is None

    def test_start_sun_with_covers(self, room_coordinator: RoomCoordinator) -> None:
        """Test start_sun aggregates from covers."""
        from datetime import datetime

        mock_cover1 = MagicMock()
        mock_cover1.data.states = {"start": datetime(2024, 6, 21, 8, 0, 0)}

        mock_cover2 = MagicMock()
        mock_cover2.data.states = {"start": datetime(2024, 6, 21, 9, 0, 0)}

        room_coordinator.register_cover(mock_cover1)
        room_coordinator.register_cover(mock_cover2)

        # Should return the earliest time
        result = room_coordinator.start_sun
        assert result == datetime(2024, 6, 21, 8, 0, 0)

    def test_end_sun_with_covers(self, room_coordinator: RoomCoordinator) -> None:
        """Test end_sun aggregates from covers."""
        from datetime import datetime

        mock_cover1 = MagicMock()
        mock_cover1.data.states = {"end": datetime(2024, 6, 21, 18, 0, 0)}

        mock_cover2 = MagicMock()
        mock_cover2.data.states = {"end": datetime(2024, 6, 21, 19, 0, 0)}

        room_coordinator.register_cover(mock_cover1)
        room_coordinator.register_cover(mock_cover2)

        # Should return the latest time
        result = room_coordinator.end_sun
        assert result == datetime(2024, 6, 21, 19, 0, 0)

    def test_comfort_status_with_covers(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test comfort_status returns first cover's status."""
        mock_cover1 = MagicMock()
        mock_cover1.comfort_status = "comfortable"

        mock_cover2 = MagicMock()
        mock_cover2.comfort_status = "too_warm"

        room_coordinator.register_cover(mock_cover1)
        room_coordinator.register_cover(mock_cover2)

        assert room_coordinator.comfort_status == "comfortable"


class TestRoomCoordinatorSensorUpdates:
    """Tests for RoomCoordinator sensor value updates."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {}
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    def test_update_last_known(self, room_coordinator: RoomCoordinator) -> None:
        """Test update_last_known method."""
        room_coordinator.update_last_known("is_presence", True)
        assert room_coordinator._last_known["is_presence"] is True

    def test_update_sensor_available(self, room_coordinator: RoomCoordinator) -> None:
        """Test update_sensor_available method."""
        room_coordinator.update_sensor_available("cloud", True)
        assert room_coordinator._sensor_available["cloud"] is True

        room_coordinator.update_sensor_available("cloud", False)
        assert room_coordinator._sensor_available["cloud"] is False

    def test_register_control_mode_select(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test registering control mode select entity."""
        mock_select = MagicMock()
        room_coordinator.register_control_mode_select(mock_select)

        assert room_coordinator._control_mode_select is mock_select

    def test_control_mode_notifies_select(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test that setting control mode notifies select entity."""
        mock_select = MagicMock()
        room_coordinator.register_control_mode_select(mock_select)

        room_coordinator.control_mode = CONTROL_MODE_FORCE

        mock_select.set_control_mode.assert_called_once_with(CONTROL_MODE_FORCE)


class TestRoomCoordinatorOptionAccessors:
    """Tests for RoomCoordinator option accessor properties."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry with various options."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {
            "start_time": "08:00",
            "end_time": "20:00",
            "start_entity": "sensor.sunrise",
            "end_entity": "sensor.sunset",
            "manual_threshold": 10,
            "manual_ignore_intermediate": True,
            "climate_mode": True,
            "return_sunset": True,
        }
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    def test_start_time(self, room_coordinator: RoomCoordinator) -> None:
        """Test start_time property."""
        assert room_coordinator.start_time == "08:00"

    def test_start_time_entity(self, room_coordinator: RoomCoordinator) -> None:
        """Test start_time_entity property."""
        assert room_coordinator.start_time_entity == "sensor.sunrise"

    def test_end_time(self, room_coordinator: RoomCoordinator) -> None:
        """Test end_time property."""
        assert room_coordinator.end_time == "20:00"

    def test_end_time_entity(self, room_coordinator: RoomCoordinator) -> None:
        """Test end_time_entity property."""
        assert room_coordinator.end_time_entity == "sensor.sunset"

    def test_manual_threshold(self, room_coordinator: RoomCoordinator) -> None:
        """Test manual_threshold property."""
        assert room_coordinator.manual_threshold == 10

    def test_ignore_intermediate_states(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test ignore_intermediate_states property."""
        assert room_coordinator.ignore_intermediate_states is True

    def test_climate_mode_enabled(self, room_coordinator: RoomCoordinator) -> None:
        """Test climate_mode_enabled property."""
        assert room_coordinator.climate_mode_enabled is True

    def test_track_end_time(self, room_coordinator: RoomCoordinator) -> None:
        """Test track_end_time property."""
        assert room_coordinator.track_end_time is True


class TestRoomCoordinatorWithNoCoverData:
    """Tests for RoomCoordinator when covers have no data."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {}
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    def test_start_sun_with_cover_no_data(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test start_sun when cover has no data."""
        mock_cover = MagicMock()
        mock_cover.data = None

        room_coordinator.register_cover(mock_cover)

        assert room_coordinator.start_sun is None

    def test_end_sun_with_cover_no_data(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test end_sun when cover has no data."""
        mock_cover = MagicMock()
        mock_cover.data = None

        room_coordinator.register_cover(mock_cover)

        assert room_coordinator.end_sun is None

    def test_start_sun_with_cover_no_start_key(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test start_sun when cover data has no start key."""
        mock_cover = MagicMock()
        mock_cover.data.states = {"end": "2024-06-21 20:00:00"}

        room_coordinator.register_cover(mock_cover)

        assert room_coordinator.start_sun is None

    def test_comfort_status_with_no_status(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test comfort_status when cover has no status."""
        mock_cover = MagicMock()
        mock_cover.comfort_status = None

        room_coordinator.register_cover(mock_cover)

        assert room_coordinator.comfort_status is None


class TestRoomCoordinatorAsync:
    """Tests for RoomCoordinator async methods."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {}
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    @pytest.mark.asyncio
    async def test_async_load_last_known(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test _async_load_last_known loads values from storage."""
        stored_data = {"is_presence": True, "has_direct_sun": False, "cloud": 50.0}
        room_coordinator._store.async_load = AsyncMock(return_value=stored_data)

        await room_coordinator._async_load_last_known()

        assert room_coordinator._last_known["is_presence"] is True
        assert room_coordinator._last_known["has_direct_sun"] is False
        assert room_coordinator._last_known["cloud"] == 50.0

    @pytest.mark.asyncio
    async def test_async_load_last_known_no_data(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test _async_load_last_known handles missing data."""
        room_coordinator._store.async_load = AsyncMock(return_value=None)

        await room_coordinator._async_load_last_known()

        # Should keep default None values
        assert room_coordinator._last_known["is_presence"] is None
        assert room_coordinator._last_known["has_direct_sun"] is None

    @pytest.mark.asyncio
    async def test_async_save_last_known(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test _async_save_last_known saves values to storage."""
        room_coordinator._last_known = {"is_presence": True, "cloud": 75.0}
        room_coordinator._store.async_save = AsyncMock()

        await room_coordinator._async_save_last_known()

        room_coordinator._store.async_save.assert_called_once_with(
            room_coordinator._last_known
        )

    @pytest.mark.asyncio
    async def test_async_notify_children(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test async_notify_children notifies all child coordinators."""
        mock_child1 = MagicMock()
        mock_child1.state_change = False
        mock_child1.async_refresh = AsyncMock()

        mock_child2 = MagicMock()
        mock_child2.state_change = False
        mock_child2.async_refresh = AsyncMock()

        room_coordinator.register_cover(mock_child1)
        room_coordinator.register_cover(mock_child2)

        await room_coordinator.async_notify_children()

        assert mock_child1.state_change is True
        assert mock_child2.state_change is True
        mock_child1.async_refresh.assert_called_once()
        mock_child2.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_force_update_covers(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test async_force_update_covers updates all child covers."""
        mock_child1 = MagicMock()
        mock_child1.async_force_update_covers = AsyncMock()

        mock_child2 = MagicMock()
        mock_child2.async_force_update_covers = AsyncMock()

        room_coordinator.register_cover(mock_child1)
        room_coordinator.register_cover(mock_child2)

        await room_coordinator.async_force_update_covers()

        mock_child1.async_force_update_covers.assert_called_once()
        mock_child2.async_force_update_covers.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_check_entity_state_change(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test async_check_entity_state_change triggers refresh and notifies children."""
        # Set up data so refresh works
        room_coordinator.data = RoomData(
            control_mode=CONTROL_MODE_AUTO,
            temp_toggle=None,
            lux_toggle=None,
            irradiance_toggle=None,
            cloud_toggle=None,
            weather_toggle=None,
            is_presence=None,
            has_direct_sun=None,
        )

        with (
            patch.object(
                room_coordinator, "async_refresh", new_callable=AsyncMock
            ) as mock_refresh,
            patch.object(
                room_coordinator, "async_notify_children", new_callable=AsyncMock
            ) as mock_notify,
        ):
            event = MagicMock()
            await room_coordinator.async_check_entity_state_change(event)

            mock_refresh.assert_called_once()
            mock_notify.assert_called_once()


class TestRoomCoordinatorSensorValueUpdates:
    """Tests for RoomCoordinator sensor value update methods."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry with sensor entities."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {
            "cloud_entity": "sensor.cloud_coverage",
            "presence_entity": "binary_sensor.presence",
            "weather_entity": "weather.home",
            "weather_state": ["sunny", "clear"],
        }
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    @pytest.mark.asyncio
    async def test_update_cloud_value_valid(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_cloud_value with valid cloud value."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="75.5",
        ):
            await room_coordinator._update_cloud_value(mock_config_entry.options)

            assert room_coordinator._last_known["cloud"] == 75.5
            assert room_coordinator._sensor_available["cloud"] is True

    @pytest.mark.asyncio
    async def test_update_cloud_value_unavailable(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_cloud_value when sensor unavailable."""
        # First set a known value
        room_coordinator._last_known["cloud"] = 50.0

        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value=None,
        ):
            await room_coordinator._update_cloud_value(mock_config_entry.options)

            # Should keep last known value
            assert room_coordinator._last_known["cloud"] == 50.0
            assert room_coordinator._sensor_available["cloud"] is False

    @pytest.mark.asyncio
    async def test_update_cloud_value_invalid(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_cloud_value with invalid (non-numeric) value."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="not_a_number",
        ):
            await room_coordinator._update_cloud_value(mock_config_entry.options)

            # Should mark as unavailable
            assert room_coordinator._sensor_available["cloud"] is False

    @pytest.mark.asyncio
    async def test_update_presence_binary_sensor_on(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_presence_value with binary_sensor entity 'on'."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="on",
        ):
            await room_coordinator._update_presence_value(mock_config_entry.options)

            assert room_coordinator._last_known["is_presence"] is True
            assert room_coordinator._sensor_available["is_presence"] is True

    @pytest.mark.asyncio
    async def test_update_presence_binary_sensor_off(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_presence_value with binary_sensor entity 'off'."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="off",
        ):
            await room_coordinator._update_presence_value(mock_config_entry.options)

            assert room_coordinator._last_known["is_presence"] is False
            assert room_coordinator._sensor_available["is_presence"] is True

    @pytest.mark.asyncio
    async def test_update_presence_device_tracker_home(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test _update_presence_value with device_tracker entity 'home'."""
        options = {"presence_entity": "device_tracker.person"}

        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="home",
        ):
            await room_coordinator._update_presence_value(options)

            assert room_coordinator._last_known["is_presence"] is True
            assert room_coordinator._sensor_available["is_presence"] is True

    @pytest.mark.asyncio
    async def test_update_presence_device_tracker_away(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test _update_presence_value with device_tracker entity 'not_home'."""
        options = {"presence_entity": "device_tracker.person"}

        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="not_home",
        ):
            await room_coordinator._update_presence_value(options)

            assert room_coordinator._last_known["is_presence"] is False
            assert room_coordinator._sensor_available["is_presence"] is True

    @pytest.mark.asyncio
    async def test_update_presence_unavailable(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_presence_value when sensor unavailable."""
        room_coordinator._last_known["is_presence"] = True

        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value=None,
        ):
            await room_coordinator._update_presence_value(mock_config_entry.options)

            # Should keep last known value
            assert room_coordinator._last_known["is_presence"] is True
            assert room_coordinator._sensor_available["is_presence"] is False

    @pytest.mark.asyncio
    async def test_update_weather_matching_condition(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_weather_value with matching weather condition."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="sunny",
        ):
            await room_coordinator._update_weather_value(mock_config_entry.options)

            assert room_coordinator._last_known["has_direct_sun"] is True
            assert room_coordinator._sensor_available["has_direct_sun"] is True

    @pytest.mark.asyncio
    async def test_update_weather_no_match(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_weather_value with non-matching weather condition."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value="cloudy",
        ):
            await room_coordinator._update_weather_value(mock_config_entry.options)

            assert room_coordinator._last_known["has_direct_sun"] is False
            assert room_coordinator._sensor_available["has_direct_sun"] is True

    @pytest.mark.asyncio
    async def test_update_weather_unavailable(
        self, room_coordinator: RoomCoordinator, mock_config_entry: MagicMock
    ) -> None:
        """Test _update_weather_value when sensor unavailable."""
        room_coordinator._last_known["has_direct_sun"] = True

        with patch(
            "custom_components.adaptive_cover.room_coordinator.get_safe_state",
            return_value=None,
        ):
            await room_coordinator._update_weather_value(mock_config_entry.options)

            # Should keep last known value
            assert room_coordinator._last_known["has_direct_sun"] is True
            assert room_coordinator._sensor_available["has_direct_sun"] is False

    @pytest.mark.asyncio
    async def test_update_data_returns_room_data(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test _async_update_data returns proper RoomData."""
        with (
            patch.object(
                room_coordinator, "_update_cloud_value", new_callable=AsyncMock
            ),
            patch.object(
                room_coordinator, "_update_presence_value", new_callable=AsyncMock
            ),
            patch.object(
                room_coordinator, "_update_weather_value", new_callable=AsyncMock
            ),
        ):
            result = await room_coordinator._async_update_data()

            assert isinstance(result, RoomData)
            assert result.control_mode == room_coordinator.control_mode


class TestRoomCoordinatorMidnightReset:
    """Tests for RoomCoordinator midnight reset functionality."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {"reset_at_midnight": True}
        return entry

    @pytest.fixture
    def room_coordinator(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> RoomCoordinator:
        """Create a RoomCoordinator instance."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, mock_config_entry)
            return coordinator

    def test_setup_midnight_reset_enabled(
        self, room_coordinator: RoomCoordinator
    ) -> None:
        """Test setup_midnight_reset creates listener when enabled."""
        with patch(
            "custom_components.adaptive_cover.room_coordinator.async_track_time_change"
        ) as mock_track:
            mock_track.return_value = MagicMock()
            room_coordinator.setup_midnight_reset()

            mock_track.assert_called_once()
            assert room_coordinator._midnight_unsub is not None

    def test_setup_midnight_reset_disabled(self, hass: HomeAssistant) -> None:
        """Test setup_midnight_reset does not create listener when disabled."""
        entry = MagicMock()
        entry.entry_id = "test_room_123"
        entry.data = {"name": "Living Room"}
        entry.options = {"reset_at_midnight": False}

        with patch(
            "custom_components.adaptive_cover.room_coordinator.Store"
        ) as mock_store:
            mock_store.return_value.async_load = AsyncMock(return_value=None)
            mock_store.return_value.async_save = AsyncMock()
            coordinator = RoomCoordinator(hass, entry)

        with patch(
            "custom_components.adaptive_cover.room_coordinator.async_track_time_change"
        ) as mock_track:
            coordinator.setup_midnight_reset()

            mock_track.assert_not_called()

    def test_midnight_reset_callback(
        self, room_coordinator: RoomCoordinator, hass: HomeAssistant
    ) -> None:
        """Test _async_midnight_reset resets control mode to AUTO."""
        from datetime import datetime

        room_coordinator.control_mode = CONTROL_MODE_DISABLED
        assert room_coordinator.control_mode == CONTROL_MODE_DISABLED

        # Simulate midnight reset callback
        room_coordinator._async_midnight_reset(datetime.now())

        assert room_coordinator.control_mode == CONTROL_MODE_AUTO
