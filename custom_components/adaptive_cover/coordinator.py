"""The Coordinator for Adaptive Cover."""

from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pytz
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import state_attr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from .room_coordinator import RoomCoordinator

from .config_context_adapter import ConfigContextAdapter

from .calculation import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    ClimateCoverData,
    ClimateCoverState,
    NormalCoverState,
)
from .const import (
    _LOGGER,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_CLIMATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_COVER_BOTTOM,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_LIST,
    CONF_INTERP_LIST_NEW,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_IRRADIANCE_ENTITY,
    CONF_IRRADIANCE_THRESHOLD,
    CONF_LENGTH_AWNING,
    CONF_LUX_ENTITY,
    CONF_LUX_THRESHOLD,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MIN_POSITION,
    CONF_CLOUD_ENTITY,
    CONF_CLOUD_THRESHOLD,
    CONF_PRESENCE_ENTITY,
    CONF_RESET_AT_MIDNIGHT,
    CONF_RETURN_SUNSET,
    CONF_SHADED_AREA_HEIGHT,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_TRANSPARENT_BLIND,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    COMFORT_STATUS_COMFORTABLE,
    COMFORT_STATUS_TOO_COLD,
    COMFORT_STATUS_TOO_HOT,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    CONTROL_MODE_FORCE,
    DOMAIN,
    LOGGER,
    ROOM_SHARED_OPTIONS,
)
from .helpers import get_datetime_from_str, get_last_updated, get_safe_state

# Storage constants for persisting last known sensor values
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "adaptive_cover"


@dataclass
class StateChangedData:
    """StateChangedData class."""

    entity_id: str
    old_state: State | None
    new_state: State | None


@dataclass
class AdaptiveCoverData:
    """AdaptiveCoverData class."""

    climate_mode_toggle: bool
    states: dict
    attributes: dict


class AdaptiveDataUpdateCoordinator(DataUpdateCoordinator[AdaptiveCoverData]):
    """Adaptive cover data update coordinator."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        room_coordinator: RoomCoordinator | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, LOGGER, name=DOMAIN)
        self.config_entry = config_entry

        self.logger = ConfigContextAdapter(_LOGGER)
        self.logger.set_config_name(self.config_entry.data.get("name"))

        # Room coordinator reference (None for standalone covers)
        self._room_coordinator = room_coordinator

        self._cover_type = self.config_entry.data.get("sensor_type")
        self._climate_mode = self._get_option(CONF_CLIMATE_MODE, False)
        self._inverse_state = self.config_entry.options.get(CONF_INVERSE_STATE, False)
        self._use_interpolation = self.config_entry.options.get(CONF_INTERP, False)
        self._track_end_time = self._get_option(CONF_RETURN_SUNSET)

        # Sensor toggles - only used for standalone covers (room manages these otherwise)
        self._lux_toggle = None
        self._irradiance_toggle = None
        self._cloud_toggle = None
        self._weather_toggle = None

        self._start_time = None
        self._sun_end_time = None
        self._sun_start_time = None

        # Control mode: "off", "on", "auto" - only used for standalone covers
        self._control_mode = CONTROL_MODE_AUTO
        self._reset_at_midnight = self._get_option(CONF_RESET_AT_MIDNIGHT, True)
        self._midnight_unsub = None

        self.state_change = False
        self.cover_state_change = False
        self.first_refresh = False
        self.timed_refresh = False
        self.climate_state = None
        self.comfort_status = COMFORT_STATUS_COMFORTABLE
        self.state_change_data: StateChangedData | None = None
        self.manager = AdaptiveCoverManager(self.logger, self)
        self.wait_for_target = {}
        self.target_call = {}
        self.ignore_intermediate_states = self._get_option(
            CONF_MANUAL_IGNORE_INTERMEDIATE, False
        )
        self._update_listener = None
        self._scheduled_time = dt.datetime.now()

        self._cached_options = None

        # Last known sensor values for graceful degradation
        # These are persisted across HA restarts (only for standalone covers)
        self._last_known: dict[str, bool | None] = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }
        # Current availability status (True = available, False = using cached)
        self._sensor_available: dict[str, bool] = {
            "has_direct_sun": True,
            "is_presence": True,
        }
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{self.config_entry.entry_id}",
        )

    def _get_option(self, key: str, default=None):
        """Get option from room if available for shared options, else from own config."""
        if self._room_coordinator and key in ROOM_SHARED_OPTIONS:
            return self._room_coordinator.get_option(key, default)
        return self.config_entry.options.get(key, default)

    @property
    def has_room(self) -> bool:
        """Check if this cover is part of a room."""
        return self._room_coordinator is not None

    @property
    def room_coordinator(self) -> RoomCoordinator | None:
        """Get the room coordinator if this cover is part of a room."""
        return self._room_coordinator

    def set_room_coordinator(self, room_coordinator: RoomCoordinator) -> None:
        """Set the room coordinator for late connection.

        This is called when a cover loads before its room, and the room
        later discovers it and establishes the connection.
        """
        if self._room_coordinator is not None:
            self.logger.debug("Room coordinator already set, skipping")
            return

        self.logger.debug("Late connecting to room coordinator")
        self._room_coordinator = room_coordinator
        # Trigger refresh to use room's settings
        self.hass.async_create_task(self.async_refresh())

    async def async_config_entry_first_refresh(self) -> None:
        """Config entry first refresh."""
        self.first_refresh = True
        # Load last known sensor values from storage
        await self._async_load_last_known()
        await super().async_config_entry_first_refresh()
        self.logger.debug("Config entry first refresh")

    async def _async_load_last_known(self) -> None:
        """Load last known sensor values from storage."""
        data = await self._store.async_load()
        if data:
            self._last_known.update(data)
            self.logger.debug("Loaded last known values from storage: %s", data)

    async def _async_save_last_known(self) -> None:
        """Save last known sensor values to storage."""
        await self._store.async_save(self._last_known)
        self.logger.debug("Saved last known values to storage: %s", self._last_known)

    async def _get_sensor_values_with_fallback(
        self, climate: ClimateCoverData
    ) -> tuple[bool | None, bool | None, bool | None, bool | None, bool | None]:
        """Get sensor values with fallback to last known values.

        For each sensor:
        - If current value is available (not None), use it and update last known
        - If current value is unavailable (None), use last known value

        Returns:
            Tuple of (is_presence, has_direct_sun, lux, irradiance, cloud) values.

        """
        values_changed = False

        # Handle is_presence
        current_presence = climate.is_presence
        self.logger.debug(
            "Sensor fallback: is_presence current=%s, last_known=%s",
            current_presence,
            self._last_known["is_presence"],
        )
        if current_presence is not None:
            # Sensor available - use current and update last known
            self._sensor_available["is_presence"] = True
            if self._last_known["is_presence"] != current_presence:
                self._last_known["is_presence"] = current_presence
                values_changed = True
            is_presence = current_presence
        else:
            # Sensor unavailable - use last known (may still be None if never available)
            self._sensor_available["is_presence"] = False
            is_presence = self._last_known["is_presence"]
            self.logger.debug(
                "Presence sensor unavailable, using last known: %s", is_presence
            )

        # Handle has_direct_sun
        current_sun = climate.has_direct_sun
        self.logger.debug(
            "Sensor fallback: has_direct_sun current=%s, last_known=%s",
            current_sun,
            self._last_known["has_direct_sun"],
        )
        if current_sun is not None:
            # Sensor available - use current and update last known
            self._sensor_available["has_direct_sun"] = True
            if self._last_known["has_direct_sun"] != current_sun:
                self._last_known["has_direct_sun"] = current_sun
                values_changed = True
            has_direct_sun = current_sun
        else:
            # Sensor unavailable - use last known (may still be None if never available)
            self._sensor_available["has_direct_sun"] = False
            has_direct_sun = self._last_known["has_direct_sun"]
            self.logger.debug(
                "Weather sensor unavailable, using last known: %s", has_direct_sun
            )

        # Handle lux (used indirectly via climate_data.lux in _has_actual_sun)
        current_lux = climate.lux
        if current_lux is not None:
            if self._last_known["lux"] != current_lux:
                self._last_known["lux"] = current_lux
                values_changed = True
            lux_value = current_lux
        else:
            lux_value = self._last_known["lux"]
            self.logger.debug("Lux sensor unavailable, using last known: %s", lux_value)

        # Handle irradiance
        current_irradiance = climate.irradiance
        if current_irradiance is not None:
            if self._last_known["irradiance"] != current_irradiance:
                self._last_known["irradiance"] = current_irradiance
                values_changed = True
            irradiance_value = current_irradiance
        else:
            irradiance_value = self._last_known["irradiance"]
            self.logger.debug(
                "Irradiance sensor unavailable, using last known: %s",
                irradiance_value,
            )

        # Handle cloud
        current_cloud = climate.cloud
        if current_cloud is not None:
            if self._last_known["cloud"] != current_cloud:
                self._last_known["cloud"] = current_cloud
                values_changed = True
            cloud_value = current_cloud
        else:
            cloud_value = self._last_known["cloud"]
            self.logger.debug(
                "Cloud sensor unavailable, using last known: %s",
                cloud_value,
            )

        # Save to storage if any value changed
        if values_changed:
            await self._async_save_last_known()

        return is_presence, has_direct_sun, lux_value, irradiance_value, cloud_value

    async def async_timed_refresh(self, event) -> None:
        """Control state at end time."""

        now = dt.datetime.now()
        if self.end_time is not None:
            time = self.end_time
        if self.end_time_entity is not None:
            time = get_safe_state(self.hass, self.end_time_entity)

        self.logger.debug("Checking timed refresh. End time: %s, now: %s", time, now)

        time_check = now - get_datetime_from_str(time)
        if time is not None and (time_check <= dt.timedelta(seconds=1)):
            self.timed_refresh = True
            self.logger.debug("Timed refresh triggered")
            await self.async_refresh()
        else:
            self.logger.debug("Timed refresh, but: not equal to end time")

    async def async_check_entity_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Entity state change")
        self.state_change = True
        await self.async_refresh()

    async def async_check_cover_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Cover state change")
        data = event.data
        if data["old_state"] is None:
            self.logger.debug("Old state is None")
            return
        self.state_change_data = StateChangedData(
            data["entity_id"], data["old_state"], data["new_state"]
        )
        if self.state_change_data.old_state.state != "unknown":
            self.cover_state_change = True
            self.process_entity_state_change()
            await self.async_refresh()
        else:
            self.logger.debug("Old state is unknown, not processing")

    def process_entity_state_change(self):
        """Process state change event."""
        event = self.state_change_data
        self.logger.debug("Processing state change event: %s", event)
        entity_id = event.entity_id
        if self.ignore_intermediate_states and event.new_state.state in [
            "opening",
            "closing",
        ]:
            self.logger.debug("Ignoring intermediate state change for %s", entity_id)
            return
        if self.wait_for_target.get(entity_id):
            position = event.new_state.attributes.get(
                "current_position"
                if self._cover_type != "cover_tilt"
                else "current_tilt_position"
            )
            if position == self.target_call.get(entity_id):
                self.wait_for_target[entity_id] = False
                self.logger.debug("Position %s reached for %s", position, entity_id)
            self.logger.debug("Wait for target: %s", self.wait_for_target)
        else:
            self.logger.debug("No wait for target call for %s", entity_id)

    @callback
    def _async_cancel_update_listener(self) -> None:
        """Cancel the scheduled update."""
        if self._update_listener:
            self._update_listener()
            self._update_listener = None

    async def async_timed_end_time(self) -> None:
        """Control state at end time."""
        self.logger.debug("Scheduling end time update at %s", self._end_time)
        self._async_cancel_update_listener()
        self.logger.debug(
            "End time: %s, Track end time: %s, Scheduled time: %s, Condition: %s",
            self._end_time,
            self._track_end_time,
            self._scheduled_time,
            self._end_time > self._scheduled_time,
        )
        self._update_listener = async_track_point_in_time(
            self.hass, self.async_timed_refresh, self._end_time
        )
        self._scheduled_time = self._end_time

    def setup_midnight_reset(self) -> None:
        """Set up midnight reset listener."""
        # If part of a room, delegate to room coordinator
        if self._room_coordinator:
            self._room_coordinator.setup_midnight_reset()
            return

        if self._midnight_unsub:
            self._midnight_unsub()
            self._midnight_unsub = None

        if self._reset_at_midnight:
            self.logger.debug("Setting up midnight reset listener")
            self._midnight_unsub = async_track_time_change(
                self.hass,
                self._async_midnight_reset,
                hour=0,
                minute=0,
                second=0,
            )

    @callback
    def _async_midnight_reset(self, now: dt.datetime) -> None:
        """Reset control mode to AUTO at midnight."""
        self.logger.info("Midnight reset: Setting control mode to AUTO")
        self.control_mode = CONTROL_MODE_AUTO
        self.hass.async_create_task(self.async_refresh())

    async def _async_update_data(self) -> AdaptiveCoverData:
        self.logger.debug("Updating data")
        if self.first_refresh:
            self._cached_options = self.config_entry.options

        options = self.config_entry.options
        self._update_options(options)

        # Get data for the blind
        cover_data = self.get_blind_data(options=options)

        # Update manager with covers
        self._update_manager_and_covers()

        # Always create climate data for is_presence and has_direct_sun sensors
        climate = ClimateCoverData(*self.get_climate_data(options))

        # Get current sensor values and apply graceful degradation
        # If sensor is unavailable (None), use last known value
        (
            self._is_presence,
            self._has_direct_sun,
            lux_value,
            irradiance_value,
            cloud_value,
        ) = await self._get_sensor_values_with_fallback(climate)

        # Store raw cloud coverage value for sensor display
        self._cloud_coverage_value = climate.cloud_value

        # Set overrides so calculation uses the same values as the sensors
        # Override format is (use_override: bool, value: bool | None)
        # We ALWAYS set use_override=True so the calculation uses our value
        # (which may be current or last known, determined by _get_sensor_values_with_fallback)
        climate._is_presence_override = (True, self._is_presence)
        # When weather toggle is disabled, default to "has light" (True) to encourage calculated position
        climate._has_direct_sun_override = (
            True,
            self._has_direct_sun if self._weather_toggle else True,
        )
        self.logger.debug(
            "Set overrides: is_presence=%s, has_direct_sun=%s",
            self._is_presence,
            self._has_direct_sun,
        )
        # Only set lux/irradiance/cloud overrides if we're using a fallback value
        # (i.e., current sensor is unavailable but we have a last known value)
        if climate.lux is None and lux_value is not None:
            climate._lux_override = lux_value
        if climate.irradiance is None and irradiance_value is not None:
            climate._irradiance_override = irradiance_value
        if climate.cloud is None and cloud_value is not None:
            climate._cloud_override = cloud_value

        # Access climate data if climate mode is enabled
        if self._climate_mode:
            self.climate_mode_data(cover_data, climate)
        else:
            self.logger.debug("Comfort status is %s", self.comfort_status)

        # calculate the state of the cover (pass weather check for basic mode)
        self.normal_cover_state = NormalCoverState(cover_data)
        self.logger.debug(
            "Determined normal cover state to be %s", self.normal_cover_state
        )

        # In ON mode (basic sun position), ignore all sensor toggles
        # In AUTO mode, apply sensor toggles
        if self.is_climate_mode:
            # AUTO mode: apply weather and cloud toggles
            has_direct_sun = self._has_direct_sun if self._weather_toggle else True
            cloud_override = climate.cloud if self._cloud_toggle else None
        else:
            # ON mode (or OFF mode): pure sun position, no sensor influence
            has_direct_sun = True
            cloud_override = None

        self.default_state = round(
            self.normal_cover_state.get_state(
                has_direct_sun=has_direct_sun,
                cloud_override=cloud_override,
            )
        )
        self.logger.debug("Determined default state to be %s", self.default_state)
        state = self.state

        if (
            self._end_time
            and self._track_end_time
            and self._end_time > self._scheduled_time
        ):
            await self.async_timed_end_time()

        # Handle types of changes
        if self.state_change:
            await self.async_handle_state_change(state, options)
        if self.cover_state_change:
            await self.async_handle_cover_state_change(state)
        if self.first_refresh:
            await self.async_handle_first_refresh(state, options)
        if self.timed_refresh:
            await self.async_handle_timed_refresh(options)

        normal_cover = self.normal_cover_state.cover
        # Run the solar_times method in a separate thread
        if (
            self.first_refresh
            or self._sun_start_time is None
            or dt.datetime.now(pytz.UTC).date() != self._sun_start_time.date()
        ):
            self.logger.debug("Calculating solar times")
            loop = asyncio.get_event_loop()
            start, end = await loop.run_in_executor(None, normal_cover.solar_times)
            self._sun_start_time = start
            self._sun_end_time = end
            self.logger.debug("Sun start time: %s, Sun end time: %s", start, end)
        else:
            start, end = self._sun_start_time, self._sun_end_time
        return AdaptiveCoverData(
            climate_mode_toggle=self.is_climate_mode,
            states={
                "state": state,
                "start": start,
                "end": end,
                "comfort_status": self.comfort_status,
                "sun_motion": normal_cover.valid,
                "is_presence": self._is_presence,
                "has_direct_sun": self._has_direct_sun,
                "is_presence_available": self._sensor_available["is_presence"],
                "has_direct_sun_available": self._sensor_available["has_direct_sun"],
                "cloud_coverage": self._cloud_coverage_value,
            },
            attributes={
                "default": options.get(CONF_DEFAULT_HEIGHT),
                "sunset_default": options.get(CONF_SUNSET_POS),
                "sunset_offset": options.get(CONF_SUNSET_OFFSET),
                "azimuth_window": options.get(CONF_AZIMUTH),
                "field_of_view": [
                    options.get(CONF_FOV_LEFT),
                    options.get(CONF_FOV_RIGHT),
                ],
                "blind_spot": options.get(CONF_BLIND_SPOT_ELEVATION),
            },
        )

    async def async_handle_state_change(self, state: int, options):
        """Handle state change from tracked entities."""
        if self.is_control_enabled:
            for cover in self.entities:
                await self.async_handle_call_service(cover, state, options)
        else:
            self.logger.debug("State change but control mode is off")
        self.state_change = False
        self.logger.debug("State change handled")

    async def async_handle_cover_state_change(self, state: int):
        """Handle state change from assigned covers."""
        if self.is_control_enabled:
            self.manager.handle_state_change(
                self.state_change_data,
                state,
                self._cover_type,
                self.wait_for_target,
                self.manual_threshold,
            )
        self.cover_state_change = False
        self.logger.debug("Cover state change handled")

    async def async_handle_first_refresh(self, state: int, options):
        """Handle first refresh."""
        if self.is_control_enabled:
            for cover in self.entities:
                if self.check_adaptive_time and self.check_position_delta(
                    cover, state, options
                ):
                    await self.async_set_position(cover, state)
        else:
            self.logger.debug("First refresh but control mode is off")
        self.first_refresh = False
        self.logger.debug("First refresh handled")

    async def async_handle_timed_refresh(self, options):
        """Handle timed refresh."""
        self.logger.debug(
            "This is a timed refresh, using sunset position: %s",
            options.get(CONF_SUNSET_POS),
        )
        if self.is_control_enabled:
            for cover in self.entities:
                await self.async_set_manual_position(
                    cover,
                    (
                        inverse_state(options.get(CONF_SUNSET_POS))
                        if self._inverse_state
                        else options.get(CONF_SUNSET_POS)
                    ),
                )
        else:
            self.logger.debug("Timed refresh but control mode is off")
        self.timed_refresh = False
        self.logger.debug("Timed refresh handled")

    async def async_handle_call_service(self, entity, state: int, options):
        """Handle call service."""
        if (
            self.check_adaptive_time
            and self.check_position_delta(entity, state, options)
            and self.check_time_delta(entity)
        ):
            await self.async_set_position(entity, state)

    async def async_set_position(self, entity, state: int):
        """Call service to set cover position."""
        await self.async_set_manual_position(entity, state)

    async def async_set_manual_position(self, entity, state):
        """Call service to set cover position."""
        if self.check_position(entity, state):
            service = SERVICE_SET_COVER_POSITION
            service_data = {}
            service_data[ATTR_ENTITY_ID] = entity

            if self._cover_type == "cover_tilt":
                service = SERVICE_SET_COVER_TILT_POSITION
                service_data[ATTR_TILT_POSITION] = state
            else:
                service_data[ATTR_POSITION] = state

            self.wait_for_target[entity] = True
            self.target_call[entity] = state
            self.logger.debug(
                "Set wait for target %s and target call %s",
                self.wait_for_target,
                self.target_call,
            )
            self.logger.debug("Run %s with data %s", service, service_data)
            await self.hass.services.async_call(COVER_DOMAIN, service, service_data)

    async def async_force_update_covers(self):
        """Force update all covers to the calculated position immediately.

        This bypasses the normal delta checks and sends the position command right away.
        """
        if not self.is_control_enabled:
            self.logger.info("Force update skipped: control mode is disabled")
            return

        # Refresh to get the latest calculated position
        await self.async_refresh()

        # Get the current calculated state
        state = self.state
        self.logger.info("Force updating covers to position: %s", state)

        # Send position to all covers, bypassing delta checks
        for cover in self.entities:
            await self.async_set_position(cover, state)

        self.logger.info("Force update completed")

    def _update_options(self, options):
        """Update options."""
        # Cover-specific options always come from own config
        self.entities = options.get(CONF_ENTITIES, [])
        self.start_value = options.get(CONF_INTERP_START)
        self.end_value = options.get(CONF_INTERP_END)
        self.normal_list = options.get(CONF_INTERP_LIST)
        self.new_list = options.get(CONF_INTERP_LIST_NEW)

        # Shared options - use _get_option to check room first
        self.min_change = self._get_option(CONF_DELTA_POSITION, 1)
        self.time_threshold = self._get_option(CONF_DELTA_TIME, 2)
        self.start_time = self._get_option(CONF_START_TIME)
        self.start_time_entity = self._get_option(CONF_START_ENTITY)
        self.end_time = self._get_option(CONF_END_TIME)
        self.end_time_entity = self._get_option(CONF_END_ENTITY)
        self.manual_threshold = self._get_option(CONF_MANUAL_THRESHOLD)
        self._reset_at_midnight = self._get_option(CONF_RESET_AT_MIDNIGHT, True)

    def _update_manager_and_covers(self):
        self.manager.add_covers(self.entities)

    def get_blind_data(self, options):
        """Assign correct class for type of blind."""
        if self._cover_type == "cover_blind":
            cover_data = AdaptiveVerticalCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                *self.common_data(options),
                *self.vertical_data(options),
            )
        if self._cover_type == "cover_awning":
            cover_data = AdaptiveHorizontalCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                *self.common_data(options),
                *self.vertical_data(options),
                *self.horizontal_data(options),
            )
        if self._cover_type == "cover_tilt":
            cover_data = AdaptiveTiltCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                *self.common_data(options),
                *self.tilt_data(options),
            )
        return cover_data

    @property
    def check_adaptive_time(self):
        """Check if time is within start and end times."""
        if self._start_time and self._end_time and self._start_time > self._end_time:
            self.logger.error("Start time is after end time")
        return self.before_end_time and self.after_start_time

    @property
    def after_start_time(self):
        """Check if time is after start time."""
        now = dt.datetime.now()
        if self.start_time_entity is not None:
            time = get_datetime_from_str(
                get_safe_state(self.hass, self.start_time_entity)
            )
            self.logger.debug(
                "Start time: %s, now: %s, now >= time: %s ", time, now, now >= time
            )
            self._start_time = time
            return now >= time
        if self.start_time is not None:
            time = get_datetime_from_str(self.start_time)

            self.logger.debug(
                "Start time: %s, now: %s, now >= time: %s", time, now, now >= time
            )
            self._start_time
            return now >= time
        return True

    @property
    def _end_time(self) -> dt.datetime | None:
        """Get end time."""
        time = None
        if self.end_time_entity is not None:
            time = get_datetime_from_str(
                get_safe_state(self.hass, self.end_time_entity)
            )
        elif self.end_time is not None:
            time = get_datetime_from_str(self.end_time)
            if time.time() == dt.time(0, 0):
                time = time + dt.timedelta(days=1)
        return time

    @property
    def before_end_time(self):
        """Check if time is before end time."""
        if self._end_time is not None:
            now = dt.datetime.now()
            self.logger.debug(
                "End time: %s, now: %s, now < time: %s",
                self._end_time,
                now,
                now < self._end_time,
            )
            return now < self._end_time
        return True

    def _get_current_position(self, entity) -> int | None:
        """Get current position of cover."""
        if self._cover_type == "cover_tilt":
            return state_attr(self.hass, entity, "current_tilt_position")
        return state_attr(self.hass, entity, "current_position")

    def check_position(self, entity, state):
        """Check if position is different as state."""
        position = self._get_current_position(entity)
        if position is not None:
            return position != state
        self.logger.debug("Cover is already at position %s", state)
        return False

    def check_position_delta(self, entity, state: int | None, options):
        """Check cover positions to reduce calls."""
        if state is None:
            return False
        position = self._get_current_position(entity)
        if position is not None:
            condition = abs(position - state) >= self.min_change
            self.logger.debug(
                "Entity: %s,  position: %s, state: %s, delta position: %s, min_change: %s, condition: %s",
                entity,
                position,
                state,
                abs(position - state),
                self.min_change,
                condition,
            )
            if state in [
                options.get(CONF_SUNSET_POS),
                options.get(CONF_DEFAULT_HEIGHT),
                0,
                100,
            ]:
                condition = True
            return condition
        return True

    def check_time_delta(self, entity):
        """Check if time delta is passed."""
        now = dt.datetime.now(dt.UTC)
        last_updated = get_last_updated(entity, self.hass)
        if last_updated is not None:
            condition = now - last_updated >= dt.timedelta(minutes=self.time_threshold)
            self.logger.debug(
                "Entity: %s, time delta: %s, threshold: %s, condition: %s",
                entity,
                now - last_updated,
                self.time_threshold,
                condition,
            )
            return condition
        return True

    @property
    def pos_sun(self):
        """Fetch information for sun position."""
        return [
            state_attr(self.hass, "sun.sun", "azimuth"),
            state_attr(self.hass, "sun.sun", "elevation"),
        ]

    def common_data(self, options):
        """Update shared parameters."""
        return [
            options.get(CONF_SUNSET_POS),
            options.get(CONF_SUNSET_OFFSET),
            options.get(CONF_SUNRISE_OFFSET, options.get(CONF_SUNSET_OFFSET)),
            self.hass.config.time_zone,
            options.get(CONF_FOV_LEFT),
            options.get(CONF_FOV_RIGHT),
            options.get(CONF_AZIMUTH),
            options.get(CONF_DEFAULT_HEIGHT),
            options.get(CONF_MAX_POSITION),
            options.get(CONF_MIN_POSITION),
            options.get(CONF_ENABLE_MAX_POSITION, False),
            options.get(CONF_ENABLE_MIN_POSITION, False),
            options.get(CONF_BLIND_SPOT_LEFT),
            options.get(CONF_BLIND_SPOT_RIGHT),
            options.get(CONF_BLIND_SPOT_ELEVATION),
            options.get(CONF_ENABLE_BLIND_SPOT, False),
            options.get(CONF_MIN_ELEVATION, None),
            options.get(CONF_MAX_ELEVATION, None),
        ]

    def get_climate_data(self, options):
        """Update climate data."""
        # Climate data uses shared options from room if available
        return [
            self.hass,
            self.logger,
            self._get_option(CONF_TEMP_ENTITY),
            self._get_option(CONF_TEMP_LOW),
            self._get_option(CONF_TEMP_HIGH),
            self._get_option(CONF_PRESENCE_ENTITY),
            self._get_option(CONF_WEATHER_ENTITY),
            self._get_option(CONF_WEATHER_STATE),
            self._cover_type,
            self._get_option(CONF_TRANSPARENT_BLIND),
            self._get_option(CONF_LUX_ENTITY),
            self._get_option(CONF_IRRADIANCE_ENTITY),
            self._get_option(CONF_LUX_THRESHOLD),
            self._get_option(CONF_IRRADIANCE_THRESHOLD),
            self.lux_toggle,  # Use property to get from room if available
            self.irradiance_toggle,  # Use property to get from room if available
            self._get_option(CONF_CLOUD_ENTITY),
            self._get_option(CONF_CLOUD_THRESHOLD),
            self.cloud_toggle,  # Use property to get from room if available
        ]

    def climate_mode_data(self, cover_data, climate):
        """Update climate mode data and comfort status."""
        self.climate_state = round(ClimateCoverState(cover_data, climate).get_state())
        climate_data = ClimateCoverState(cover_data, climate).climate_data
        if climate_data.is_summer and self.is_climate_mode:
            self.comfort_status = COMFORT_STATUS_TOO_HOT
        if climate_data.is_winter and self.is_climate_mode:
            self.comfort_status = COMFORT_STATUS_TOO_COLD
        self.logger.debug(
            "Climate mode comfort status was set to %s", self.comfort_status
        )

    def vertical_data(self, options):
        """Update data for vertical blinds."""
        return [
            options.get(CONF_DISTANCE),
            options.get(CONF_HEIGHT_WIN),
            options.get(CONF_COVER_BOTTOM, 0),
            options.get(CONF_SHADED_AREA_HEIGHT, 0),
        ]

    def horizontal_data(self, options):
        """Update data for horizontal blinds."""
        return [
            options.get(CONF_LENGTH_AWNING),
            options.get(CONF_AWNING_ANGLE),
        ]

    def tilt_data(self, options):
        """Update data for tilted blinds."""
        return [
            options.get(CONF_TILT_DISTANCE),
            options.get(CONF_TILT_DEPTH),
            options.get(CONF_TILT_MODE),
        ]

    @property
    def state(self) -> int:
        """Handle the output of the state based on mode."""
        self.logger.debug(
            "Basic position: %s; Climate position: %s; Using climate mode? %s",
            self.default_state,
            self.climate_state,
            self.is_climate_mode,
        )
        if self.is_climate_mode:
            state = self.climate_state
        else:
            state = self.default_state

        if self._use_interpolation:
            self.logger.debug("Interpolating position: %s", state)
            state = self.interpolate_states(state)

        if self._inverse_state and self._use_interpolation:
            self.logger.info(
                "Inverse state is not supported with interpolation, you can inverse the state by arranging the list from high to low"
            )

        if self._inverse_state and not self._use_interpolation:
            state = inverse_state(state)
            self.logger.debug("Inversed position: %s", state)

        self.logger.debug("Final position to use: %s", state)
        return state

    def interpolate_states(self, state):
        """Interpolate states."""
        normal_range = [0, 100]
        new_range = []
        if self.start_value and self.end_value:
            new_range = [self.start_value, self.end_value]
        if self.normal_list and self.new_list:
            normal_range = list(map(int, self.normal_list))
            new_range = list(map(int, self.new_list))
        if new_range:
            state = np.interp(state, normal_range, new_range)
            if state == new_range[0]:
                state = 0
            if state == new_range[-1]:
                state = 100
        return state

    @property
    def control_mode(self):
        """Get control mode (off/on/auto)."""
        if self._room_coordinator:
            return self._room_coordinator.control_mode
        return self._control_mode

    @control_mode.setter
    def control_mode(self, value):
        """Set control mode and notify select entity."""
        if value in (CONTROL_MODE_DISABLED, CONTROL_MODE_FORCE, CONTROL_MODE_AUTO):
            if self._room_coordinator:
                self._room_coordinator.control_mode = value
            else:
                self._control_mode = value
                self.logger.debug("Control mode set to: %s", value)
                # Notify select entity if it exists
                if hasattr(self, "_control_mode_select") and self._control_mode_select:
                    self._control_mode_select.set_control_mode(value)

    def register_control_mode_select(self, select_entity):
        """Register the control mode select entity for callbacks."""
        if self._room_coordinator:
            self._room_coordinator.register_control_mode_select(select_entity)
        else:
            self._control_mode_select = select_entity

    @property
    def is_control_enabled(self):
        """Check if control is enabled (mode is not OFF)."""
        if self._room_coordinator:
            return self._room_coordinator.is_control_enabled
        return self._control_mode != CONTROL_MODE_DISABLED

    @property
    def is_climate_mode(self):
        """Check if climate mode is active (mode is AUTO)."""
        if self._room_coordinator:
            return self._room_coordinator.is_climate_mode
        return self._control_mode == CONTROL_MODE_AUTO

    @property
    def lux_toggle(self):
        """Toggle automation."""
        if self._room_coordinator:
            return self._room_coordinator.lux_toggle
        return self._lux_toggle

    @lux_toggle.setter
    def lux_toggle(self, value):
        if self._room_coordinator:
            self._room_coordinator.lux_toggle = value
        else:
            self._lux_toggle = value

    @property
    def irradiance_toggle(self):
        """Toggle automation."""
        if self._room_coordinator:
            return self._room_coordinator.irradiance_toggle
        return self._irradiance_toggle

    @irradiance_toggle.setter
    def irradiance_toggle(self, value):
        if self._room_coordinator:
            self._room_coordinator.irradiance_toggle = value
        else:
            self._irradiance_toggle = value

    @property
    def cloud_toggle(self):
        """Toggle cloud coverage check."""
        if self._room_coordinator:
            return self._room_coordinator.cloud_toggle
        return self._cloud_toggle

    @cloud_toggle.setter
    def cloud_toggle(self, value):
        if self._room_coordinator:
            self._room_coordinator.cloud_toggle = value
        else:
            self._cloud_toggle = value

    @property
    def weather_toggle(self):
        """Toggle weather check."""
        if self._room_coordinator:
            return self._room_coordinator.weather_toggle
        return self._weather_toggle

    @weather_toggle.setter
    def weather_toggle(self, value):
        if self._room_coordinator:
            self._room_coordinator.weather_toggle = value
        else:
            self._weather_toggle = value


class AdaptiveCoverManager:
    """Track position changes and detect manual control."""

    def __init__(self, logger, coordinator) -> None:
        """Initialize the AdaptiveCoverManager."""
        self.covers: set[str] = set()
        self.logger = logger
        self.coordinator = coordinator

    def add_covers(self, entity):
        """Update set with entities."""
        self.covers.update(entity)

    def handle_state_change(
        self,
        states_data,
        our_state,
        blind_type,
        wait_target_call,
        manual_threshold,
    ):
        """Process state change event and set control mode to OFF if manual change detected."""
        event = states_data
        if event is None:
            return
        entity_id = event.entity_id
        if entity_id not in self.covers:
            return
        if wait_target_call.get(entity_id):
            return

        new_state = event.new_state

        if blind_type == "cover_tilt":
            new_position = new_state.attributes.get("current_tilt_position")
        else:
            new_position = new_state.attributes.get("current_position")

        if new_position != our_state:
            if (
                manual_threshold is not None
                and abs(our_state - new_position) < manual_threshold
            ):
                self.logger.debug(
                    "Position change is less than threshold %s for %s",
                    manual_threshold,
                    entity_id,
                )
                return
            self.logger.debug(
                "Manual change detected for %s. Our state: %s, new state: %s",
                entity_id,
                our_state,
                new_position,
            )
            self.logger.info(
                "Setting control mode to OFF due to manual change on %s",
                entity_id,
            )
            # Set control mode to OFF when manual change detected
            self.coordinator.control_mode = CONTROL_MODE_DISABLED


def inverse_state(state: int) -> int:
    """Inverse state."""
    return 100 - state
