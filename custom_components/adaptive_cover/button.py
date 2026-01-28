"""Button platform for the Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENTITIES, DOMAIN
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities = []

    # Only add force update button if there are cover entities configured
    if len(config_entry.options.get(CONF_ENTITIES, [])) >= 1:
        force_update_button = ForceUpdateButton(
            config_entry,
            config_entry.entry_id,
            coordinator,
        )
        entities.append(force_update_button)

    async_add_entities(entities)


class ForceUpdateButton(CoordinatorEntity[AdaptiveDataUpdateCoordinator], ButtonEntity):
    """Button to force update cover position immediately."""

    _attr_has_entity_name = True
    _attr_translation_key = "force_update"

    def __init__(
        self,
        config_entry: ConfigEntry,
        unique_id: str,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator=coordinator)
        self._name = config_entry.data["name"]
        self._attr_name = "Force Update"
        self._attr_unique_id = f"{unique_id}_force_update"
        self._attr_icon = "mdi:refresh"
        self._device_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )

        self.coordinator.logger.debug("Setup force update button")

    async def async_press(self) -> None:
        """Handle the button press."""
        self.coordinator.logger.info("Force update button pressed")
        await self.coordinator.async_force_update_covers()
