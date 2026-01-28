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
    CONF_IRRADIANCE_ENTITY,
    CONF_LUX_ENTITY,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    # Sensor toggle switches (only functional in AUTO mode)
    temp_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Outside Temperature",
        False,
        "temp_toggle",
        coordinator,
    )
    lux_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Lux",
        True,
        "lux_toggle",
        coordinator,
    )
    irradiance_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Irradiance",
        True,
        "irradiance_toggle",
        coordinator,
    )
    cloud_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Cloud Coverage",
        True,
        "cloud_toggle",
        coordinator,
    )
    weather_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Weather",
        True,
        "weather_toggle",
        coordinator,
    )

    climate_mode = config_entry.options.get(CONF_CLIMATE_MODE)
    weather_entity = config_entry.options.get(CONF_WEATHER_ENTITY)
    sensor_entity = config_entry.options.get(CONF_OUTSIDETEMP_ENTITY)
    lux_entity = config_entry.options.get(CONF_LUX_ENTITY)
    irradiance_entity = config_entry.options.get(CONF_IRRADIANCE_ENTITY)
    cloud_entity = config_entry.options.get(CONF_CLOUD_ENTITY)
    switches = []

    # Sensor toggles are shown if climate mode is enabled in config
    # They only affect behavior when control mode is AUTO
    if climate_mode:
        if weather_entity or sensor_entity:
            switches.append(temp_switch)
        if lux_entity:
            switches.append(lux_switch)
        if irradiance_entity:
            switches.append(irradiance_switch)
        if cloud_entity:
            switches.append(cloud_switch)
        if weather_entity:
            switches.append(weather_switch)

    async_add_entities(switches)


class AdaptiveCoverSwitch(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SwitchEntity, RestoreEntity
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
        coordinator: AdaptiveDataUpdateCoordinator,
        device_class: SwitchDeviceClass | None = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator=coordinator)
        self._name = config_entry.data["name"]
        self._state: bool | None = None
        self._key = key
        self._attr_translation_key = key
        self._attr_name = switch_name
        self._attr_device_class = device_class
        self._initial_state = initial_state
        self._attr_unique_id = f"{unique_id}_{switch_name}"
        self._device_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )

        self.coordinator.logger.debug("Setup switch")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.logger.debug("Turning on %s", self._key)
        self._attr_is_on = True
        setattr(self.coordinator, self._key, True)
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.coordinator.logger.debug("Turning off %s", self._key)
        self._attr_is_on = False
        setattr(self.coordinator, self._key, False)
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        self.coordinator.logger.debug("%s: last state is %s", self._name, last_state)
        if (last_state is None and self._initial_state) or (
            last_state is not None and last_state.state == STATE_ON
        ):
            await self.async_turn_on(added=True)
        else:
            await self.async_turn_off(added=True)
