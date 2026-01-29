"""Button platform for the Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENTITIES, CONF_ROOM_ID, DOMAIN
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
    room_id = config_entry.data.get(CONF_ROOM_ID)

    entities = []

    # Only add force update button if there are cover entities configured
    if len(config_entry.options.get(CONF_ENTITIES, [])) >= 1:
        force_update_button = ForceUpdateButton(
            config_entry,
            config_entry.entry_id,
            coordinator,
            room_id=room_id,
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
        room_id: str | None = None,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator=coordinator)
        self._name = config_entry.data["name"]
        self._attr_unique_id = f"{unique_id}_force_update"
        self._attr_icon = "mdi:refresh"
        self._device_id = unique_id
        self._room_id = room_id

        # When cover belongs to a room, include cover name in entity name
        if room_id:
            self._attr_has_entity_name = False
            self._attr_name = f"{self._name} Force Update"
        else:
            self._attr_name = "Force Update"

        info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
        if room_id:
            info["via_device"] = (DOMAIN, f"room_{room_id}")
        self._attr_device_info = info

        self.coordinator.logger.debug("Setup force update button")

    async def async_press(self) -> None:
        """Handle the button press."""
        self.coordinator.logger.info("Force update button pressed")
        await self.coordinator.async_force_update_covers()
