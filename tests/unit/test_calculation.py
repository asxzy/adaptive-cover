"""Tests for cover position calculation classes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from custom_components.adaptive_cover.calculation import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
)

if TYPE_CHECKING:
    from custom_components.adaptive_cover.config_context_adapter import (
        ConfigContextAdapter,
    )


class TestAdaptiveGeneralCoverProperties:
    """Tests for common AdaptiveGeneralCover properties."""

    def test_gamma_sun_from_south_south_window(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test gamma when sun is directly south and window faces south."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,  # Sun from south
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
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

            # When sun and window both face south, gamma should be 0
            assert cover.gamma == pytest.approx(0.0, abs=0.1)

    def test_gamma_sun_from_east_south_window(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test gamma when sun is from east and window faces south."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=90.0,  # Sun from east
                sol_elev=30.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
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

            # Window faces south (180), sun from east (90): gamma = 180 - 90 = 90
            assert cover.gamma == pytest.approx(90.0, abs=0.1)

    def test_azi_min_abs(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test minimum azimuth calculation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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

            # win_azi=180, fov_left=90: azi_min_abs = (180 - 90 + 360) % 360 = 90
            assert cover.azi_min_abs == 90

    def test_azi_max_abs(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test maximum azimuth calculation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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

            # win_azi=180, fov_right=90: azi_max_abs = (180 + 90 + 360) % 360 = 270
            assert cover.azi_max_abs == 270

    def test_valid_sun_in_front_of_window(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that sun directly in front of window is valid."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,  # Sun from south
                sol_elev=45.0,  # Above horizon
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
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

            assert cover.valid is True

    def test_valid_sun_behind_window(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test that sun behind window is not valid."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=0.0,  # Sun from north (behind south window)
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
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

            assert cover.valid is False

    def test_valid_elevation_within_range(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test valid_elevation with elevation constraints."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,  # Within range
                sunset_pos=0,
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
                min_elevation=20,  # Min elevation constraint
                max_elevation=60,  # Max elevation constraint
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            assert cover.valid_elevation is True

    def test_valid_elevation_below_range(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test valid_elevation when sun is below min elevation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=10.0,  # Below min
                sunset_pos=0,
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
                min_elevation=20,
                max_elevation=60,
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            assert cover.valid_elevation is False

    def test_is_sun_in_blind_spot_true(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test blind spot detection when sun is in blind spot."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            # Blind spot logic:
            # left_edge = fov_left - blind_spot_left
            # right_edge = fov_left - blind_spot_right
            # in_blind_spot = (gamma <= left_edge) & (gamma >= right_edge)
            #
            # With gamma=0, fov_left=90:
            # We need: right_edge <= 0 <= left_edge
            # So: blind_spot_left=90 => left_edge=0
            #     blind_spot_right=100 => right_edge=-10
            # gamma=0 is within -10 to 0: right_edge <= gamma <= left_edge
            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,  # gamma will be 0
                sol_elev=30.0,
                sunset_pos=0,
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
                blind_spot_left=80,  # left_edge = 90 - 80 = 10
                blind_spot_right=100,  # right_edge = 90 - 100 = -10
                blind_spot_elevation=40,  # elev 30 < 40, so elevation check passes
                blind_spot_on=True,
                min_elevation=None,
                max_elevation=None,
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            # gamma=0 is within range: -10 <= 0 <= 10
            # elev=30 < blind_spot_elevation=40
            assert cover.is_sun_in_blind_spot is True


class TestAdaptiveVerticalCover:
    """Tests for AdaptiveVerticalCover calculations."""

    def test_cover_height(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test cover height calculation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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
                cover_bottom=0.3,
                shaded_area_height=0.0,
            )

            # cover_height = h_win - cover_bottom = 2.1 - 0.3 = 1.8
            assert cover.cover_height == pytest.approx(1.8, abs=0.01)

    def test_calculate_position_sun_from_south(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test position calculation with sun from south."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,  # Sun from south
                sol_elev=45.0,  # 45 degree elevation
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
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
                distance=0.5,  # 0.5m distance
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            position = cover.calculate_position()
            # At 45 degrees elevation, tan(45) = 1
            # gamma = 0, cos(0) = 1, so d_eff = 0.5
            # position = 0 + 0.5 * 1 = 0.5 (clipped between 0 and 2.1)
            assert position == pytest.approx(0.5, abs=0.1)

    def test_calculate_percentage(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test percentage calculation from position."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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

            percentage = cover.calculate_percentage()
            # position ~= 0.5, cover_height = 2.1
            # percentage = (0.5 - 0) / 2.1 * 100 ~= 24%
            assert 20 <= percentage <= 30


class TestAdaptiveHorizontalCover:
    """Tests for AdaptiveHorizontalCover (awning) calculations."""

    def test_calculate_position_awning(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test awning extension calculation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveHorizontalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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
                awn_length=2.1,
                awn_angle=0.0,
            )

            position = cover.calculate_position()
            # Position should be a positive length value
            assert position > 0

    def test_calculate_percentage_awning(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test awning percentage calculation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveHorizontalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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
                awn_length=2.1,
                awn_angle=0.0,
            )

            percentage = cover.calculate_percentage()
            # Should return a percentage value
            assert isinstance(percentage, int)


class TestAdaptiveTiltCover:
    """Tests for AdaptiveTiltCover (venetian blind) calculations."""

    def test_beta_calculation(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test beta (profile angle) calculation."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveTiltCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,  # Sun from south
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
                h_def=50,
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
                mode="mode1",
            )

            beta = cover.beta
            # With gamma=0 (sun straight ahead) and elev=45,
            # beta = arctan(tan(45) / cos(0)) = arctan(1/1) = 45 degrees
            assert np.rad2deg(beta) == pytest.approx(45.0, abs=1.0)

    def test_calculate_position_mode1(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test slat angle calculation for mode1 (single directional)."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveTiltCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,
                h_def=50,
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
                mode="mode1",
            )

            position = cover.calculate_position()
            # Position should be an angle in degrees
            assert 0 <= position <= 90

    def test_calculate_percentage_mode1(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test percentage calculation for mode1."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveTiltCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,
                h_def=50,
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
                mode="mode1",
            )

            percentage = cover.calculate_percentage()
            # Mode1: 0-90 degrees maps to 0-100%
            assert 0 <= percentage <= 100

    def test_calculate_percentage_mode2(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test percentage calculation for mode2 (bi-directional)."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveTiltCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,
                h_def=50,
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
                mode="mode2",
            )

            percentage = cover.calculate_percentage()
            # Mode2: 0-180 degrees maps to 0-100%
            assert 0 <= percentage <= 100


class TestCoverFOV:
    """Tests for field of view calculations."""

    def test_fov_method(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test fov() returns correct azimuth range."""
        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=180.0,
                sol_elev=45.0,
                sunset_pos=0,
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

            fov = cover.fov()
            assert fov == [90, 270]  # [azi_min_abs, azi_max_abs]
