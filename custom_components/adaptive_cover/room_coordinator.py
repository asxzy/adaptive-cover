"""Room Coordinator for Adaptive Cover integration."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_context_adapter import ConfigContextAdapter
from .helpers import get_safe_state
from .const import (
    _LOGGER,
    COMFORT_STATUS_COMFORTABLE,
    COMFORT_STATUS_TOO_COLD,
    COMFORT_STATUS_TOO_HOT,
    CONF_CLIMATE_MODE,
    CONF_CLOUD_ENTITY,
    CONF_CLOUD_THRESHOLD,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTRY_TYPE,
    CONF_IRRADIANCE_ENTITY,
    CONF_IRRADIANCE_THRESHOLD,
    CONF_LUX_ENTITY,
    CONF_LUX_THRESHOLD,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_THRESHOLD,
    CONF_PRESENCE_ENTITY,
    CONF_RESET_AT_MIDNIGHT,
    CONF_RETURN_SUNSET,
    CONF_ROOM_ID,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TRANSPARENT_BLIND,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_DISABLED,
    CONTROL_MODE_FORCE,
    DOMAIN,
    EntryType,
    LOGGER,
    SIGNAL_COVER_REGISTERED,
)

if TYPE_CHECKING:
    from .coordinator import AdaptiveDataUpdateCoordinator

# Storage constants for persisting last known sensor values
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "adaptive_cover_room"


@dataclass
class RoomData:
    """Shared room data passed to cover coordinators."""

    control_mode: str
    lux_toggle: bool | None
    irradiance_toggle: bool | None
    cloud_toggle: bool | None
    weather_toggle: bool | None
    is_presence: bool | None
    has_direct_sun: bool | None
    # Room-calculated values
    comfort_status: str | None = None
    cloud_coverage: float | None = None
    climate_data_args: list | None = None
    # Sensor availability for graceful degradation
    sensor_available: dict = field(default_factory=dict)
    # Last known values for graceful degradation
    last_known: dict = field(default_factory=dict)


class RoomCoordinator(DataUpdateCoordinator[RoomData]):
    """Coordinator for room-level shared state.

    Manages shared sensors, control mode, and toggles for all covers in a room.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the room coordinator."""
        super().__init__(hass, LOGGER, name=f"{DOMAIN}_room")

        self.config_entry = config_entry
        self.logger = ConfigContextAdapter(_LOGGER)
        self.logger.set_config_name(f"Room: {config_entry.data.get('name')}")

        # Child cover coordinators
        self._child_coordinators: list[AdaptiveDataUpdateCoordinator] = []

        # Control mode
        self._control_mode = CONTROL_MODE_AUTO
        self._reset_at_midnight = config_entry.options.get(CONF_RESET_AT_MIDNIGHT, True)
        self._midnight_unsub = None

        # Sensor toggles (shared across all covers in the room)
        self._lux_toggle: bool | None = None
        self._irradiance_toggle: bool | None = None
        self._cloud_toggle: bool | None = None
        self._weather_toggle: bool | None = None

        # Automation settings
        self._climate_mode = config_entry.options.get(CONF_CLIMATE_MODE, False)
        self._track_end_time = config_entry.options.get(CONF_RETURN_SUNSET)

        # Control mode select entity reference
        self._control_mode_select = None

        # Last known sensor values for graceful degradation
        self._last_known: dict[str, bool | float | None] = {
            "has_direct_sun": None,
            "is_presence": None,
            "lux": None,
            "irradiance": None,
            "cloud": None,
        }
        self._sensor_available: dict[str, bool] = {
            "has_direct_sun": True,
            "is_presence": True,
        }
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{config_entry.entry_id}",
        )

        # Cached options
        self._cached_options = None

    def register_cover(self, cover_coordinator: AdaptiveDataUpdateCoordinator) -> None:
        """Register a child cover coordinator."""
        if cover_coordinator not in self._child_coordinators:
            self._child_coordinators.append(cover_coordinator)
            self.logger.debug(
                "Registered cover coordinator, total: %d", len(self._child_coordinators)
            )
            # Notify listeners that data has changed (triggers room sensor updates)
            self.async_set_updated_data(self.data)
            # Fire signal for dynamic proxy sensor creation on room device
            async_dispatcher_send(
                self.hass,
                f"{SIGNAL_COVER_REGISTERED}_{self.config_entry.entry_id}",
                cover_coordinator,
            )

    def unregister_cover(
        self, cover_coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Unregister a child cover coordinator."""
        if cover_coordinator in self._child_coordinators:
            self._child_coordinators.remove(cover_coordinator)
            self.logger.debug(
                "Unregistered cover coordinator, remaining: %d",
                len(self._child_coordinators),
            )

    async def async_config_entry_first_refresh(self) -> None:
        """Config entry first refresh."""
        await self._async_load_last_known()
        await super().async_config_entry_first_refresh()
        self.logger.debug("Room config entry first refresh")

    async def async_discover_existing_covers(self) -> None:
        """Discover and register existing covers that belong to this room.

        This handles the case where the room is reloaded and needs to reconnect
        to its child covers that are already loaded.
        """
        room_id = self.config_entry.entry_id
        self.logger.debug("Discovering existing covers for room %s", room_id)

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            # Skip room entries
            if entry.data.get(CONF_ENTRY_TYPE) == EntryType.ROOM:
                continue

            # Check if this cover belongs to this room
            if entry.data.get(CONF_ROOM_ID) == room_id:
                cover_coordinator = self.hass.data[DOMAIN].get(entry.entry_id)
                if (
                    cover_coordinator
                    and cover_coordinator not in self._child_coordinators
                ):
                    self.logger.debug(
                        "Discovered existing cover %s, registering",
                        entry.data.get("name"),
                    )
                    # Update cover's room coordinator reference
                    cover_coordinator.set_room_coordinator(self)
                    self.register_cover(cover_coordinator)

        if self._child_coordinators:
            self.logger.debug(
                "Discovered %d existing covers", len(self._child_coordinators)
            )

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

    async def _async_update_data(self) -> RoomData:
        """Update room-level shared data."""
        self.logger.debug("Updating room data")
        options = self.config_entry.options

        # Fetch and update all sensor values
        await self._update_cloud_value(options)
        await self._update_presence_value(options)
        await self._update_weather_value(options)

        # Calculate comfort status based on inside temperature
        comfort_status = self._calculate_comfort_status(options)

        # Build climate data arguments for child coordinators
        climate_data_args = self._get_climate_data_args(options)

        return RoomData(
            control_mode=self._control_mode,
            lux_toggle=self._lux_toggle,
            irradiance_toggle=self._irradiance_toggle,
            cloud_toggle=self._cloud_toggle,
            weather_toggle=self._weather_toggle,
            is_presence=self._last_known.get("is_presence"),
            has_direct_sun=self._last_known.get("has_direct_sun"),
            comfort_status=comfort_status,
            cloud_coverage=self._last_known.get("cloud"),
            climate_data_args=climate_data_args,
            sensor_available=self._sensor_available.copy(),
            last_known=self._last_known.copy(),
        )

    async def _update_cloud_value(self, options) -> None:
        """Fetch cloud entity value and update last_known."""
        cloud_entity = options.get(CONF_CLOUD_ENTITY)
        if cloud_entity is None:
            self.logger.debug("No cloud entity configured")
            return

        value = get_safe_state(self.hass, cloud_entity)
        self.logger.debug(
            "Cloud entity %s state: %s (previous: %s)",
            cloud_entity,
            value,
            self._last_known.get("cloud"),
        )

        if value is not None:
            try:
                cloud_value = float(value)
                if self._last_known.get("cloud") != cloud_value:
                    self._last_known["cloud"] = cloud_value
                    await self._async_save_last_known()
                    self.logger.debug("Updated cloud last_known to: %s", cloud_value)
                self._sensor_available["cloud"] = True
            except (ValueError, TypeError) as err:
                self.logger.warning("Invalid cloud value '%s': %s", value, err)
                self._sensor_available["cloud"] = False
        else:
            self._sensor_available["cloud"] = False
            self.logger.debug(
                "Cloud entity unavailable, keeping last known: %s",
                self._last_known.get("cloud"),
            )

    async def _update_presence_value(self, options) -> None:
        """Fetch presence entity value and update last_known."""
        presence_entity = options.get(CONF_PRESENCE_ENTITY)
        if presence_entity is None:
            self.logger.debug("No presence entity configured")
            return

        value = get_safe_state(self.hass, presence_entity)
        self.logger.debug(
            "Presence entity %s state: %s (previous: %s)",
            presence_entity,
            value,
            self._last_known.get("is_presence"),
        )

        if value is not None:
            domain = presence_entity.split(".")[0]
            if domain == "binary_sensor":
                presence_value = value == "on"
            elif domain == "device_tracker":
                presence_value = value == "home"
            else:
                presence_value = value not in ("off", "not_home", "0", "false")

            if self._last_known.get("is_presence") != presence_value:
                self._last_known["is_presence"] = presence_value
                await self._async_save_last_known()
                self.logger.debug("Updated presence last_known to: %s", presence_value)
            self._sensor_available["is_presence"] = True
        else:
            self._sensor_available["is_presence"] = False
            self.logger.debug(
                "Presence entity unavailable, keeping last known: %s",
                self._last_known.get("is_presence"),
            )

    async def _update_weather_value(self, options) -> None:
        """Fetch weather entity value and update has_direct_sun in last_known."""
        weather_entity = options.get(CONF_WEATHER_ENTITY)
        if weather_entity is None:
            self.logger.debug("No weather entity configured")
            return

        weather_conditions = options.get(CONF_WEATHER_STATE, [])
        value = get_safe_state(self.hass, weather_entity)
        self.logger.debug(
            "Weather entity %s state: %s (conditions: %s, previous: %s)",
            weather_entity,
            value,
            weather_conditions,
            self._last_known.get("has_direct_sun"),
        )

        if value is not None:
            has_direct_sun = value in weather_conditions
            if self._last_known.get("has_direct_sun") != has_direct_sun:
                self._last_known["has_direct_sun"] = has_direct_sun
                await self._async_save_last_known()
                self.logger.debug(
                    "Updated has_direct_sun last_known to: %s", has_direct_sun
                )
            self._sensor_available["has_direct_sun"] = True
        else:
            self._sensor_available["has_direct_sun"] = False
            self.logger.debug(
                "Weather entity unavailable, keeping last known: %s",
                self._last_known.get("has_direct_sun"),
            )

    def _calculate_comfort_status(self, options) -> str:
        """Calculate comfort status based on inside temperature vs thresholds."""
        temp_entity = options.get(CONF_TEMP_ENTITY)
        temp_low = options.get(CONF_TEMP_LOW)
        temp_high = options.get(CONF_TEMP_HIGH)

        # Default to comfortable if no temperature sensor configured
        if not temp_entity:
            return COMFORT_STATUS_COMFORTABLE

        value = get_safe_state(self.hass, temp_entity)
        if value is None:
            self.logger.debug("Inside temp entity unavailable for comfort calculation")
            return COMFORT_STATUS_COMFORTABLE

        try:
            inside_temp = float(value)
        except (ValueError, TypeError):
            self.logger.warning(
                "Invalid inside temperature value '%s' for comfort calculation", value
            )
            return COMFORT_STATUS_COMFORTABLE

        self.logger.debug(
            "Comfort calculation: inside_temp=%s, temp_low=%s, temp_high=%s",
            inside_temp,
            temp_low,
            temp_high,
        )

        if temp_high is not None and inside_temp > temp_high:
            return COMFORT_STATUS_TOO_HOT
        if temp_low is not None and inside_temp < temp_low:
            return COMFORT_STATUS_TOO_COLD
        return COMFORT_STATUS_COMFORTABLE

    def _get_climate_data_args(self, options) -> list:
        """Get climate data arguments for ClimateCoverData construction."""
        return [
            self.hass,
            self.logger,
            options.get(CONF_TEMP_ENTITY),
            options.get(CONF_TEMP_LOW),
            options.get(CONF_TEMP_HIGH),
            options.get(CONF_PRESENCE_ENTITY),
            options.get(CONF_WEATHER_ENTITY),
            options.get(CONF_WEATHER_STATE),
            None,  # cover_type - will be overridden by cover coordinator
            options.get(CONF_TRANSPARENT_BLIND),
            options.get(CONF_LUX_ENTITY),
            options.get(CONF_IRRADIANCE_ENTITY),
            options.get(CONF_LUX_THRESHOLD),
            options.get(CONF_IRRADIANCE_THRESHOLD),
            self._lux_toggle,
            self._irradiance_toggle,
            options.get(CONF_CLOUD_ENTITY),
            options.get(CONF_CLOUD_THRESHOLD),
            self._cloud_toggle,
        ]

    async def async_notify_children(self) -> None:
        """Notify all child cover coordinators to refresh."""
        self.logger.debug(
            "Notifying %d child coordinators", len(self._child_coordinators)
        )
        for child in self._child_coordinators:
            child.state_change = True
            await child.async_refresh()

    async def async_force_update_covers(self) -> None:
        """Force update all covers in this room."""
        self.logger.info("Force updating all covers in room")
        for child in self._child_coordinators:
            await child.async_force_update_covers()

    @property
    def comfort_status(self) -> str | None:
        """Get comfort status calculated by room from inside temperature."""
        if self.data is not None:
            return self.data.comfort_status
        return COMFORT_STATUS_COMFORTABLE

    @property
    def cloud_coverage(self) -> float | None:
        """Get cloud coverage value."""
        if self.data is not None:
            return self.data.cloud_coverage
        return None

    async def async_check_entity_state_change(self, event) -> None:
        """Handle state change for tracked entities."""
        self.logger.debug("Room entity state change")
        await self.async_refresh()
        await self.async_notify_children()

    def setup_midnight_reset(self) -> None:
        """Set up midnight reset listener."""
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
        self.hass.async_create_task(self.async_notify_children())

    # Control mode property
    @property
    def control_mode(self) -> str:
        """Get control mode (off/on/auto)."""
        return self._control_mode

    @control_mode.setter
    def control_mode(self, value: str) -> None:
        """Set control mode and notify select entity."""
        if value in (CONTROL_MODE_DISABLED, CONTROL_MODE_FORCE, CONTROL_MODE_AUTO):
            self._control_mode = value
            self.logger.debug("Control mode set to: %s", value)
            # Notify select entity if it exists
            if self._control_mode_select:
                self._control_mode_select.set_control_mode(value)

    def register_control_mode_select(self, select_entity) -> None:
        """Register the control mode select entity for callbacks."""
        self._control_mode_select = select_entity

    @property
    def is_control_enabled(self) -> bool:
        """Check if control is enabled (mode is not OFF)."""
        return self._control_mode != CONTROL_MODE_DISABLED

    @property
    def is_climate_mode(self) -> bool:
        """Check if climate mode is active (mode is AUTO)."""
        return self._control_mode == CONTROL_MODE_AUTO

    # Sensor toggle properties
    @property
    def lux_toggle(self) -> bool | None:
        """Toggle lux sensor."""
        return self._lux_toggle

    @lux_toggle.setter
    def lux_toggle(self, value: bool | None) -> None:
        self._lux_toggle = value

    @property
    def irradiance_toggle(self) -> bool | None:
        """Toggle irradiance sensor."""
        return self._irradiance_toggle

    @irradiance_toggle.setter
    def irradiance_toggle(self, value: bool | None) -> None:
        self._irradiance_toggle = value

    @property
    def cloud_toggle(self) -> bool | None:
        """Toggle cloud coverage check."""
        return self._cloud_toggle

    @cloud_toggle.setter
    def cloud_toggle(self, value: bool | None) -> None:
        self._cloud_toggle = value

    @property
    def weather_toggle(self) -> bool | None:
        """Toggle weather check."""
        return self._weather_toggle

    @weather_toggle.setter
    def weather_toggle(self, value: bool | None) -> None:
        self._weather_toggle = value

    # Automation settings accessors
    def get_option(self, key: str, default=None):
        """Get a shared option value."""
        return self.config_entry.options.get(key, default)

    @property
    def delta_position(self) -> int:
        """Get minimum position change threshold."""
        return self.config_entry.options.get(CONF_DELTA_POSITION, 1)

    @property
    def delta_time(self) -> int:
        """Get minimum time between updates."""
        return self.config_entry.options.get(CONF_DELTA_TIME, 2)

    @property
    def start_time(self) -> str | None:
        """Get automation start time."""
        return self.config_entry.options.get(CONF_START_TIME)

    @property
    def start_time_entity(self) -> str | None:
        """Get automation start time entity."""
        return self.config_entry.options.get(CONF_START_ENTITY)

    @property
    def end_time(self) -> str | None:
        """Get automation end time."""
        return self.config_entry.options.get(CONF_END_TIME)

    @property
    def end_time_entity(self) -> str | None:
        """Get automation end time entity."""
        return self.config_entry.options.get(CONF_END_ENTITY)

    @property
    def manual_threshold(self) -> int | None:
        """Get manual override threshold."""
        return self.config_entry.options.get(CONF_MANUAL_THRESHOLD)

    @property
    def ignore_intermediate_states(self) -> bool:
        """Get whether to ignore intermediate states."""
        return self.config_entry.options.get(CONF_MANUAL_IGNORE_INTERMEDIATE, False)

    @property
    def climate_mode_enabled(self) -> bool:
        """Check if climate mode is enabled in config."""
        return self._climate_mode

    @property
    def track_end_time(self) -> bool:
        """Check if end time tracking is enabled."""
        return self._track_end_time or False

    # Graceful degradation
    def update_last_known(self, key: str, value: bool | None) -> None:
        """Update a last known sensor value."""
        if self._last_known.get(key) != value:
            self._last_known[key] = value
            self.hass.async_create_task(self._async_save_last_known())

    def update_sensor_available(self, key: str, available: bool) -> None:
        """Update sensor availability status."""
        self._sensor_available[key] = available
