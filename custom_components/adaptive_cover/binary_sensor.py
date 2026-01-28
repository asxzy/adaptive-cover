"""Binary Sensor platform for the Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Adaptive Cover binary sensor platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    binary_sensor = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Sun Infront",
        False,
        "sun_motion",
        BinarySensorDeviceClass.MOTION,
        coordinator,
    )
    is_presence = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Room Occupied",
        False,
        "is_presence",
        BinarySensorDeviceClass.OCCUPANCY,
        coordinator,
    )
    has_direct_sun = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Weather Has Direct Sun",
        False,
        "has_direct_sun",
        BinarySensorDeviceClass.LIGHT,
        coordinator,
    )
    async_add_entities([binary_sensor, is_presence, has_direct_sun])


class AdaptiveCoverBinarySensor(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], BinarySensorEntity
):
    """representation of a Adaptive Cover binary sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        binary_name: str,
        state: bool,
        key: str,
        device_class: BinarySensorDeviceClass,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator=coordinator)
        self._key = key
        self._attr_translation_key = key
        self._name = config_entry.data["name"]
        self._attr_name = binary_name
        self._attr_unique_id = f"{unique_id}_{binary_name}"
        self._device_id = unique_id
        self._state = state
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.states[self._key]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if coordinator is available first
        if not super().available:
            return False
        # For sensors that depend on external entities, check availability status
        if self._key == "has_direct_sun":
            return self.coordinator.data.states.get("has_direct_sun_available", True)
        if self._key == "is_presence":
            return self.coordinator.data.states.get("is_presence_available", True)
        return True

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        if self._key == "has_direct_sun":
            return {
                "sensor_available": self.coordinator.data.states.get(
                    "has_direct_sun_available"
                ),
                "using_last_known": not self.coordinator.data.states.get(
                    "has_direct_sun_available", True
                ),
                "current_value": self.coordinator.data.states.get("has_direct_sun"),
            }
        if self._key == "is_presence":
            return {
                "sensor_available": self.coordinator.data.states.get(
                    "is_presence_available"
                ),
                "using_last_known": not self.coordinator.data.states.get(
                    "is_presence_available", True
                ),
                "current_value": self.coordinator.data.states.get("is_presence"),
            }
        return None
