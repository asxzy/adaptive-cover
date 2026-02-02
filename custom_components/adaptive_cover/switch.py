"""Switch platform for the Adaptive Cover integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CLIMATE_MODE,
    CONF_CLOUD_ENTITY,
    CONF_ENTRY_TYPE,
    CONF_IRRADIANCE_ENTITY,
    CONF_LUX_ENTITY,
    CONF_ROOM_ID,
    CONF_WEATHER_ENTITY,
    CONTROL_MODE_AUTO,
    DOMAIN,
    EntryType,
    _LOGGER,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .room_coordinator import RoomCoordinator

CoordinatorType = AdaptiveDataUpdateCoordinator | RoomCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator: CoordinatorType = hass.data[DOMAIN][config_entry.entry_id]
    entry_type = config_entry.data.get(CONF_ENTRY_TYPE)
    room_id = config_entry.data.get(CONF_ROOM_ID)

    # Determine if this is a room entry
    is_room = entry_type == EntryType.ROOM

    # Skip switches for covers inside a room (room handles switches)
    if room_id and not is_room:
        async_add_entities([])
        return

    # Sensor toggle switches (only functional in AUTO mode)
    lux_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Lux",
        True,
        "lux_toggle",
        coordinator,
        is_room=is_room,
        room_id=room_id,
    )
    irradiance_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Irradiance",
        True,
        "irradiance_toggle",
        coordinator,
        is_room=is_room,
        room_id=room_id,
    )
    cloud_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Cloud Coverage",
        True,
        "cloud_toggle",
        coordinator,
        is_room=is_room,
        room_id=room_id,
    )
    weather_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Weather",
        True,
        "weather_toggle",
        coordinator,
        is_room=is_room,
        room_id=room_id,
    )

    # Room entries always have climate mode enabled
    climate_mode = (
        True if is_room else config_entry.options.get(CONF_CLIMATE_MODE, False)
    )
    weather_entity = config_entry.options.get(CONF_WEATHER_ENTITY)
    lux_entity = config_entry.options.get(CONF_LUX_ENTITY)
    irradiance_entity = config_entry.options.get(CONF_IRRADIANCE_ENTITY)
    cloud_entity = config_entry.options.get(CONF_CLOUD_ENTITY)
    switches = []

    _LOGGER.debug(
        "Switch setup for %s: climate_mode=%s, weather_entity=%s, "
        "lux_entity=%s, irradiance_entity=%s, cloud_entity=%s, "
        "control_mode=%s",
        config_entry.data.get("name"),
        climate_mode,
        weather_entity,
        lux_entity,
        irradiance_entity,
        cloud_entity,
        coordinator.control_mode,
    )

    # Sensor toggles are shown if climate mode is enabled in config
    # They only affect behavior when control mode is AUTO
    if climate_mode:
        if lux_entity:
            switches.append(lux_switch)
        if irradiance_entity:
            switches.append(irradiance_switch)
        if cloud_entity:
            switches.append(cloud_switch)
        if weather_entity:
            switches.append(weather_switch)

    _LOGGER.debug(
        "Created %d switches for %s: %s",
        len(switches),
        config_entry.data.get("name"),
        [s._key for s in switches],
    )

    async_add_entities(switches)


class AdaptiveCoverSwitch(
    CoordinatorEntity[CoordinatorType], SwitchEntity, RestoreEntity
):
    """Representation of a adaptive cover switch."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        switch_name: str,
        initial_state: bool,
        key: str,
        coordinator: CoordinatorType,
        device_class: SwitchDeviceClass | None = None,
        is_room: bool = False,
        room_id: str | None = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator=coordinator)
        self._name = config_entry.data["name"]
        self._state: bool | None = None
        self._key = key
        self._attr_translation_key = key
        self._attr_device_class = device_class
        self._initial_state = initial_state
        self._attr_unique_id = f"{unique_id}_{switch_name}"
        self._device_id = unique_id
        self._is_room = is_room
        self._room_id = room_id

        # When cover belongs to a room, include cover name in entity name
        if room_id and not is_room:
            self._attr_has_entity_name = False
            self._attr_name = f"{self._name} {switch_name}"
        else:
            self._attr_name = switch_name

        # Set device info based on entry type
        if is_room:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"room_{self._device_id}")},
                name=f"Room: {self._name}",
            )
        else:
            info = DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=self._name,
            )
            if room_id:
                info["via_device"] = (DOMAIN, f"room_{room_id}")
            self._attr_device_info = info

        self.coordinator.logger.debug("Setup switch")

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Sensor toggles are only available in AUTO mode.
        """
        current_mode = self.coordinator.control_mode
        is_available = current_mode == CONTROL_MODE_AUTO
        if not is_available:
            self.coordinator.logger.debug(
                "%s switch unavailable: control_mode=%r, expected=%r",
                self._key,
                current_mode,
                CONTROL_MODE_AUTO,
            )
        return is_available

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update availability when control mode changes
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.logger.debug("Turning on %s", self._key)
        self._attr_is_on = True
        setattr(self.coordinator, self._key, True)

        # Skip refresh when restoring state during initialization
        # to avoid moving covers before first proper refresh
        if kwargs.get("added"):
            self.schedule_update_ha_state()
            return

        # For room coordinator, notify children
        if isinstance(self.coordinator, RoomCoordinator):
            await self.coordinator.async_refresh()
            await self.coordinator.async_notify_children()
        else:
            self.coordinator.state_change = True
            await self.coordinator.async_refresh()

        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.coordinator.logger.debug("Turning off %s", self._key)
        self._attr_is_on = False
        setattr(self.coordinator, self._key, False)

        # Skip refresh when restoring state during initialization
        # to avoid moving covers before first proper refresh
        if kwargs.get("added"):
            self.schedule_update_ha_state()
            return

        # For room coordinator, notify children
        if isinstance(self.coordinator, RoomCoordinator):
            await self.coordinator.async_refresh()
            await self.coordinator.async_notify_children()
        else:
            self.coordinator.state_change = True
            await self.coordinator.async_refresh()

        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        self.coordinator.logger.debug("%s: last state is %s", self._name, last_state)
        if (last_state is None and self._initial_state) or (
            last_state is not None and last_state.state == STATE_ON
        ):
            await self.async_turn_on(added=True)
        else:
            await self.async_turn_off(added=True)
