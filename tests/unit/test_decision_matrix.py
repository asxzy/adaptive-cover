"""Comprehensive decision matrix tests for cover position calculation.

This module tests all combinations of sensor states to verify the system
outputs the correct position: calculated, default, 0 (closed), 100 (open),
or that control is disabled (no_control).

Decision Tree Summary:
    CONTROL MODE?
    ├── DISABLED → no_control (position calculated but NOT sent)
    ├── FORCE → NormalCoverState.get_state()
    │   └── direct_sun_valid?
    │       ├── Yes → calculated
    │       └── No → default
    └── AUTO → climate_mode?
        ├── False → NormalCoverState + weather/cloud toggles
        └── True → ClimateCoverState
            └── _has_actual_sun()?
                ├── No → default
                └── Yes → presence?
                    ├── True/None → calculated (comfort blocking)
                    └── False → temperature?
                        ├── Summer → 0
                        ├── Winter → 100 (or parallel for tilt mode2)
                        └── Intermediate → calculated
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch

import numpy as np
import pytest

from custom_components.adaptive_cover.calculation import (
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
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
    max_pos: int = 100,
    min_pos: int = 0,
    max_pos_bool: bool = False,
    min_pos_bool: bool = False,
) -> AdaptiveTiltCover:
    """Create a tilt cover with common defaults."""
    with patch("custom_components.adaptive_cover.calculation.SunData") as mock_sun_data:
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
            slat_distance=0.025,
            depth=0.02,
            mode=mode,
        )


# =============================================================================
# Matrix 2: FORCE Mode (Basic Sun Position) - NormalCoverState
# =============================================================================


class TestForceMode:
    """Tests for FORCE mode (basic sun position via NormalCoverState).

    In FORCE mode, the system uses NormalCoverState.get_state() without
    weather or cloud toggles. Only sun geometry matters.
    """

    def test_sun_valid_returns_calculated(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test: direct_sun_valid=True returns calculated position."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True
            with patch.object(cover, "calculate_percentage", return_value=35):
                state = NormalCoverState(cover)
                result = state.get_state()

                assert result == 35

    def test_sun_invalid_returns_default(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test: direct_sun_valid=False returns default position."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = False
            mock_sunset.return_value = False
            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 60


# =============================================================================
# Matrix 3: AUTO Mode Without Climate Mode
# =============================================================================


class TestAutoModeWithoutClimateMode:
    """Tests for AUTO mode without climate mode enabled.

    In this mode, NormalCoverState is used with weather and cloud toggles
    affecting the result.
    """

    @pytest.mark.parametrize(
        ("dsv", "has_direct_sun", "cloud_override", "expected_type"),
        [
            # Weather toggle disabled (has_direct_sun=None), cloud toggle disabled
            (True, None, None, "calculated"),
            # Weather toggle disabled, cloud below threshold
            (True, None, False, "calculated"),
            # Weather toggle disabled, cloud above threshold (too cloudy)
            (True, None, True, "default"),
            # Weather allows sun, cloud toggle disabled
            (True, True, None, "calculated"),
            # Weather blocks sun, cloud toggle disabled
            (True, False, None, "default"),
            # Weather allows sun, cloud below threshold
            (True, True, False, "calculated"),
            # Weather allows sun, cloud above threshold
            (True, True, True, "default"),
            # Weather blocks sun, cloud below threshold
            (True, False, False, "default"),
            # Weather blocks sun, cloud above threshold
            (True, False, True, "default"),
            # Geometry invalid, all other conditions pass
            (False, True, False, "default"),
            (False, None, None, "default"),
        ],
        ids=[
            "dsv=T,weather=None,cloud=None->calc",
            "dsv=T,weather=None,cloud=F->calc",
            "dsv=T,weather=None,cloud=T->default",
            "dsv=T,weather=T,cloud=None->calc",
            "dsv=T,weather=F,cloud=None->default",
            "dsv=T,weather=T,cloud=F->calc",
            "dsv=T,weather=T,cloud=T->default",
            "dsv=T,weather=F,cloud=F->default",
            "dsv=T,weather=F,cloud=T->default",
            "dsv=F,weather=T,cloud=F->default",
            "dsv=F,weather=None,cloud=None->default",
        ],
    )
    def test_weather_cloud_combinations(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        dsv: bool,
        has_direct_sun: bool | None,
        cloud_override: bool | None,
        expected_type: str,
    ) -> None:
        """Test all combinations of weather and cloud toggles."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        calculated_value = 35

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
            patch.object(cover, "calculate_percentage", return_value=calculated_value),
        ):
            mock_dsv.return_value = dsv
            mock_sunset.return_value = False

            state = NormalCoverState(cover)
            result = state.get_state(
                has_direct_sun=has_direct_sun, cloud_override=cloud_override
            )

            if expected_type == "calculated":
                assert result == calculated_value
            else:
                assert result == 60  # default


# =============================================================================
# Matrix 4: _has_actual_sun() Logic (Climate Mode)
# =============================================================================


class TestHasActualSunLogic:
    """Tests for _has_actual_sun() in ClimateCoverState.

    All conditions must pass for _has_actual_sun() to return True:
    1. direct_sun_valid = True (geometry)
    2. has_direct_sun = True (weather, None = False for safety)
    3. lux = False or None (not below threshold)
    4. irradiance = False or None (not below threshold)
    5. cloud = False or None (not above threshold)
    """

    @pytest.mark.parametrize(
        ("dsv", "has_sun", "lux", "irradiance", "cloud", "expected"),
        [
            # All conditions pass
            (True, True, False, False, False, True),
            # Sensor unavailable (None) - ignored, passes
            (True, True, False, False, None, True),
            (True, True, False, None, False, True),
            (True, True, None, False, False, True),
            (True, True, None, None, None, True),
            # Geometry blocks (overrides everything)
            (False, True, False, False, False, False),
            (False, True, True, True, True, False),
            # Weather blocks
            (True, False, False, False, False, False),
            # Weather unavailable (None) - treated as no sun for safety
            (True, None, False, False, False, False),
            # Lux below threshold (True = no sun)
            (True, True, True, False, False, False),
            # Irradiance below threshold (True = no sun)
            (True, True, False, True, False, False),
            # Cloud above threshold (True = too cloudy)
            (True, True, False, False, True, False),
            # Multiple sensors block
            (True, True, True, True, False, False),
            (True, True, True, False, True, False),
            (True, True, False, True, True, False),
            (True, True, True, True, True, False),
            # Weather + sensors block
            (True, False, True, True, True, False),
            # Geometry + weather block
            (False, False, False, False, False, False),
        ],
        ids=[
            "all_pass",
            "cloud_unavail_pass",
            "irrad_unavail_pass",
            "lux_unavail_pass",
            "all_sensors_unavail_pass",
            "geom_blocks",
            "geom_blocks_all_sensors_block",
            "weather_blocks",
            "weather_unavail_blocks",
            "lux_blocks",
            "irrad_blocks",
            "cloud_blocks",
            "lux+irrad_block",
            "lux+cloud_block",
            "irrad+cloud_block",
            "all_sensors_block",
            "weather+sensors_block",
            "geom+weather_block",
        ],
    )
    def test_has_actual_sun_combinations(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
        dsv: bool,
        has_sun: bool | None,
        lux: bool | None,
        irradiance: bool | None,
        cloud: bool | None,
        expected: bool,
    ) -> None:
        """Test _has_actual_sun() with all sensor combinations."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = climate_data_factory(
            has_direct_sun=has_sun,
            lux=lux,
            irradiance=irradiance,
            cloud=cloud,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = dsv

            state = ClimateCoverState(cover, climate_data)
            result = state._has_actual_sun()

            assert result == expected


# =============================================================================
# Matrix 5: Climate Mode Output (Vertical/Horizontal Covers)
# =============================================================================


class TestClimateModeWithPresence:
    """Tests for climate mode when presence is detected or unavailable.

    When occupied (is_presence=True or None), temperature is IGNORED.
    The system blocks sun for comfort (against glare).
    """

    @pytest.mark.parametrize(
        ("has_actual_sun", "is_presence", "is_summer", "is_winter", "expected_type"),
        [
            # No actual sun → default (regardless of presence/temp)
            (False, True, False, False, "default"),
            (False, True, True, False, "default"),
            (False, True, False, True, "default"),
            (False, None, False, False, "default"),
            # Presence True → calculated (ignore temperature)
            (True, True, False, False, "calculated"),
            (True, True, True, False, "calculated"),
            (True, True, False, True, "calculated"),
            # Presence None (unavailable) → assume occupied → calculated
            (True, None, False, False, "calculated"),
            (True, None, True, False, "calculated"),
            (True, None, False, True, "calculated"),
        ],
        ids=[
            "no_sun,pres=T,intermediate",
            "no_sun,pres=T,summer",
            "no_sun,pres=T,winter",
            "no_sun,pres=None,intermediate",
            "sun,pres=T,intermediate->calc",
            "sun,pres=T,summer->calc",
            "sun,pres=T,winter->calc",
            "sun,pres=None,intermediate->calc",
            "sun,pres=None,summer->calc",
            "sun,pres=None,winter->calc",
        ],
    )
    def test_presence_behavior(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
        has_actual_sun: bool,
        is_presence: bool | None,
        is_summer: bool,
        is_winter: bool,
        expected_type: str,
    ) -> None:
        """Test climate mode output with presence."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        calculated_value = 35

        climate_data = climate_data_factory(
            is_presence=is_presence,
            has_direct_sun=has_actual_sun,
            is_summer=is_summer,
            is_winter=is_winter,
            # Ensure sensors don't block actual sun check
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
            patch.object(cover, "calculate_percentage", return_value=calculated_value),
        ):
            mock_dsv.return_value = has_actual_sun
            mock_sunset.return_value = False

            state = ClimateCoverState(cover, climate_data)
            result = state.normal_type_cover()

            if expected_type == "calculated":
                assert result == calculated_value
            else:
                assert result == 60  # default


class TestClimateModeWithoutPresence:
    """Tests for climate mode when no presence is detected.

    When not occupied, optimize for temperature:
    - Summer → 0 (close to block heat)
    - Winter → 100 (open to let heat in)
    - Intermediate → calculated position
    """

    @pytest.mark.parametrize(
        ("has_actual_sun", "is_summer", "is_winter", "expected"),
        [
            # No actual sun → default
            (False, False, False, "default"),
            (False, True, False, "default"),
            (False, False, True, "default"),
            # Actual sun + no presence + summer → 0
            (True, True, False, 0),
            # Actual sun + no presence + winter → 100
            (True, False, True, 100),
            # Actual sun + no presence + intermediate → calculated
            (True, False, False, "calculated"),
        ],
        ids=[
            "no_sun,intermediate->default",
            "no_sun,summer->default",
            "no_sun,winter->default",
            "sun,summer->0",
            "sun,winter->100",
            "sun,intermediate->calc",
        ],
    )
    def test_no_presence_temperature_behavior(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
        has_actual_sun: bool,
        is_summer: bool,
        is_winter: bool,
        expected,
    ) -> None:
        """Test climate mode output without presence."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        calculated_value = 35

        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=has_actual_sun,
            is_summer=is_summer,
            is_winter=is_winter,
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
            patch.object(cover, "calculate_percentage", return_value=calculated_value),
        ):
            mock_dsv.return_value = has_actual_sun
            mock_sunset.return_value = False

            state = ClimateCoverState(cover, climate_data)
            result = state.normal_type_cover()

            if expected == "default":
                assert result == 60
            elif expected == "calculated":
                assert result == calculated_value
            else:
                assert result == expected


# =============================================================================
# Matrix 6: Tilt Cover Specific (Winter Without Presence)
# =============================================================================


class TestTiltCoverSpecific:
    """Tests for tilt cover specific behavior.

    In winter without presence:
    - mode1: fully open (100) to let heat in
    - mode2: parallel to sun beams ((beta + 90) / 180 * 100) for max heat gain
    """

    def test_tilt_mode1_winter_no_presence_returns_100(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test tilt mode1 in winter without presence returns 100."""
        cover = create_tilt_cover(mock_hass, mock_logger, h_def=50, mode="mode1")

        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=True,
            is_summer=False,
            is_winter=True,
            blind_type="cover_tilt",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.tilt_state()

            assert result == 100

    def test_tilt_mode2_winter_no_presence_returns_parallel(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test tilt mode2 in winter without presence returns parallel angle."""
        cover = create_tilt_cover(
            mock_hass, mock_logger, h_def=50, mode="mode2", sol_elev=45.0
        )

        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=True,
            is_summer=False,
            is_winter=True,
            blind_type="cover_tilt",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.tilt_state()

            # Calculate expected: (beta + 90) / 180 * 100
            beta = np.rad2deg(cover.beta)
            expected = (beta + 90) / 180 * 100

            assert result == pytest.approx(expected, rel=0.01)

    @pytest.mark.parametrize(
        "mode",
        ["mode1", "mode2"],
    )
    def test_tilt_with_presence_ignores_winter(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
        mode: str,
    ) -> None:
        """Test tilt cover with presence ignores winter, uses calculated."""
        cover = create_tilt_cover(mock_hass, mock_logger, h_def=50, mode=mode)
        calculated_value = 45

        climate_data = climate_data_factory(
            is_presence=True,
            has_direct_sun=True,
            is_summer=False,
            is_winter=True,
            blind_type="cover_tilt",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
            patch.object(cover, "calculate_percentage", return_value=calculated_value),
        ):
            mock_dsv.return_value = True
            mock_sunset.return_value = False

            state = ClimateCoverState(cover, climate_data)
            result = state.tilt_state()

            # With presence, should use calculated position (not winter override)
            assert result == calculated_value

    @pytest.mark.parametrize(
        "mode",
        ["mode1", "mode2"],
    )
    def test_tilt_no_actual_sun_returns_default(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
        mode: str,
    ) -> None:
        """Test tilt cover without actual sun returns default."""
        cover = create_tilt_cover(mock_hass, mock_logger, h_def=50, mode=mode)

        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=False,  # Weather blocks sun
            is_summer=False,
            is_winter=True,
            blind_type="cover_tilt",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = True  # Geometry valid
            mock_sunset.return_value = False

            state = ClimateCoverState(cover, climate_data)
            result = state.tilt_state()

            # No actual sun (weather blocks), should use default
            assert result == 50

    def test_tilt_mode2_summer_no_presence_returns_0(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test tilt mode2 in summer without presence returns 0 (closed)."""
        cover = create_tilt_cover(mock_hass, mock_logger, h_def=50, mode="mode2")

        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=True,
            is_summer=True,
            is_winter=False,
            blind_type="cover_tilt",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.tilt_state()

            assert result == 0


# =============================================================================
# Matrix 7: Position Limits Application
# =============================================================================


class TestPositionLimits:
    """Tests for position limits (min_pos, max_pos) application.

    Limits can be:
    - Always applied (xxx_pos_bool=False)
    - Conditionally applied only when direct_sun_valid=True (xxx_pos_bool=True)
    """

    def test_max_position_always_applied(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test max_position always applied when max_pos_bool=False."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, max_pos=70, max_pos_bool=False
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=80),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 70

    def test_max_position_conditional_with_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test max_position conditionally applied when dsv=True."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, max_pos=70, max_pos_bool=True
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=80),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 70

    def test_max_position_conditional_without_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test max_position NOT applied when conditional and dsv=False."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=80, max_pos=70, max_pos_bool=True
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = False
            mock_sunset.return_value = False

            state = NormalCoverState(cover)
            result = state.get_state()

            # dsv=False, max_pos_bool=True, so limit NOT applied
            # Should return default (80)
            assert result == 80

    def test_min_position_always_applied(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test min_position always applied when min_pos_bool=False."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, min_pos=30, min_pos_bool=False
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=20),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 30

    def test_min_position_conditional_with_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test min_position conditionally applied when dsv=True."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, min_pos=30, min_pos_bool=True
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=20),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 30

    def test_min_position_conditional_without_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test min_position NOT applied when conditional and dsv=False."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=20, min_pos=30, min_pos_bool=True
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = False
            mock_sunset.return_value = False

            state = NormalCoverState(cover)
            result = state.get_state()

            # dsv=False, min_pos_bool=True, so limit NOT applied
            # Should return default (20)
            assert result == 20

    def test_max_takes_precedence_over_min(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that max position is applied after min (max wins if conflicting)."""
        # This tests the order of application in the code
        cover = create_vertical_cover(
            mock_hass,
            mock_logger,
            h_def=60,
            max_pos=70,
            min_pos=30,
            max_pos_bool=False,
            min_pos_bool=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=80),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            # 80 capped by max_pos=70
            assert result == 70

    def test_no_limits_active(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test result unchanged when no limits are active."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, max_pos=100, min_pos=0
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=50),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 50


# =============================================================================
# Climate Mode Position Limits
# =============================================================================


class TestClimatePositionLimits:
    """Tests for position limits in climate mode (ClimateCoverState)."""

    def test_climate_max_position_applied(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test max position limit applied in climate mode."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, max_pos=50, max_pos_bool=False
        )
        climate_data = climate_data_factory(
            is_presence=True,
            has_direct_sun=True,
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=70),
        ):
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.get_state()

            assert result == 50

    def test_climate_min_position_applied(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test min position limit applied in climate mode."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, min_pos=25, min_pos_bool=False
        )
        climate_data = climate_data_factory(
            is_presence=True,
            has_direct_sun=True,
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=10),
        ):
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.get_state()

            assert result == 25

    def test_climate_summer_close_respects_min_position(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test summer close (0) is not below min_position if applied."""
        # Note: min_pos is applied AFTER the summer/winter logic
        # So if min_pos=25, summer returns 0, then min_pos raises it to 25
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, min_pos=25, min_pos_bool=False
        )
        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=True,
            is_summer=True,
            is_winter=False,
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.get_state()

            # Summer returns 0, but min_pos=25 raises it
            assert result == 25

    def test_climate_winter_open_respects_max_position(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test winter open (100) is capped by max_position if applied."""
        cover = create_vertical_cover(
            mock_hass, mock_logger, h_def=60, max_pos=75, max_pos_bool=False
        )
        climate_data = climate_data_factory(
            is_presence=False,
            has_direct_sun=True,
            is_summer=False,
            is_winter=True,
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with patch.object(
            type(cover), "direct_sun_valid", new_callable=PropertyMock
        ) as mock_dsv:
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.get_state()

            # Winter returns 100, but max_pos=75 caps it
            assert result == 75


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_calculated_value_clipped_to_100(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test calculated value above 100 is clipped."""
        cover = create_vertical_cover(mock_hass, mock_logger)

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=150),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 100

    def test_calculated_value_clipped_to_0(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test calculated value below 0 is clipped."""
        cover = create_vertical_cover(mock_hass, mock_logger)

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=-10),
        ):
            mock_dsv.return_value = True

            state = NormalCoverState(cover)
            result = state.get_state()

            assert result == 0

    def test_sunset_valid_uses_sunset_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that sunset_valid=True returns sunset_pos instead of h_def."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(2099, 6, 21, 21)
            mock_sun_data.return_value.sunrise.return_value = datetime(2099, 6, 21, 5)

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=10,  # Different from default
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,
                h_def=60,
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
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(
                type(cover), "sunset_valid", new_callable=PropertyMock
            ) as mock_sunset,
        ):
            mock_dsv.return_value = False
            mock_sunset.return_value = True  # After sunset

            state = NormalCoverState(cover)
            result = state.get_state()

            # Should use sunset_pos (10) not h_def (60)
            assert result == 10

    def test_get_state_dispatches_to_tilt_for_cover_tilt(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test ClimateCoverState.get_state() dispatches to tilt_state for tilt covers."""
        cover = create_tilt_cover(mock_hass, mock_logger, h_def=50, mode="mode1")
        climate_data = climate_data_factory(
            is_presence=True,
            has_direct_sun=True,
            blind_type="cover_tilt",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=45),
        ):
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.get_state()

            # Should return a valid tilt percentage
            assert 0 <= result <= 100

    def test_get_state_uses_normal_type_for_cover_blind(
        self,
        mock_hass: MagicMock,
        mock_logger: ConfigContextAdapter,
        climate_data_factory,
    ) -> None:
        """Test ClimateCoverState.get_state() uses normal_type_cover for blinds."""
        cover = create_vertical_cover(mock_hass, mock_logger, h_def=60)
        climate_data = climate_data_factory(
            is_presence=True,
            has_direct_sun=True,
            blind_type="cover_blind",
            lux=False,
            irradiance=False,
            cloud=False,
        )

        with (
            patch.object(
                type(cover), "direct_sun_valid", new_callable=PropertyMock
            ) as mock_dsv,
            patch.object(cover, "calculate_percentage", return_value=35),
        ):
            mock_dsv.return_value = True

            state = ClimateCoverState(cover, climate_data)
            result = state.get_state()

            assert result == 35
