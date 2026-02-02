"""Integration tests for SunData class."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pandas as pd

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestSunData:
    """Tests for SunData class."""

    def test_times_returns_datetime_index(self, hass: HomeAssistant) -> None:
        """Test that times property returns a DatetimeIndex."""
        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            mock_astral.return_value = (mock_location, 0)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            times = sun_data.times

            assert isinstance(times, pd.DatetimeIndex)
            # Should cover at least one full day with 5-minute intervals
            # 24 hours * 60 minutes / 5 = 288 intervals
            assert len(times) >= 288

    def test_times_has_5_minute_frequency(self, hass: HomeAssistant) -> None:
        """Test that times are spaced 5 minutes apart."""
        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            mock_astral.return_value = (mock_location, 0)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            times = sun_data.times

            # Check frequency between consecutive times
            if len(times) >= 2:
                diff = times[1] - times[0]
                assert diff == pd.Timedelta(minutes=5)

    def test_solar_azimuth_returns_list(self, hass: HomeAssistant) -> None:
        """Test that solar_azimuth returns a list of values."""
        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            mock_location.solar_azimuth.return_value = 180.0
            mock_astral.return_value = (mock_location, 0)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            azimuths = sun_data.solar_azimuth

            assert isinstance(azimuths, list)
            assert len(azimuths) == len(sun_data.times)
            assert all(isinstance(a, float) for a in azimuths)

    def test_solar_elevation_returns_list(self, hass: HomeAssistant) -> None:
        """Test that solar_elevation returns a list of values."""
        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            mock_location.solar_elevation.return_value = 45.0
            mock_astral.return_value = (mock_location, 0)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            elevations = sun_data.solar_elevation

            assert isinstance(elevations, list)
            assert len(elevations) == len(sun_data.times)
            assert all(isinstance(e, float) for e in elevations)

    def test_sunset_returns_datetime(self, hass: HomeAssistant) -> None:
        """Test that sunset returns a datetime."""
        from datetime import datetime

        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            expected_sunset = datetime(2024, 6, 21, 21, 30, 0)
            mock_location.sunset.return_value = expected_sunset
            mock_astral.return_value = (mock_location, 0)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            sunset = sun_data.sunset()

            assert sunset == expected_sunset
            mock_location.sunset.assert_called_once_with(date.today(), local=False)

    def test_sunrise_returns_datetime(self, hass: HomeAssistant) -> None:
        """Test that sunrise returns a datetime."""
        from datetime import datetime

        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            expected_sunrise = datetime(2024, 6, 21, 5, 15, 0)
            mock_location.sunrise.return_value = expected_sunrise
            mock_astral.return_value = (mock_location, 0)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            sunrise = sun_data.sunrise()

            assert sunrise == expected_sunrise
            mock_location.sunrise.assert_called_once_with(date.today(), local=False)

    def test_stores_location_and_elevation(self, hass: HomeAssistant) -> None:
        """Test that location and elevation are stored."""
        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            expected_elevation = 100
            mock_astral.return_value = (mock_location, expected_elevation)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)

            assert sun_data.location is mock_location
            assert sun_data.elevation == expected_elevation
            assert sun_data.timezone == "Europe/Amsterdam"

    def test_solar_azimuth_calls_location_method_for_each_time(
        self, hass: HomeAssistant
    ) -> None:
        """Test that solar_azimuth calls location method for each time point."""
        with patch(
            "custom_components.adaptive_cover.sun.get_astral_location"
        ) as mock_astral:
            mock_location = MagicMock()
            mock_location.solar_azimuth.return_value = 180.0
            mock_astral.return_value = (mock_location, 50)

            from custom_components.adaptive_cover.sun import SunData

            sun_data = SunData("Europe/Amsterdam", hass)
            _azimuths = sun_data.solar_azimuth

            # Should be called once for each time point
            assert mock_location.solar_azimuth.call_count == len(sun_data.times)
            # Each call should include elevation parameter
            for call in mock_location.solar_azimuth.call_args_list:
                assert call[0][1] == 50  # elevation parameter
