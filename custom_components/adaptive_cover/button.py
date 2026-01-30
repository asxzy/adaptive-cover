"""Button platform for the Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENTITIES, CONF_ENTRY_TYPE, CONF_ROOM_ID, DOMAIN, EntryType
from .coordinator import AdaptiveDataUpdateCoordinator
from .room_coordinator import RoomCoordinator

CoordinatorType = AdaptiveDataUpdateCoordinator | RoomCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: CoordinatorType = hass.data[DOMAIN][config_entry.entry_id]
    entry_type = config_entry.data.get(CONF_ENTRY_TYPE)
    room_id = config_entry.data.get(CONF_ROOM_ID)

    entities = []

    # Room entry - add force update button for all covers in room
    if entry_type == EntryType.ROOM:
        force_update_button = ForceUpdateButton(
            config_entry,
            config_entry.entry_id,
            coordinator,
            is_room=True,
        )
        entities.append(force_update_button)
    # Standalone cover - add force update button if cover entities configured
    elif not room_id and len(config_entry.options.get(CONF_ENTITIES, [])) >= 1:
        force_update_button = ForceUpdateButton(
            config_entry,
            config_entry.entry_id,
            coordinator,
        )
        entities.append(force_update_button)
    # Cover in room - no button (room handles this)

    async_add_entities(entities)


class ForceUpdateButton(CoordinatorEntity[CoordinatorType], ButtonEntity):
    """Button to force update cover position immediately."""

    _attr_has_entity_name = True
    _attr_translation_key = "force_update"

    def __init__(
        self,
        config_entry: ConfigEntry,
        unique_id: str,
        coordinator: CoordinatorType,
        is_room: bool = False,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator=coordinator)
        self._name = config_entry.data["name"]
        self._attr_unique_id = f"{unique_id}_force_update"
        self._attr_icon = "mdi:refresh"
        self._device_id = unique_id
        self._is_room = is_room
        self._attr_name = "Force Update"

        # Set device info based on entry type
        if is_room:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"room_{self._device_id}")},
                name=f"Room: {self._name}",
            )
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=self._name,
            )

        self.coordinator.logger.debug("Setup force update button")

    async def async_press(self) -> None:
        """Handle the button press."""
        self.coordinator.logger.info("Force update button pressed")
        await self.coordinator.async_force_update_covers()
