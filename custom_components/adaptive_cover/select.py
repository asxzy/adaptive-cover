"""Select platform for the Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENTITIES,
    CONTROL_MODE_AUTO,
    CONTROL_MODE_OFF,
    CONTROL_MODE_ON,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities = []

    # Only add control mode select if there are cover entities configured
    if len(config_entry.options.get(CONF_ENTITIES, [])) >= 1:
        control_mode_select = ControlModeSelect(
            config_entry,
            config_entry.entry_id,
            coordinator,
        )
        entities.append(control_mode_select)

    async_add_entities(entities)


class ControlModeSelect(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SelectEntity, RestoreEntity
):
    """Select entity for control mode (OFF/ON/AUTO)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "control_mode"
    _attr_options = [CONTROL_MODE_OFF, CONTROL_MODE_ON, CONTROL_MODE_AUTO]

    def __init__(
        self,
        config_entry: ConfigEntry,
        unique_id: str,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator=coordinator)
        self._name = config_entry.data["name"]
        self._attr_name = "Control Mode"
        self._attr_unique_id = f"{unique_id}_control_mode"
        self._device_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
        self._attr_current_option = CONTROL_MODE_AUTO

        self.coordinator.logger.debug("Setup control mode select")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.coordinator.logger.debug("Selecting control mode: %s", option)
        self._attr_current_option = option
        self.coordinator.control_mode = option
        await self.coordinator.async_refresh()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        self.coordinator.logger.debug(
            "%s: last control mode state is %s", self._name, last_state
        )

        if last_state is not None and last_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            if last_state.state in self._attr_options:
                self._attr_current_option = last_state.state
            else:
                self._attr_current_option = CONTROL_MODE_AUTO
        else:
            self._attr_current_option = CONTROL_MODE_AUTO

        # Register with coordinator for callbacks
        self.coordinator.register_control_mode_select(self)

        # Sync with coordinator
        self.coordinator.control_mode = self._attr_current_option

        # Set up midnight reset
        self.coordinator.setup_midnight_reset()

    def set_control_mode(self, mode: str) -> None:
        """Set control mode programmatically (called by coordinator)."""
        if mode in self._attr_options:
            self._attr_current_option = mode
            self.async_write_ha_state()
