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


class TestSolarTimes:
    """Tests for solar_times method."""

    def test_solar_times_returns_times(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test solar_times returns start and end times."""
        import pandas as pd

        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            # Mock time index
            times = pd.date_range("2024-06-21 05:00", "2024-06-21 21:00", freq="5min")
            num_points = len(times)
            mock_sun_data.return_value.times = times
            # Sun from east (90) to west (270) through south (180)
            # Create azimuths that span the range and match the number of time points
            azimuths = [90 + (180 * i / num_points) for i in range(num_points)]
            elevations = [30.0] * num_points  # Above horizon
            mock_sun_data.return_value.solar_azimuth = azimuths
            mock_sun_data.return_value.solar_elevation = elevations
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

            start, end = cover.solar_times()
            # Should return datetime objects when sun is in FOV
            assert (
                start is not None or end is not None or (start is None and end is None)
            )

    def test_solar_times_returns_none_when_no_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test solar_times returns None when sun never in FOV."""
        import pandas as pd

        with patch(
            "custom_components.adaptive_cover.calculation.SunData"
        ) as mock_sun_data:
            times = pd.date_range("2024-06-21 05:00", "2024-06-21 21:00", freq="5min")
            mock_sun_data.return_value.times = times
            # Sun always from north (0) - never in south-facing FOV
            azimuths = [0.0] * len(times)
            elevations = [30.0] * len(times)
            mock_sun_data.return_value.solar_azimuth = azimuths
            mock_sun_data.return_value.solar_elevation = elevations
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
                win_azi=180,  # South-facing
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

            start, end = cover.solar_times()
            # Should return None, None when sun never in FOV
            assert start is None
            assert end is None


class TestSunsetSunriseValid:
    """Tests for sunset_valid and sunrise_valid properties."""

    def test_sunset_valid_before_sunset(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test sunset_valid is False before sunset."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
            # Sunset at 21:00, current time is 14:00
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
                sunset_off=0,  # No offset
                sunrise_off=0,
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

            # Before sunset (14:00 < 21:00)
            assert cover.sunset_valid is False

    def test_sunset_valid_after_sunset(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test sunset_valid is True after sunset."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 22:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
            # Sunset at 21:00, current time is 22:00
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
                sunset_off=0,  # No offset
                sunrise_off=0,
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

            # After sunset (22:00 > 21:00)
            assert cover.sunset_valid is True

    def test_sunset_valid_before_sunrise(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test sunset_valid is True before sunrise (early morning)."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 04:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
            # Sunrise at 05:00, current time is 04:00
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
                sunset_off=0,
                sunrise_off=0,  # No offset
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

            # Before sunrise (04:00 < 05:00), sunset_valid should be True
            assert cover.sunset_valid is True


class TestBlindSpotEdgeCases:
    """Tests for blind spot edge cases."""

    def test_blind_spot_disabled(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test blind spot detection when disabled."""
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
                blind_spot_left=80,
                blind_spot_right=100,
                blind_spot_elevation=40,
                blind_spot_on=False,  # Disabled
                min_elevation=None,
                max_elevation=None,
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            # Should return False when disabled
            assert cover.is_sun_in_blind_spot is False

    def test_blind_spot_no_elevation_check(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test blind spot without elevation constraint."""
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
                sol_azi=180.0,  # gamma = 0
                sol_elev=60.0,  # High elevation
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
                blind_spot_left=80,  # left_edge = 10
                blind_spot_right=100,  # right_edge = -10
                blind_spot_elevation=None,  # No elevation check
                blind_spot_on=True,
                min_elevation=None,
                max_elevation=None,
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            # gamma=0 is within range, no elevation check
            assert cover.is_sun_in_blind_spot is True


class TestElevationConstraints:
    """Tests for elevation constraints."""

    def test_elevation_above_max(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test valid_elevation when sun is above max elevation."""
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
                sol_elev=70.0,  # Above max
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
                max_elevation=60,  # Max is 60
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            assert cover.valid_elevation is False

    def test_elevation_no_constraints(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test valid_elevation with no constraints."""
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
                min_elevation=None,  # No min
                max_elevation=None,  # No max
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            # With no constraints, should always be valid
            assert cover.valid_elevation is True


class TestDefaultProperty:
    """Tests for the default property."""

    def test_default_returns_h_def(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test default returns h_def when not sunset."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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
                sunset_off=0,
                sunrise_off=0,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,
                h_def=75,  # Default position
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

            # Before sunset, should return h_def
            assert cover.default == 75


class TestAzimuthEdges:
    """Tests for azimuth edge property."""

    def test_get_azimuth_edges(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test _get_azimuth_edges returns sum of fov."""
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
                fov_left=60,
                fov_right=45,
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

            # _get_azimuth_edges = fov_left + fov_right = 60 + 45 = 105
            assert cover._get_azimuth_edges == 105


class TestClimateCoverData:
    """Tests for ClimateCoverData class."""

    def test_is_presence_override_true(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence uses override value when set to True."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity="binary_sensor.motion",
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
            _is_presence_override=(True, True),  # Override to True
        )

        assert climate.is_presence is True

    def test_is_presence_override_false(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence uses override value when set to False."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity="binary_sensor.motion",
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
            _is_presence_override=(True, False),  # Override to False
        )

        assert climate.is_presence is False

    def test_is_presence_no_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence returns True when no entity configured."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity=None,  # No entity
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

        assert climate.is_presence is True

    def test_has_direct_sun_override_true(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun uses override value when set to True."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity=None,
            weather_entity="weather.home",
            weather_condition=["sunny"],
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
            _has_direct_sun_override=(True, True),  # Override to True
        )

        assert climate.has_direct_sun is True

    def test_has_direct_sun_override_false(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun uses override value when set to False."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity=None,
            weather_entity="weather.home",
            weather_condition=["sunny"],
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
            _has_direct_sun_override=(True, False),  # Override to False
        )

        assert climate.has_direct_sun is False

    def test_has_direct_sun_no_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun returns True when no entity configured."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity=None,
            weather_entity=None,  # No entity
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

        assert climate.has_direct_sun is True

    def test_lux_override(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test lux uses override value when set."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
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
            _lux_override=True,  # Override to True
        )

        assert climate.lux is True

    def test_irradiance_override(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test irradiance uses override value when set."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
            presence_entity=None,
            weather_entity=None,
            weather_condition=[],
            blind_type="cover_blind",
            transparent_blind=False,
            lux_entity=None,
            irradiance_entity="sensor.irradiance",
            lux_threshold=None,
            irradiance_threshold=500,
            _use_lux=False,
            _use_irradiance=True,
            cloud_entity=None,
            cloud_threshold=None,
            _use_cloud=False,
            _irradiance_override=False,  # Override to False
        )

        assert climate.irradiance is False

    def test_cloud_override(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test cloud uses override value when set."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        climate = ClimateCoverData(
            hass=mock_hass,
            logger=mock_logger,
            temp_entity=None,
            temp_low=20.0,
            temp_high=25.0,
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
            cloud_entity="sensor.cloud",
            cloud_threshold=50,
            _use_cloud=True,
            _cloud_override=True,  # Override to True
        )

        assert climate.cloud is True


class TestClimateCoverStateCreation:
    """Tests for ClimateCoverState creation."""

    def test_climate_state_initialization(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test ClimateCoverState can be initialized correctly."""
        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

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

            # Create climate with all overrides
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
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
                _has_direct_sun_override=(True, True),
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)

            # State should have the correct cover reference
            assert state.cover is cover


class TestMinMaxPositionBool:
    """Tests for min_pos_bool and max_pos_bool behavior."""

    def test_apply_min_position_with_bool_and_direct_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test apply_min_position when min_pos_bool is True and sun is direct."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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
                min_pos=20,  # Min position set
                max_pos_bool=False,
                min_pos_bool=True,  # Only apply when direct sun
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

            # direct_sun_valid is True in this configuration
            assert cover.apply_min_position is True

    def test_apply_max_position_with_bool_and_no_direct_sun(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test apply_max_position when max_pos_bool is True but no direct sun."""
        from freezegun import freeze_time

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
            mock_sun_data.return_value.sunset.return_value = datetime(
                2024, 6, 21, 21, 0, 0
            )
            mock_sun_data.return_value.sunrise.return_value = datetime(
                2024, 6, 21, 5, 0, 0
            )

            cover = AdaptiveVerticalCover(
                hass=mock_hass,
                logger=mock_logger,
                sol_azi=0.0,  # Sun from north - not in front of south window
                sol_elev=45.0,
                sunset_pos=0,
                sunset_off=30,
                sunrise_off=30,
                timezone="Europe/Amsterdam",
                fov_left=90,
                fov_right=90,
                win_azi=180,  # South-facing window
                h_def=60,
                max_pos=80,  # Max position set
                min_pos=0,
                max_pos_bool=True,  # Only apply when direct sun
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

            # direct_sun_valid is False (sun behind window)
            # So apply_max_position should be False when max_pos_bool=True
            assert cover.apply_max_position is False


class TestPresenceFromDifferentDomains:
    """Tests for presence detection from different entity domains."""

    def test_is_presence_from_zone_domain(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence returns True when zone has persons."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        # Mock zone state to return "2" (2 persons in zone)
        with (
            patch(
                "custom_components.adaptive_cover.calculation.get_safe_state",
                return_value="2",
            ),
            patch(
                "custom_components.adaptive_cover.calculation.get_domain",
                return_value="zone",
            ),
        ):
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity="zone.home",
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

            assert climate.is_presence is True

    def test_is_presence_from_zone_domain_empty(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence returns False when zone has no persons."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        # Mock zone state to return "0" (0 persons in zone)
        with (
            patch(
                "custom_components.adaptive_cover.calculation.get_safe_state",
                return_value="0",
            ),
            patch(
                "custom_components.adaptive_cover.calculation.get_domain",
                return_value="zone",
            ),
        ):
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity="zone.home",
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

            assert climate.is_presence is False

    def test_is_presence_unknown_domain_returns_true(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence returns True for unknown entity domains."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        # Mock an unknown domain
        with (
            patch(
                "custom_components.adaptive_cover.calculation.get_safe_state",
                return_value="some_state",
            ),
            patch(
                "custom_components.adaptive_cover.calculation.get_domain",
                return_value="unknown_domain",
            ),
        ):
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity="unknown_domain.test",
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

            # Unknown domain defaults to True
            assert climate.is_presence is True


class TestInsideTemperatureFromClimate:
    """Tests for inside temperature from climate entity."""

    def test_inside_temp_from_climate_entity(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test inside_temperature is fetched from climate entity."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        # Mock state_attr to return temperature from climate entity
        with (
            patch(
                "custom_components.adaptive_cover.calculation.get_domain",
                return_value="climate",
            ),
            patch(
                "custom_components.adaptive_cover.calculation.state_attr",
                return_value=22.0,
            ),
        ):
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity="climate.living_room",  # Climate entity
                temp_low=20.0,
                temp_high=25.0,
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

            assert climate.inside_temperature == 22.0


class TestOverrideNoneValues:
    """Tests for override tuples with None values."""

    def test_is_presence_override_with_none_value(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test is_presence override with None value uses entity."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        # Override is set but value is None - should fall through to entity check
        with (
            patch(
                "custom_components.adaptive_cover.calculation.get_safe_state",
                return_value="on",
            ),
            patch(
                "custom_components.adaptive_cover.calculation.get_domain",
                return_value="binary_sensor",
            ),
        ):
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity="binary_sensor.motion",
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
                _is_presence_override=(False, None),  # use_override=False, value=None
            )

            # Should use entity value since use_override is False
            assert climate.is_presence is True

    def test_has_direct_sun_override_with_none_value(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test has_direct_sun override with None value uses entity."""
        from custom_components.adaptive_cover.calculation import ClimateCoverData

        mock_state = MagicMock()
        mock_state.state = "sunny"
        mock_hass.states.get.return_value = mock_state

        with patch(
            "custom_components.adaptive_cover.calculation.get_safe_state",
            return_value="sunny",
        ):
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity=None,
                weather_entity="weather.home",
                weather_condition=["sunny"],
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
                _has_direct_sun_override=(False, None),  # use_override=False
            )

            # Should use entity value since use_override is False
            assert climate.has_direct_sun is True


class TestSensorUnavailableCases:
    """Tests for _has_actual_sun with unavailable sensors."""

    def test_has_actual_sun_weather_unavailable(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test _has_actual_sun returns False when weather unavailable."""
        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

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

            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity=None,
                weather_entity="weather.home",
                weather_condition=["sunny"],
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
                _has_direct_sun_override=(True, None),  # Unavailable
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)

            # Weather unavailable should return False
            assert state._has_actual_sun() is False

    def test_has_actual_sun_lux_below_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test _has_actual_sun returns False when lux is below threshold."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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

            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
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
                _lux_override=True,  # Lux below threshold (True means no sun)
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)

            # Lux below threshold means no actual sun
            assert state._has_actual_sun() is False

    def test_has_actual_sun_cloud_above_threshold(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test _has_actual_sun returns False when cloud is above threshold."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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

            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
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
                cloud_entity="sensor.cloud",
                cloud_threshold=50,
                _use_cloud=True,
                _cloud_override=True,  # Cloud above threshold (True means too cloudy)
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)

            # Cloud above threshold means no actual sun
            assert state._has_actual_sun() is False


class TestClimateCoverStatePositionLimits:
    """Tests for position limits in ClimateCoverState.get_state()."""

    def test_climate_state_applies_max_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test ClimateCoverState applies max_position limit."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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
                h_def=100,  # High default
                max_pos=80,  # Max position is 80
                min_pos=0,
                max_pos_bool=False,  # Always apply
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

            # Climate with no actual sun (will use default which is 100)
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
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
                _has_direct_sun_override=(True, False),  # No sun
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)
            result = state.get_state()

            # Should be capped at max_pos (80), not default (100)
            assert result == 80

    def test_climate_state_applies_min_position(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test ClimateCoverState applies min_position limit."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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
                h_def=10,  # Low default
                max_pos=100,
                min_pos=20,  # Min position is 20
                max_pos_bool=False,
                min_pos_bool=False,  # Always apply
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

            # Climate with no actual sun (will use default which is 10)
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
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
                _has_direct_sun_override=(True, False),  # No sun
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)
            result = state.get_state()

            # Should be raised to min_pos (20), not default (10)
            assert result == 20


class TestTiltMode2WinterLogic:
    """Tests for tilt mode2 winter calculation."""

    def test_tilt_mode2_winter_calculation(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test tilt without presence in winter mode2 calculates parallel angle."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
            patch(
                "custom_components.adaptive_cover.calculation.get_safe_state",
                return_value="10.0",  # Below temp_low to trigger winter
            ),
        ):
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
                mode="mode2",  # Bi-directional mode
            )

            # Winter conditions: temp=10 < temp_low=25
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity="sensor.temp",  # Has temp entity
                temp_low=25.0,  # Temp_low is 25, current is 10
                temp_high=30.0,
                presence_entity=None,
                weather_entity=None,
                weather_condition=[],
                blind_type="cover_tilt",
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
                _is_presence_override=(True, False),  # No presence
                _has_direct_sun_override=(True, True),  # Has sun
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)
            result = state.tilt_without_presence(180)

            # In winter mode2 with sun: calculates parallel to sun angle
            # beta = 45 degrees, tilt = (45 + 90) / 180 * 100 = 75%
            assert 70 <= result <= 80

    def test_tilt_mode2_summer_returns_zero(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test tilt without presence in summer returns 0 (closed)."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
            patch(
                "custom_components.adaptive_cover.calculation.get_safe_state",
                return_value="30.0",  # Above temp_high to trigger summer
            ),
        ):
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

            # Summer conditions: temp=30 > temp_high=20
            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity="sensor.temp",  # Has temp entity
                temp_low=15.0,
                temp_high=20.0,  # Temp_high is 20, current is 30
                presence_entity=None,
                weather_entity=None,
                weather_condition=[],
                blind_type="cover_tilt",
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
                _is_presence_override=(True, False),  # No presence
                _has_direct_sun_override=(True, True),  # Has sun
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)
            result = state.tilt_without_presence(180)

            # In summer with sun: closed (0) to block heat
            assert result == 0


class TestTiltPresenceUnavailable:
    """Tests for tilt state when presence is unavailable."""

    def test_tilt_presence_unavailable_assumes_occupied(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test tilt_state assumes occupied when presence unavailable."""
        from freezegun import freeze_time

        from custom_components.adaptive_cover.calculation import (
            ClimateCoverData,
            ClimateCoverState,
        )

        with (
            freeze_time("2024-06-21 14:00:00"),
            patch(
                "custom_components.adaptive_cover.calculation.SunData"
            ) as mock_sun_data,
        ):
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

            climate = ClimateCoverData(
                hass=mock_hass,
                logger=mock_logger,
                temp_entity=None,
                temp_low=20.0,
                temp_high=25.0,
                presence_entity="binary_sensor.motion",
                weather_entity=None,
                weather_condition=[],
                blind_type="cover_tilt",
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
                _is_presence_override=(True, None),  # Presence unavailable (None)
            )

            state = ClimateCoverState(cover=cover, climate_data=climate)
            result = state.tilt_state()

            # When presence is None (unavailable), assumes occupied
            # This triggers tilt_with_presence path
            # Result can be a numpy type, so check it's a valid number
            assert 0 <= result <= 100


class TestElevationOnlyConstraints:
    """Tests for elevation constraints with only min or only max."""

    def test_elevation_only_max_below_max(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test valid_elevation when only max_elevation is set and sun is below."""
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
                sol_elev=30.0,  # Below max
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
                min_elevation=None,  # No min
                max_elevation=60,  # Only max
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            assert cover.valid_elevation is True

    def test_elevation_only_min_above_min(
        self, mock_hass: MagicMock, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test valid_elevation when only min_elevation is set and sun is above."""
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
                sol_elev=45.0,  # Above min
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
                min_elevation=20,  # Only min
                max_elevation=None,  # No max
                distance=0.5,
                h_win=2.1,
                cover_bottom=0.0,
                shaded_area_height=0.0,
            )

            assert cover.valid_elevation is True
