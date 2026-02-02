"""Tests for cover state strategy classes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch


from custom_components.adaptive_cover.calculation import (
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    ClimateCoverData,
    ClimateCoverState,
    NormalCoverState,
)

if TYPE_CHECKING:
    from custom_components.adaptive_cover.config_context_adapter import (
        ConfigContextAdapter,
    )


def create_vertical_cover(
    mock_hass: MagicMock,
    mock_logger: ConfigContextAdapter,
    sol_azi: float = 180.0,
    sol_elev: float = 45.0,
    h_def: int = 60,
    max_pos: int = 100,
    min_pos: int = 0,
    max_pos_bool: bool = False,
    min_pos_bool: bool = False,
) -> AdaptiveVerticalCover:
    """Create a vertical cover with common defaults."""
    with patch("custom_components.adaptive_cover.calculation.SunData") as mock_sun_data:
        # Use future dates to avoid sunset_valid returning True
        mock_sun_data.return_value.sunset.return_value = datetime(2099, 6, 21, 21, 0, 0)
        mock_sun_data.return_value.sunrise.return_value = datetime(2099, 6, 21, 5, 0, 0)

        return AdaptiveVerticalCover(
            hass=mock_hass,
            logger=mock_logger,
            sol_azi=sol_azi,
            sol_elev=sol_elev,
            sunset_pos=0,
            sunset_off=30,
            sunrise_off=30,
            timezone="Europe/Amsterdam",
            fov_left=90,
            fov_right=90,
            win_azi=180,
            h_def=h_def,
            max_pos=max_pos,
            min_pos=min_pos,
            max_pos_bool=max_pos_bool,
            min_pos_bool=min_pos_bool,
            blind_spot_left=None,
            blind_spot_right=None,
            blind_spot_elevation=None,
            blind_spot_on=False,
            min_elevation=None,
            max_elevation=None,
            distance=0.5,
            h_win=2.1,
            cover_bottom=0.0,
            shaded_area_height=0.0,
        )


def create_tilt_cover(
    mock_hass: MagicMock,
    mock_logger: ConfigContextAdapter,
    sol_azi: float = 180.0,
    sol_elev: float = 45.0,
    h_def: int = 50,
    mode: str = "mode1",
) -> AdaptiveTiltCover:
    """Create a tilt cover with common defaults."""
    with patch("custom_components.adaptive_cover.calculation.SunData") as mock_sun_data:
        # Use future dates to avoid sunset_valid returning True
        mock_sun_data.return_value.sunset.return_value = datetime(2099, 6, 21, 21, 0, 0)
        mock_sun_data.return_value.sunrise.return_value = datetime(2099, 6, 21, 5, 0, 0)

        return AdaptiveTiltCover(
            hass=mock_hass,
            logger=mock_logger,
            sol_azi=sol_azi,
            sol_elev=sol_elev,
            sunset_pos=0,
            sunset_off=30,
            sunrise_off=30,
            timezone="Europe/Amsterdam",
            fov_left=90,
            fov_right=90,
            win_azi=180,
            h_def=h_def,
            max_pos=100,
            min_pos=0,
            max_pos_bool=False,
            min_pos_bool=False,
            blind_spot_left=None,
            blind_spot_right=None,
            blind_spot_elevation=None,
            blind_spot_on=False,
            min_elevation=None,
            max_elevation=None,
            slat_distance=0.025,
            depth=0.02,
            mode=mode,
        )


class TestNormalCoverState:
    """Tests for NormalCoverState class."""

    def test_get_state_sun_valid_no_weather(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state when sun is valid and no weather check."""
        cover = create_vertical_cover(mock_hass, mock_logger)

        # Mock direct_sun_valid to return True
        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=30):
                state = NormalCoverState(cover)
                result = state.get_state(has_direct_sun=None, cloud_override=None)

                # Should use calculated percentage
                assert result == 30

    def test_get_state_sun_valid_weather_sunny(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state when sun valid and weather allows sun."""
        cover = create_vertical_cover(mock_hass, mock_logger)

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=40):
                state = NormalCoverState(cover)
                result = state.get_state(has_direct_sun=True, cloud_override=False)

                assert result == 40

    def test_get_state_sun_valid_weather_cloudy(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state when sun valid but weather doesn't allow sun."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = True
            mock_sunset.return_value = False  # Before sunset
            state = NormalCoverState(cover)
            result = state.get_state(has_direct_sun=False, cloud_override=None)

            # Should use default value (h_def)
            assert result == 60

    def test_get_state_sun_valid_cloud_override(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state when sun valid but cloud override blocks sun."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = True
            mock_sunset.return_value = False  # Before sunset
            state = NormalCoverState(cover)
            result = state.get_state(has_direct_sun=True, cloud_override=True)

            # Should use default value (cloud blocks sun)
            assert result == 60

    def test_get_state_sun_not_valid(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state when sun is not in valid position."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=70)

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = False
            mock_sunset.return_value = False  # Before sunset
            state = NormalCoverState(cover)
            result = state.get_state(has_direct_sun=True)

            # Should use default value
            assert result == 70

    def test_get_state_applies_max_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that max position limit is applied."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, max_pos=50, max_pos_bool=False
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=70):
                state = NormalCoverState(cover)
                result = state.get_state()

                # Should be limited to max_pos
                assert result == 50

    def test_get_state_applies_min_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that min position limit is applied."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, min_pos=30, min_pos_bool=False
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=10):
                state = NormalCoverState(cover)
                result = state.get_state()

                # Should be raised to min_pos
                assert result == 30

    def test_get_state_clips_to_valid_range(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that result is clipped to 0-100 range."""
        cover = create_vertical_cover(mock_hass, mock_logger)

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            # Return value outside 0-100 range
            with patch.object(cover, "calculate_percentage", return_value=150):
                state = NormalCoverState(cover)
                result = state.get_state()

                # Should be clipped to 100
                assert result == 100


class TestClimateCoverData:
    """Tests for ClimateCoverData class."""

    def _create_climate_data(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        **kwargs,
    ) -> ClimateCoverData:
        """Create ClimateCoverData with defaults."""
        defaults = {
            "hass": mock_hass,
            "logger": mock_logger,
            "temp_entity": None,
            "temp_low": 18.0,
            "temp_high": 24.0,
            "presence_entity": None,
            "weather_entity": None,
            "weather_condition": [],
            "blind_type": "cover_blind",
            "transparent_blind": False,
            "lux_entity": None,
            "irradiance_entity": None,
            "lux_threshold": None,
            "irradiance_threshold": None,
            "_use_lux": False,
            "_use_irradiance": False,
            "cloud_entity": None,
            "cloud_threshold": None,
            "_use_cloud": False,
        }
        defaults.update(kwargs)
        return ClimateCoverData(**defaults)

    def test_is_presence_no_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence returns True when no presence entity configured."""
        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.is_presence is True

    def test_is_presence_binary_sensor_on(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence with binary_sensor that is on."""
        mock_state = MagicMock()
        mock_state.state = "on"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity="binary_sensor.presence",
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.is_presence is True

    def test_is_presence_binary_sensor_off(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence with binary_sensor that is off."""
        mock_state = MagicMock()
        mock_state.state = "off"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity="binary_sensor.presence",
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.is_presence is False

    def test_is_presence_device_tracker_home(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence with device_tracker at home."""
        mock_state = MagicMock()
        mock_state.state = "home"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity="device_tracker.phone",
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.is_presence is True

    def test_is_winter_below_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_winter when temperature is below threshold."""
        mock_state = MagicMock()
        mock_state.state = "16.0"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity="sensor.temperature",
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.is_winter is True

    def test_is_summer_above_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_summer when temperature is above threshold."""
        mock_state = MagicMock()
        mock_state.state = "26.0"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity="sensor.temperature",
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.is_summer is True

    def test_has_direct_sun_no_weather_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun returns True when no weather entity."""
        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.has_direct_sun is True

    def test_has_direct_sun_sunny_weather(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun with sunny weather."""
        mock_state = MagicMock()
        mock_state.state = "sunny"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity="weather.home",
            weather_condition=["sunny", "partlycloudy"],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.has_direct_sun is True

    def test_has_direct_sun_rainy_weather(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun with rainy weather."""
        mock_state = MagicMock()
        mock_state.state = "rainy"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity="weather.home",
            weather_condition=["sunny", "partlycloudy"],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.has_direct_sun is False

    def test_lux_below_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test lux returns True when below threshold (no actual sun)."""
        mock_state = MagicMock()
        mock_state.state = "500"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity="sensor.lux",
            irradiance_entity=None,
            lux_threshold=1000,
            irradiance_threshold=None,
            _use_lux=True,
            _use_irradiance=False,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
        )

        assert climate_data.lux is True

    def test_cloud_above_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test cloud returns True when above threshold (too cloudy)."""
        mock_state = MagicMock()
        mock_state.state = "80"
        mock_hass.states.get.return_value = mock_state

        climate_data = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=18.0,
            temp_high=24.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity=None,
            lux_threshold=None,
            irradiance_threshold=None,
            _use_lux=False,
            _use_irradiance=False,
            cloud_entity="sensor.cloud_coverage",
            cloud_threshold=50,
            _use_cloud=True,
        )

        assert climate_data.cloud is True

    def test_irradiance_above_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test irradiance returns False when above threshold (actual sun)."""
        mock_state = MagicMock()
        mock_state.state = "600"
        mock_hass.states.get.return_value = mock_state

        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            irradiance_entity="sensor.irradiance",
            irradiance_threshold=400,
            _use_irradiance=True,
        )

        # irradiance returns True if BELOW threshold (no sun)
        # 600 > 400 so returns False (actual sun)
        assert climate_data.irradiance is False

    def test_irradiance_below_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test irradiance returns True when below threshold (no actual sun)."""
        mock_state = MagicMock()
        mock_state.state = "200"
        mock_hass.states.get.return_value = mock_state

        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            irradiance_entity="sensor.irradiance",
            irradiance_threshold=400,
            _use_irradiance=True,
        )

        # 200 < 400 so returns True (no actual sun)
        assert climate_data.irradiance is True

    def test_lux_no_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test lux returns False when no entity configured."""
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            lux_entity=None,
            _use_lux=False,
        )

        assert climate_data.lux is False

    def test_irradiance_no_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test irradiance returns False when no entity configured."""
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            irradiance_entity=None,
            _use_irradiance=False,
        )

        assert climate_data.irradiance is False

    def test_cloud_no_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test cloud returns False when no entity configured."""
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            cloud_entity=None,
            _use_cloud=False,
        )

        assert climate_data.cloud is False

    def test_is_winter_no_temp_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_winter returns False when no temp entity configured."""
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            temp_entity=None,
        )

        assert climate_data.is_winter is False

    def test_is_summer_no_temp_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_summer returns False when no temp entity configured."""
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            temp_entity=None,
        )

        assert climate_data.is_summer is False


class TestClimateCoverState:
    """Tests for ClimateCoverState class."""

    def _create_climate_data(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        is_presence: bool = True,
        is_winter: bool = False,
        is_summer: bool = False,
        has_direct_sun: bool = True,
        blind_type: str = "cover_blind",
    ) -> ClimateCoverData:
        """Create a mock ClimateCoverData with controlled properties."""
        climate_data = MagicMock(spec=ClimateCoverData)
        climate_data.is_presence = is_presence
        climate_data.is_winter = is_winter
        climate_data.is_summer = is_summer
        climate_data.has_direct_sun = has_direct_sun
        climate_data.blind_type = blind_type
        climate_data.lux = False
        climate_data.irradiance = False
        climate_data.cloud = False
        climate_data.logger = mock_logger
        return climate_data

    def test_normal_type_with_presence_sun_valid(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test normal cover with presence and valid sun returns calculated position."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = self._create_climate_data(
            mock_hass, mock_logger, is_presence=True, has_direct_sun=True
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=35):
                state = ClimateCoverState(cover, climate_data)
                result = state.normal_type_cover()

                # With presence + sun valid, should use calculated position
                assert result == 35

    def test_normal_type_with_presence_no_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test normal cover with presence but no sun returns default."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = self._create_climate_data(
            mock_hass, mock_logger, is_presence=True, has_direct_sun=False
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = True  # Sun geometry is valid
            mock_sunset.return_value = False  # Before sunset
            state = ClimateCoverState(cover, climate_data)
            result = state.normal_type_cover()

            # Weather says no sun, so use default
            assert result == 60

    def test_normal_type_without_presence_summer(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test normal cover without presence in summer closes to block heat."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            is_presence=False,
            is_summer=True,
            has_direct_sun=True,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            state = ClimateCoverState(cover, climate_data)
            result = state.normal_type_cover()

            # No presence + summer + sun = close (0) to block heat
            assert result == 0

    def test_normal_type_without_presence_winter(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test normal cover without presence in winter opens to let heat in."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            is_presence=False,
            is_winter=True,
            has_direct_sun=True,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            state = ClimateCoverState(cover, climate_data)
            result = state.normal_type_cover()

            # No presence + winter + sun = open (100) to let heat in
            assert result == 100

    def test_get_state_tilt_cover(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state dispatches to tilt_state for tilt covers."""
        cover = create_tilt_cover(mock_hass, mock_logger, h_def=50)
        climate_data = self._create_climate_data(
            mock_hass,
            mock_logger,
            is_presence=True,
            has_direct_sun=True,
            blind_type="cover_tilt",
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=45):
                state = ClimateCoverState(cover, climate_data)
                result = state.get_state()

                # Should return a valid percentage
                assert 0 <= result <= 100

    def test_get_state_applies_max_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state applies max position limit."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, max_pos=50, max_pos_bool=False
        )
        climate_data = self._create_climate_data(
            mock_hass, mock_logger, is_presence=True, has_direct_sun=True
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=70):
                state = ClimateCoverState(cover, climate_data)
                result = state.get_state()

                # Should be limited to max_pos
                assert result == 50

    def test_get_state_applies_min_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test get_state applies min position limit."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, min_pos=25, min_pos_bool=False
        )
        climate_data = self._create_climate_data(
            mock_hass, mock_logger, is_presence=True, has_direct_sun=True
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=10):
                state = ClimateCoverState(cover, climate_data)
                result = state.get_state()

                # Should be raised to min_pos
                assert result == 25

    def test_presence_unavailable_assumes_occupied(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that unavailable presence entity assumes occupied for safety."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = self._create_climate_data(
            mock_hass, mock_logger, is_presence=True, has_direct_sun=True
        )
        # Simulate presence entity returning None (unavailable)
        climate_data.is_presence = None

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=40):
                state = ClimateCoverState(cover, climate_data)
                result = state.normal_type_cover()

                # Should treat as occupied and use calculated position
                assert result == 40
