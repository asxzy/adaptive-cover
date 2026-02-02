"""Generate values for all types of covers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import state_attr
from numpy import cos, sin, tan
from numpy import radians as rad

from .config_context_adapter import ConfigContextAdapter
from .helpers import get_domain, get_safe_state
from .sun import SunData

# Default weather conditions that allow direct sunlight
DEFAULT_WEATHER_CONDITIONS = [
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
    ATTR_CONDITION_SNOWY,
]


@dataclass
class AdaptiveGeneralCover(ABC):
    """Collect common data."""

    hass: HomeAssistant
    logger: ConfigContextAdapter
    sol_azi: float
    sol_elev: float
    sunset_pos: int
    sunset_off: int
    sunrise_off: int
    timezone: str
    fov_left: int
    fov_right: int
    win_azi: int
    h_def: int
    max_pos: int
    min_pos: int
    max_pos_bool: bool
    min_pos_bool: bool
    blind_spot_left: int
    blind_spot_right: int
    blind_spot_elevation: int
    blind_spot_on: bool
    min_elevation: int
    max_elevation: int
    sun_data: SunData = field(init=False)

    def __post_init__(self):
        """Add solar data to dataset."""
        self.sun_data = SunData(self.timezone, self.hass)

    def solar_times(self):
        """Determine start/end times."""
        df_today = pd.DataFrame(
            {
                "azimuth": self.sun_data.solar_azimuth,
                "elevation": self.sun_data.solar_elevation,
            }
        )
        solpos = df_today.set_index(self.sun_data.times)

        alpha = solpos["azimuth"]
        frame = (
            (alpha - self.azi_min_abs) % 360
            <= (self.azi_max_abs - self.azi_min_abs) % 360
        ) & (solpos["elevation"] > 0)

        if solpos[frame].empty:
            return None, None
        else:
            return (
                solpos[frame].index[0].to_pydatetime(),
                solpos[frame].index[-1].to_pydatetime(),
            )

    @property
    def _get_azimuth_edges(self) -> tuple[int, int]:
        """Calculate azimuth edges."""
        return self.fov_left + self.fov_right

    @property
    def is_sun_in_blind_spot(self) -> bool:
        """Check if sun is in blind spot."""
        if (
            self.blind_spot_left is not None
            and self.blind_spot_right is not None
            and self.blind_spot_on
        ):
            left_edge = self.fov_left - self.blind_spot_left
            right_edge = self.fov_left - self.blind_spot_right
            blindspot = (self.gamma <= left_edge) & (self.gamma >= right_edge)
            if self.blind_spot_elevation is not None:
                blindspot = blindspot & (self.sol_elev <= self.blind_spot_elevation)
            self.logger.debug("Is sun in blind spot? %s", blindspot)
            return blindspot
        return False

    @property
    def azi_min_abs(self) -> int:
        """Calculate min azimuth."""
        azi_min_abs = (self.win_azi - self.fov_left + 360) % 360
        return azi_min_abs

    @property
    def azi_max_abs(self) -> int:
        """Calculate max azimuth."""
        azi_max_abs = (self.win_azi + self.fov_right + 360) % 360
        return azi_max_abs

    @property
    def gamma(self) -> float:
        """Calculate Gamma."""
        # surface solar azimuth
        gamma = (self.win_azi - self.sol_azi + 180) % 360 - 180
        return gamma

    @property
    def valid_elevation(self) -> bool:
        """Check if elevation is within range."""
        if self.min_elevation is None and self.max_elevation is None:
            return self.sol_elev >= 0
        if self.min_elevation is None:
            return self.sol_elev <= self.max_elevation
        if self.max_elevation is None:
            return self.sol_elev >= self.min_elevation
        within_range = self.min_elevation <= self.sol_elev <= self.max_elevation
        self.logger.debug("elevation within range? %s", within_range)
        return within_range

    @property
    def valid(self) -> bool:
        """Determine if sun is in front of window."""
        # clip azi_min and azi_max to 90
        azi_min = min(self.fov_left, 90)
        azi_max = min(self.fov_right, 90)

        # valid sun positions are those within the blind's azimuth range and above the horizon (FOV)
        valid = (
            (self.gamma < azi_min) & (self.gamma > -azi_max) & (self.valid_elevation)
        )
        self.logger.debug("Sun in front of window (ignoring blindspot)? %s", valid)
        return valid

    @property
    def sunset_valid(self) -> bool:
        """Determine if it is after sunset plus offset."""
        sunset = self.sun_data.sunset().replace(tzinfo=None)
        sunrise = self.sun_data.sunrise().replace(tzinfo=None)
        after_sunset = datetime.utcnow() > (sunset + timedelta(minutes=self.sunset_off))
        before_sunrise = datetime.utcnow() < (
            sunrise + timedelta(minutes=self.sunrise_off)
        )
        self.logger.debug(
            "After sunset plus offset? %s", (after_sunset or before_sunrise)
        )
        return after_sunset or before_sunrise

    @property
    def default(self) -> float:
        """Change default position at sunset."""
        default = self.h_def
        if self.sunset_valid:
            default = self.sunset_pos
        return default

    def fov(self) -> list:
        """Return field of view."""
        return [self.azi_min_abs, self.azi_max_abs]

    @property
    def apply_min_position(self) -> bool:
        """Check if min position is applied."""
        if self.min_pos is not None and self.min_pos != 0:
            if self.min_pos_bool:
                return self.direct_sun_valid
            return True
        return False

    @property
    def apply_max_position(self) -> bool:
        """Check if max position is applied."""
        if self.max_pos is not None and self.max_pos != 100:
            if self.max_pos_bool:
                return self.direct_sun_valid
            return True
        return False

    @property
    def direct_sun_valid(self) -> bool:
        """Check if sun is directly in front of window."""
        return (self.valid) & (not self.sunset_valid) & (not self.is_sun_in_blind_spot)

    @abstractmethod
    def calculate_position(self) -> float:
        """Calculate the position of the blind."""

    @abstractmethod
    def calculate_percentage(self) -> int:
        """Calculate percentage from position."""


@dataclass
class NormalCoverState:
    """Compute state for normal operation."""

    cover: AdaptiveGeneralCover

    def get_state(
        self, has_direct_sun: bool | None = None, cloud_override: bool | None = None
    ) -> int:
        """Return state.

        Args:
            has_direct_sun: Optional weather check. When set, only use calculated
                position if weather allows direct sun. None means no weather check.
            cloud_override: Optional cloud check. When True, it means too cloudy
                and should use default position.

        """
        self.cover.logger.debug("Determining normal position")
        dsv = self.cover.direct_sun_valid
        self.cover.logger.debug(
            "Sun directly in front of window & before sunset + offset? %s", dsv
        )

        # Check weather condition if provided
        weather_allows_sun = has_direct_sun is None or has_direct_sun
        self.cover.logger.debug("Weather allows direct sun? %s", weather_allows_sun)

        # Check cloud coverage - if True, too cloudy for sun
        cloud_blocks_sun = cloud_override is True
        self.cover.logger.debug("Cloud blocks sun? %s", cloud_blocks_sun)

        if dsv and weather_allows_sun and not cloud_blocks_sun:
            state = self.cover.calculate_percentage()
            self.cover.logger.debug(
                "Yes sun in window & weather sunny & not too cloudy: "
                "using calculated percentage (%s)",
                state,
            )
        else:
            state = self.cover.default
            self.cover.logger.debug(
                "No sun in window or weather cloudy or too cloudy: "
                "using default value (%s)",
                state,
            )

        result = np.clip(state, 0, 100)
        if self.cover.apply_max_position and result > self.cover.max_pos:
            return self.cover.max_pos
        if self.cover.apply_min_position and result < self.cover.min_pos:
            return self.cover.min_pos
        return result


@dataclass
class ClimateCoverData:
    """Fetch additional data."""

    hass: HomeAssistant
    logger: ConfigContextAdapter
    temp_entity: str
    temp_low: float
    temp_high: float
    presence_entity: str
    weather_entity: str
    weather_condition: list[str]
    blind_type: str
    transparent_blind: bool
    lux_entity: str
    irradiance_entity: str
    lux_threshold: int
    irradiance_threshold: int
    _use_lux: bool
    _use_irradiance: bool
    cloud_entity: str
    cloud_threshold: int
    _use_cloud: bool
    # Override fields - when set to a tuple, these values are used instead of computing
    # from entities. The tuple format is (use_override: bool, value: bool | None).
    # None means "not overridden" - compute from entity.
    # (True, value) means "use this value" (either current or last known).
    _is_presence_override: tuple[bool, bool | None] | None = None
    _has_direct_sun_override: tuple[bool, bool | None] | None = None
    _lux_override: bool | None = None
    _irradiance_override: bool | None = None
    _cloud_override: bool | None = None

    @property
    def inside_temperature(self):
        """Get inside temp from entity."""
        if self.temp_entity is not None:
            if get_domain(self.temp_entity) != "climate":
                temp = get_safe_state(
                    self.hass,
                    self.temp_entity,
                )
            else:
                temp = state_attr(self.hass, self.temp_entity, "current_temperature")
            return temp

    @property
    def get_current_temperature(self) -> float:
        """Get inside temperature for climate decisions."""
        if self.inside_temperature:
            return float(self.inside_temperature)

    @property
    def is_presence(self) -> bool | None:
        """Check if people are present.

        Returns:
            True: Room is occupied
            False: Room is not occupied
            None: Presence entity unavailable

        """
        # Use override if set (from coordinator's stored value)
        # Override is a tuple (use_override: bool, value: bool | None)
        if self._is_presence_override is not None:
            use_override, value = self._is_presence_override
            if use_override:
                self.logger.debug(
                    "is_presence(): Using override value: %s",
                    value,
                )
                return value
        # No presence entity configured → assume occupied
        if self.presence_entity is None:
            return True
        presence = get_safe_state(self.hass, self.presence_entity)
        # Handle unavailable presence entity
        if presence is None:
            self.logger.debug(
                "is_presence(): Presence entity unavailable, returning None"
            )
            return None
        domain = get_domain(self.presence_entity)
        if domain == "device_tracker":
            return presence == "home"
        if domain == "zone":
            return int(presence) > 0
        if domain in ["binary_sensor", "input_boolean"]:
            return presence == "on"
        return True

    @property
    def is_winter(self) -> bool:
        """Check if temperature is below threshold."""
        if self.temp_low is not None and self.get_current_temperature is not None:
            is_it = self.get_current_temperature < self.temp_low
        else:
            is_it = False

        self.logger.debug(
            "is_winter(): current_temperature < temp_low: %s < %s = %s",
            self.get_current_temperature,
            self.temp_low,
            is_it,
        )
        return is_it

    @property
    def is_summer(self) -> bool:
        """Check if inside temperature is over high threshold (room is too hot)."""
        if self.temp_high is not None and self.get_current_temperature is not None:
            is_it = self.get_current_temperature > self.temp_high
        else:
            is_it = False

        self.logger.debug(
            "is_summer(): current_temp > temp_high: %s > %s = %s",
            self.get_current_temperature,
            self.temp_high,
            is_it,
        )
        return is_it

    @property
    def has_direct_sun(self) -> bool | None:
        """Check if weather condition allows direct sunlight.

        Returns:
            True: Weather allows direct sun
            False: Weather does not allow direct sun
            None: Weather entity unavailable (unknown state)

        """
        # Use override if set (from coordinator's stored value)
        # Override is a tuple (use_override: bool, value: bool | None)
        if self._has_direct_sun_override is not None:
            use_override, value = self._has_direct_sun_override
            if use_override:
                self.logger.debug(
                    "has_direct_sun(): Using override value: %s",
                    value,
                )
                return value
        self.logger.debug(
            "has_direct_sun(): weather_condition=%s (type=%s)",
            self.weather_condition,
            type(self.weather_condition).__name__,
        )
        if self.weather_entity is None:
            self.logger.debug("has_direct_sun(): No weather entity defined")
            return True
        # Get raw state for debugging
        raw_state = self.hass.states.get(self.weather_entity)
        self.logger.debug(
            "has_direct_sun(): Raw weather state: %s (available: %s)",
            raw_state.state if raw_state else "None",
            raw_state is not None,
        )
        weather_state = get_safe_state(self.hass, self.weather_entity)
        # Handle unavailable weather entity
        if weather_state is None:
            self.logger.debug(
                "has_direct_sun(): Weather entity unavailable (state=%s), returning None",
                raw_state.state if raw_state else "no state object",
            )
            return None
        # Use configured conditions or default
        conditions = self.weather_condition
        if not conditions:
            conditions = DEFAULT_WEATHER_CONDITIONS
            self.logger.debug(
                "has_direct_sun(): No weather conditions configured, using defaults"
            )
        matches = weather_state in conditions
        self.logger.debug(
            "has_direct_sun(): Weather: %s in %s = %s",
            weather_state,
            conditions,
            matches,
        )
        return matches

    @property
    def lux(self) -> bool | None:
        """Get lux value and compare to threshold.

        Returns:
            True: Lux is below threshold (no actual sun)
            False: Lux is above threshold (has sun) or not configured
            None: Lux entity unavailable

        """
        # Use override if set (for graceful degradation with last known value)
        if self._lux_override is not None:
            return self._lux_override
        if not self._use_lux:
            return False
        if self.lux_entity is None or self.lux_threshold is None:
            return False
        value = get_safe_state(self.hass, self.lux_entity)
        if value is None:
            self.logger.debug("lux(): Lux entity unavailable, returning None")
            return None
        return float(value) <= self.lux_threshold

    @property
    def irradiance(self) -> bool | None:
        """Get irradiance value and compare to threshold.

        Returns:
            True: Irradiance is below threshold (no actual sun)
            False: Irradiance is above threshold (has sun) or not configured
            None: Irradiance entity unavailable

        """
        # Use override if set (for graceful degradation with last known value)
        if self._irradiance_override is not None:
            return self._irradiance_override
        if not self._use_irradiance:
            return False
        if self.irradiance_entity is None or self.irradiance_threshold is None:
            return False
        value = get_safe_state(self.hass, self.irradiance_entity)
        if value is None:
            self.logger.debug(
                "irradiance(): Irradiance entity unavailable, returning None"
            )
            return None
        return float(value) <= self.irradiance_threshold

    @property
    def cloud(self) -> bool | None:
        """Get cloud coverage value and compare to threshold.

        Returns:
            True: Cloud coverage is above threshold (too cloudy, no direct sun)
            False: Cloud coverage is below threshold (has sun) or not configured
            None: Cloud entity unavailable

        """
        # Use override if set (for graceful degradation with last known value)
        if self._cloud_override is not None:
            return self._cloud_override
        if not self._use_cloud:
            return False
        if self.cloud_entity is None or self.cloud_threshold is None:
            return False
        value = get_safe_state(self.hass, self.cloud_entity)
        if value is None:
            self.logger.debug("cloud(): Cloud entity unavailable, returning None")
            return None
        return float(value) >= self.cloud_threshold

    @property
    def cloud_value(self) -> float | None:
        """Get raw cloud coverage percentage value.

        Returns:
            The cloud coverage percentage (0-100) or None if unavailable.

        """
        if self.cloud_entity is None:
            return None
        value = get_safe_state(self.hass, self.cloud_entity)
        if value is None:
            return None
        return float(value)


@dataclass
class ClimateCoverState(NormalCoverState):
    """Compute state for climate control operation."""

    climate_data: ClimateCoverData

    def _has_actual_sun(self) -> bool:
        """Check if there is actual direct sunlight.

        Combines four checks:
        1. Sun geometry: direct_sun_valid (in front + not sunset + not blind spot)
        2. Weather: has_direct_sun (sunny, not cloudy)
        3. Lux/Irradiance: if configured AND enabled, reading must be >= threshold
        4. Cloud coverage: if configured AND enabled, reading must be <= threshold

        Note on lux/irradiance:
        - self.climate_data.lux returns True if reading < threshold (no actual sun)
        - self.climate_data.irradiance returns True if reading < threshold (no actual sun)

        Note on cloud:
        - self.climate_data.cloud returns True if reading > threshold (too cloudy)
        """
        # Check 1: Sun geometry
        if not self.cover.direct_sun_valid:
            self.cover.logger.debug("_has_actual_sun: No - sun not in valid position")
            return False

        # Check 2: Weather condition (None = unavailable, treated as no sun for safety)
        has_sun = self.climate_data.has_direct_sun
        if has_sun is None:
            self.cover.logger.debug(
                "_has_actual_sun: No - weather unavailable, assuming no direct sun"
            )
            return False
        if not has_sun:
            self.cover.logger.debug("_has_actual_sun: No - weather says no direct sun")
            return False

        # Check 3: Lux/irradiance override (if configured and enabled)
        # These return True when reading is BELOW threshold (meaning no actual sun)
        # None means sensor unavailable - treat as no override (trust weather)
        lux_check = self.climate_data.lux
        irradiance_check = self.climate_data.irradiance
        if lux_check is None:
            self.cover.logger.debug(
                "_has_actual_sun: Lux sensor unavailable, ignoring lux check"
            )
            lux_check = False
        if irradiance_check is None:
            self.cover.logger.debug(
                "_has_actual_sun: Irradiance sensor unavailable, ignoring irradiance"
            )
            irradiance_check = False
        if lux_check or irradiance_check:
            self.cover.logger.debug(
                "_has_actual_sun: No - lux/irradiance below threshold"
            )
            return False

        # Check 4: Cloud coverage (if configured and enabled)
        # Returns True when reading is ABOVE threshold (meaning too cloudy, no sun)
        # None means sensor unavailable - treat as no override (trust weather)
        cloud_check = self.climate_data.cloud
        if cloud_check is None:
            self.cover.logger.debug(
                "_has_actual_sun: Cloud sensor unavailable, ignoring cloud check"
            )
            cloud_check = False
        if cloud_check:
            self.cover.logger.debug(
                "_has_actual_sun: No - cloud coverage above threshold"
            )
            return False

        self.cover.logger.debug("_has_actual_sun: Yes - actual sun confirmed")
        return True

    def normal_type_cover(self) -> int:
        """Determine state for horizontal and vertical covers."""
        is_presence = self.climate_data.is_presence
        self.cover.logger.debug("Is presence? %s", is_presence)

        # None means presence entity unavailable - assume occupied for safety
        if is_presence is None:
            self.cover.logger.debug(
                "Presence unavailable, assuming occupied for comfort"
            )
            is_presence = True

        if is_presence:
            return self.normal_with_presence()

        return self.normal_without_presence()

    def normal_with_presence(self) -> int:
        """Determine state for horizontal and vertical covers with occupants.

        When occupied: block sun for comfort (against glare/sunlight).
        Temperature (summer/winter) is IGNORED in this mode.
        """
        if self._has_actual_sun():
            self.cover.logger.debug(
                "n_w_p(): Actual sun exists, calculating blocking position"
            )
            return super().get_state(has_direct_sun=True)

        self.cover.logger.debug("n_w_p(): No actual sun, using default")
        return self.cover.default

    def normal_without_presence(self) -> int:
        """Determine state for horizontal and vertical covers without occupants.

        When not occupied: optimize temperature based on actual sunlight.
        - Summer: close (0) to block heat
        - Winter: open (100) to let heat in
        - Intermediate: calculated position
        """
        if not self._has_actual_sun():
            self.cover.logger.debug("n_wo_p(): No actual sun, using default")
            return self.cover.default

        # Actual sun exists - optimize by temperature
        if self.climate_data.is_summer:
            self.cover.logger.debug("n_wo_p(): Summer + actual sun, closing (0)")
            return 0

        if self.climate_data.is_winter:
            self.cover.logger.debug("n_wo_p(): Winter + actual sun, opening (100)")
            return 100

        self.cover.logger.debug("n_wo_p(): Intermediate temp, using calculated")
        return super().get_state(has_direct_sun=True)

    def tilt_with_presence(self, degrees: int) -> int:
        """Determine state for tilted blinds with occupants.

        When occupied: block sun for comfort (against glare/sunlight).
        Temperature (summer/winter) is IGNORED in this mode.
        """
        if self._has_actual_sun():
            self.cover.logger.debug(
                "t_w_p(): Actual sun exists, calculating blocking angle"
            )
            return super().get_state(has_direct_sun=True)

        self.cover.logger.debug("t_w_p(): No actual sun, using default")
        return self.cover.default

    def tilt_without_presence(self, degrees: int) -> int:
        """Determine state for tilted blinds without occupants.

        When not occupied: optimize temperature based on actual sunlight.
        - Summer: fully closed (0) to block heat
        - Winter mode2: parallel to sun beams for max heat gain
        - Winter mode1: fully open (100) to let heat in
        - Intermediate: calculated position
        """
        if not self._has_actual_sun():
            self.cover.logger.debug("t_wo_p(): No actual sun, using default")
            return self.cover.default

        # Actual sun exists - optimize by temperature
        if self.climate_data.is_summer:
            self.cover.logger.debug("t_wo_p(): Summer + actual sun, closing (0)")
            return 0

        if self.climate_data.is_winter:
            if self.cover.mode == "mode2":
                # Bi-directional: parallel to sun beams for max heat
                beta = np.rad2deg(self.cover.beta)
                tilt = (beta + 90) / degrees * 100
                self.cover.logger.debug(
                    "t_wo_p(): Winter mode2, parallel to sun (%s)", tilt
                )
                return tilt
            # Single direction: fully open
            self.cover.logger.debug("t_wo_p(): Winter mode1, opening (100)")
            return 100

        self.cover.logger.debug("t_wo_p(): Intermediate temp, using calculated")
        return super().get_state(has_direct_sun=True)

    def tilt_state(self):
        """Add tilt specific controls."""
        degrees = 90
        if self.cover.mode == "mode2":
            degrees = 180

        is_presence = self.climate_data.is_presence
        # None means presence entity unavailable - assume occupied for safety
        if is_presence is None:
            self.cover.logger.debug(
                "tilt_state: Presence unavailable, assuming occupied for comfort"
            )
            is_presence = True

        if is_presence:
            return self.tilt_with_presence(degrees)
        return self.tilt_without_presence(degrees)

    def get_state(self) -> int:
        """Return state."""
        result = self.normal_type_cover()
        if self.climate_data.blind_type == "cover_tilt":
            result = self.tilt_state()
        if self.cover.apply_max_position and result > self.cover.max_pos:
            self.cover.logger.debug(
                "Climate state: Max position applied (%s > %s)",
                result,
                self.cover.max_pos,
            )
            return self.cover.max_pos
        if self.cover.apply_min_position and result < self.cover.min_pos:
            self.cover.logger.debug(
                "Climate state: Min position applied (%s < %s)",
                result,
                self.cover.min_pos,
            )
            return self.cover.min_pos
        return result


@dataclass
class AdaptiveVerticalCover(AdaptiveGeneralCover):
    """Calculate state for Vertical blinds."""

    distance: float
    h_win: float  # cover_top - height from floor to top of cover
    cover_bottom: float = 0.0  # height from floor to bottom of fully extended cover
    shaded_area_height: float = 0.0  # height of the area to protect from sun

    @property
    def cover_height(self) -> float:
        """Total cover extension range."""
        return self.h_win - self.cover_bottom

    def calculate_position(self) -> float:
        """Calculate cover position height to protect shaded area.

        Returns the height from floor that the cover bottom needs to reach
        to cast a shadow that protects the shaded area from direct sunlight.
        """
        # Effective distance accounting for sun azimuth angle relative to window
        d_eff = self.distance / cos(rad(self.gamma))

        # Height at which cover bottom must be to cast shadow at shaded_area_height
        cover_position = self.shaded_area_height + d_eff * tan(rad(self.sol_elev))

        # Clip to valid range (between cover_bottom and cover_top)
        return np.clip(cover_position, self.cover_bottom, self.h_win)

    def calculate_percentage(self) -> float:
        """Convert cover position to open percentage.

        0% = cover fully extended (closed)
        100% = cover fully retracted (open)
        """
        position = self.calculate_position()
        self.logger.debug(
            "Converting position to percentage: (%s - %s) / %s * 100",
            position,
            self.cover_bottom,
            self.cover_height,
        )
        result = (position - self.cover_bottom) / self.cover_height * 100
        return round(result)


@dataclass
class AdaptiveHorizontalCover(AdaptiveVerticalCover):
    """Calculate state for Horizontal blinds."""

    awn_length: float = 2.1  # default required due to parent class having defaults
    awn_angle: float = 0.0  # default required due to parent class having defaults

    def calculate_position(self) -> float:
        """Calculate awn length from blind height."""
        awn_angle = 90 - self.awn_angle
        a_angle = 90 - self.sol_elev
        c_angle = 180 - awn_angle - a_angle

        vertical_position = super().calculate_position()
        length = ((self.h_win - vertical_position) * sin(rad(a_angle))) / sin(
            rad(c_angle)
        )
        # return np.clip(length, 0, self.awn_length)
        return length

    def calculate_percentage(self) -> float:
        """Convert awn length to percentage or default value."""
        result = self.calculate_position() / self.awn_length * 100
        return round(result)


@dataclass
class AdaptiveTiltCover(AdaptiveGeneralCover):
    """Calculate state for tilted blinds."""

    slat_distance: float
    depth: float
    mode: str

    @property
    def beta(self):
        """Calculate beta."""
        beta = np.arctan(tan(rad(self.sol_elev)) / cos(rad(self.gamma)))
        return beta

    def calculate_position(self) -> float:
        """Calculate position of venetian blinds.

        https://www.mdpi.com/1996-1073/13/7/1731
        """
        beta = self.beta

        slat = 2 * np.arctan(
            (
                tan(beta)
                + np.sqrt(
                    (tan(beta) ** 2) - ((self.slat_distance / self.depth) ** 2) + 1
                )
            )
            / (1 + self.slat_distance / self.depth)
        )
        result = np.rad2deg(slat)

        return result

    def calculate_percentage(self):
        """Convert tilt angle to percentages or default value."""
        # 0 degrees is closed, 90 degrees is open, 180 degrees is closed
        percentage_single = self.calculate_position() / 90 * 100  # single directional
        percentage_bi = self.calculate_position() / 180 * 100  # bi-directional

        if self.mode == "mode1":
            percentage = percentage_single
        else:
            percentage = percentage_bi

        return round(percentage)
