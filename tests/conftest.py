"""Shared test fixtures for Adaptive Cover tests."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_cover.config_context_adapter import ConfigContextAdapter
from custom_components.adaptive_cover.const import (
    CONF_AZIMUTH,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_DEFAULT_HEIGHT,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
    CONF_ENTRY_TYPE,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MIN_POSITION,
    CONF_SENSOR_TYPE,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    EntryType,
    SensorType,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_logger() -> ConfigContextAdapter:
    """Create a mock logger for testing."""
    logger = ConfigContextAdapter(logging.getLogger("test"))
    logger.set_config_name("test_cover")
    return logger


@pytest.fixture
def mock_sun_data() -> MagicMock:
    """Create a mock SunData object."""
    sun_data = MagicMock()
    sun_data.sunset.return_value = datetime(2024, 6, 21, 21, 0, 0)
    sun_data.sunrise.return_value = datetime(2024, 6, 21, 5, 0, 0)
    return sun_data


@pytest.fixture
def vertical_cover_params() -> dict[str, Any]:
    """Return base parameters for AdaptiveVerticalCover."""
    return {
        "sol_azi": 180.0,  # Sun from south
        "sol_elev": 45.0,  # 45 degree elevation
        "sunset_pos": 0,
        "sunset_off": 30,
        "sunrise_off": 30,
        "timezone": "Europe/Amsterdam",
        "fov_left": 90,
        "fov_right": 90,
        "win_azi": 180,  # South-facing window
        "h_def": 60,  # Default position
        "max_pos": 100,
        "min_pos": 0,
        "max_pos_bool": False,
        "min_pos_bool": False,
        "blind_spot_left": None,
        "blind_spot_right": None,
        "blind_spot_elevation": None,
        "blind_spot_on": False,
        "min_elevation": None,
        "max_elevation": None,
        "distance": 0.5,
        "h_win": 2.1,
        "cover_bottom": 0.0,
        "shaded_area_height": 0.0,
    }


@pytest.fixture
def horizontal_cover_params(vertical_cover_params: dict[str, Any]) -> dict[str, Any]:
    """Return base parameters for AdaptiveHorizontalCover."""
    return {
        **vertical_cover_params,
        "awn_length": 2.1,
        "awn_angle": 0.0,
    }


@pytest.fixture
def tilt_cover_params() -> dict[str, Any]:
    """Return base parameters for AdaptiveTiltCover."""
    return {
        "sol_azi": 180.0,
        "sol_elev": 45.0,
        "sunset_pos": 0,
        "sunset_off": 30,
        "sunrise_off": 30,
        "timezone": "Europe/Amsterdam",
        "fov_left": 90,
        "fov_right": 90,
        "win_azi": 180,
        "h_def": 50,
        "max_pos": 100,
        "min_pos": 0,
        "max_pos_bool": False,
        "min_pos_bool": False,
        "blind_spot_left": None,
        "blind_spot_right": None,
        "blind_spot_elevation": None,
        "blind_spot_on": False,
        "min_elevation": None,
        "max_elevation": None,
        "slat_distance": 0.025,
        "depth": 0.02,
        "mode": "mode1",
    }


@pytest.fixture
def mock_config_entry_data() -> dict[str, Any]:
    """Mock config entry data for a vertical cover."""
    return {
        CONF_ENTRY_TYPE: EntryType.COVER,
        CONF_SENSOR_TYPE: SensorType.BLIND,
        CONF_AZIMUTH: 180,
        CONF_HEIGHT_WIN: 2.1,
        CONF_DISTANCE: 0.5,
        CONF_FOV_LEFT: 90,
        CONF_FOV_RIGHT: 90,
        CONF_DEFAULT_HEIGHT: 60,
        CONF_MAX_POSITION: 100,
        CONF_MIN_POSITION: 0,
        CONF_ENABLE_MAX_POSITION: False,
        CONF_ENABLE_MIN_POSITION: False,
        CONF_SUNSET_POS: 0,
        CONF_SUNSET_OFFSET: 30,
        CONF_SUNRISE_OFFSET: 30,
        CONF_ENABLE_BLIND_SPOT: False,
        CONF_BLIND_SPOT_LEFT: None,
        CONF_BLIND_SPOT_RIGHT: None,
        CONF_BLIND_SPOT_ELEVATION: None,
        CONF_MIN_ELEVATION: None,
        CONF_MAX_ELEVATION: None,
    }


@pytest.fixture
def mock_tilt_config_entry_data() -> dict[str, Any]:
    """Mock config entry data for a tilt cover."""
    return {
        CONF_ENTRY_TYPE: EntryType.COVER,
        CONF_SENSOR_TYPE: SensorType.TILT,
        CONF_AZIMUTH: 180,
        CONF_FOV_LEFT: 90,
        CONF_FOV_RIGHT: 90,
        CONF_DEFAULT_HEIGHT: 50,
        CONF_MAX_POSITION: 100,
        CONF_MIN_POSITION: 0,
        CONF_ENABLE_MAX_POSITION: False,
        CONF_ENABLE_MIN_POSITION: False,
        CONF_SUNSET_POS: 0,
        CONF_SUNSET_OFFSET: 30,
        CONF_SUNRISE_OFFSET: 30,
        CONF_ENABLE_BLIND_SPOT: False,
        CONF_BLIND_SPOT_LEFT: None,
        CONF_BLIND_SPOT_RIGHT: None,
        CONF_BLIND_SPOT_ELEVATION: None,
        CONF_MIN_ELEVATION: None,
        CONF_MAX_ELEVATION: None,
        CONF_TILT_DEPTH: 0.02,
        CONF_TILT_DISTANCE: 0.025,
        CONF_TILT_MODE: "mode1",
    }


@pytest.fixture
def mock_room_config_entry_data() -> dict[str, Any]:
    """Mock config entry data for a room."""
    return {
        CONF_ENTRY_TYPE: EntryType.ROOM,
    }


@pytest.fixture
def mock_hass_state() -> MagicMock:
    """Create a mock Home Assistant state object."""
    state = MagicMock()
    state.state = "20.5"
    state.last_updated = datetime.now()
    return state


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    return hass
