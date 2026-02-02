"""Tests for helper functions."""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import pandas as pd
from freezegun import freeze_time

from custom_components.adaptive_cover.helpers import (
    check_time_passed,
    dt_check_time_passed,
    get_datetime_from_str,
    get_domain,
    get_last_updated,
    get_safe_state,
    get_timedelta_str,
)


class TestGetSafeState:
    """Tests for get_safe_state function."""

    def test_returns_state_value_when_available(self, mock_hass: MagicMock) -> None:
        """Test that valid state is returned."""
        mock_state = MagicMock()
        mock_state.state = "20.5"
        mock_hass.states.get.return_value = mock_state

        result = get_safe_state(mock_hass, "sensor.temperature")

        assert result == "20.5"
        mock_hass.states.get.assert_called_once_with("sensor.temperature")

    def test_returns_none_when_entity_not_found(self, mock_hass: MagicMock) -> None:
        """Test that None is returned when entity doesn't exist."""
        mock_hass.states.get.return_value = None

        result = get_safe_state(mock_hass, "sensor.nonexistent")

        assert result is None

    def test_returns_none_when_state_unknown(self, mock_hass: MagicMock) -> None:
        """Test that None is returned for unknown state."""
        mock_state = MagicMock()
        mock_state.state = "unknown"
        mock_hass.states.get.return_value = mock_state

        result = get_safe_state(mock_hass, "sensor.temperature")

        assert result is None

    def test_returns_none_when_state_unavailable(self, mock_hass: MagicMock) -> None:
        """Test that None is returned for unavailable state."""
        mock_state = MagicMock()
        mock_state.state = "unavailable"
        mock_hass.states.get.return_value = mock_state

        result = get_safe_state(mock_hass, "sensor.temperature")

        assert result is None

    def test_returns_on_off_states(self, mock_hass: MagicMock) -> None:
        """Test that on/off states are returned correctly."""
        mock_state = MagicMock()
        mock_state.state = "on"
        mock_hass.states.get.return_value = mock_state

        assert get_safe_state(mock_hass, "binary_sensor.presence") == "on"

        mock_state.state = "off"
        assert get_safe_state(mock_hass, "binary_sensor.presence") == "off"


class TestGetDomain:
    """Tests for get_domain function."""

    def test_extracts_sensor_domain(self) -> None:
        """Test extraction of sensor domain."""
        assert get_domain("sensor.temperature") == "sensor"

    def test_extracts_binary_sensor_domain(self) -> None:
        """Test extraction of binary_sensor domain."""
        assert get_domain("binary_sensor.motion") == "binary_sensor"

    def test_extracts_cover_domain(self) -> None:
        """Test extraction of cover domain."""
        assert get_domain("cover.living_room") == "cover"

    def test_extracts_climate_domain(self) -> None:
        """Test extraction of climate domain."""
        assert get_domain("climate.thermostat") == "climate"

    def test_extracts_device_tracker_domain(self) -> None:
        """Test extraction of device_tracker domain."""
        assert get_domain("device_tracker.phone") == "device_tracker"

    def test_returns_none_for_none_input(self) -> None:
        """Test that None input returns None."""
        assert get_domain(None) is None


class TestGetTimedeltaStr:
    """Tests for get_timedelta_str function."""

    def test_converts_minutes_string(self) -> None:
        """Test conversion of minutes string."""
        result = get_timedelta_str("30min")
        assert result == pd.Timedelta(minutes=30)

    def test_converts_hours_string(self) -> None:
        """Test conversion of hours string."""
        result = get_timedelta_str("2h")
        assert result == pd.Timedelta(hours=2)

    def test_converts_seconds_string(self) -> None:
        """Test conversion of seconds string."""
        result = get_timedelta_str("90s")
        assert result == pd.Timedelta(seconds=90)

    def test_converts_complex_timedelta(self) -> None:
        """Test conversion of complex timedelta string."""
        result = get_timedelta_str("1h30min")
        assert result == pd.Timedelta(hours=1, minutes=30)

    def test_returns_none_for_none_input(self) -> None:
        """Test that None input returns None."""
        assert get_timedelta_str(None) is None


class TestGetDatetimeFromStr:
    """Tests for get_datetime_from_str function."""

    def test_parses_iso_format(self) -> None:
        """Test parsing ISO format datetime."""
        result = get_datetime_from_str("2024-06-21T14:30:00")
        assert result == dt.datetime(2024, 6, 21, 14, 30, 0)

    def test_parses_date_with_time(self) -> None:
        """Test parsing date with time."""
        result = get_datetime_from_str("2024-06-21 14:30:00")
        assert result == dt.datetime(2024, 6, 21, 14, 30, 0)

    def test_parses_date_only(self) -> None:
        """Test parsing date only."""
        result = get_datetime_from_str("2024-06-21")
        assert result == dt.datetime(2024, 6, 21, 0, 0, 0)

    def test_ignores_timezone(self) -> None:
        """Test that timezone is ignored."""
        result = get_datetime_from_str("2024-06-21T14:30:00+02:00")
        assert result == dt.datetime(2024, 6, 21, 14, 30, 0)

    def test_returns_none_for_none_input(self) -> None:
        """Test that None input returns None."""
        assert get_datetime_from_str(None) is None


class TestGetLastUpdated:
    """Tests for get_last_updated function."""

    def test_returns_last_updated_time(self, mock_hass: MagicMock) -> None:
        """Test that last_updated attribute is returned."""
        expected_time = dt.datetime(2024, 6, 21, 14, 30, 0)
        mock_state = MagicMock()
        mock_state.last_updated = expected_time
        mock_hass.states.get.return_value = mock_state

        result = get_last_updated("sensor.temperature", mock_hass)

        assert result == expected_time

    def test_returns_none_when_entity_not_found(self, mock_hass: MagicMock) -> None:
        """Test that None is returned when entity doesn't exist."""
        mock_hass.states.get.return_value = None

        result = get_last_updated("sensor.nonexistent", mock_hass)

        assert result is None

    def test_returns_none_for_none_entity_id(self, mock_hass: MagicMock) -> None:
        """Test that None entity_id returns None."""
        result = get_last_updated(None, mock_hass)

        assert result is None


class TestCheckTimePassed:
    """Tests for check_time_passed function."""

    @freeze_time("2024-06-21 14:30:00")
    def test_returns_true_when_time_passed(self) -> None:
        """Test returns True when time has passed."""
        past_time = dt.datetime(2024, 6, 21, 10, 0, 0)
        assert check_time_passed(past_time) is True

    @freeze_time("2024-06-21 14:30:00")
    def test_returns_false_when_time_not_passed(self) -> None:
        """Test returns False when time has not passed."""
        future_time = dt.datetime(2024, 6, 21, 16, 0, 0)
        assert check_time_passed(future_time) is False

    @freeze_time("2024-06-21 14:30:00")
    def test_returns_true_at_exact_time(self) -> None:
        """Test returns True at exact time."""
        exact_time = dt.datetime(2024, 6, 21, 14, 30, 0)
        assert check_time_passed(exact_time) is True


class TestDtCheckTimePassed:
    """Tests for dt_check_time_passed function."""

    @freeze_time("2024-06-21 14:30:00", tz_offset=0)
    def test_returns_true_when_time_passed_today(self) -> None:
        """Test returns True when time has passed today."""
        past_time = dt.datetime(2024, 6, 21, 10, 0, 0, tzinfo=dt.UTC)
        assert dt_check_time_passed(past_time) is True

    @freeze_time("2024-06-21 14:30:00", tz_offset=0)
    def test_returns_false_when_time_not_passed_today(self) -> None:
        """Test returns False when time has not passed today."""
        future_time = dt.datetime(2024, 6, 21, 16, 0, 0, tzinfo=dt.UTC)
        assert dt_check_time_passed(future_time) is False

    @freeze_time("2024-06-21 14:30:00", tz_offset=0)
    def test_returns_true_for_past_date(self) -> None:
        """Test returns True for past date (different day)."""
        past_date = dt.datetime(2024, 6, 20, 16, 0, 0, tzinfo=dt.UTC)
        assert dt_check_time_passed(past_date) is True
