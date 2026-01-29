"""Sensor platform for Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CLOUD_ENTITY,
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    CONTROL_MODE_DISABLED,
    DOMAIN,
    EntryType,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .room_coordinator import RoomCoordinator

CoordinatorType = AdaptiveDataUpdateCoordinator | RoomCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Adaptive Cover config entry."""
    name = config_entry.data["name"]
    coordinator: CoordinatorType = hass.data[DOMAIN][config_entry.entry_id]
    entry_type = config_entry.data.get(CONF_ENTRY_TYPE)
    room_id = config_entry.data.get(CONF_ROOM_ID)

    entities = []

    # Room entry - only cloud coverage sensor
    if entry_type == EntryType.ROOM:
        cloud_entity = config_entry.options.get(CONF_CLOUD_ENTITY)
        if cloud_entity:
            cloud_sensor = AdaptiveCoverCloudSensorEntity(
                config_entry.entry_id,
                hass,
                config_entry,
                name,
                coordinator,
                is_room=True,
            )
            entities.append(cloud_sensor)

    # Cover entry - position, time, and control sensors
    else:
        sensor = AdaptiveCoverSensorEntity(
            config_entry.entry_id, hass, config_entry, name, coordinator, room_id=room_id
        )
        start = AdaptiveCoverTimeSensorEntity(
            config_entry.entry_id,
            hass,
            config_entry,
            name,
            "Start Sun",
            "start",
            "mdi:sun-clock-outline",
            coordinator,
            room_id=room_id,
        )
        end = AdaptiveCoverTimeSensorEntity(
            config_entry.entry_id,
            hass,
            config_entry,
            name,
            "End Sun",
            "end",
            "mdi:sun-clock",
            coordinator,
            room_id=room_id,
        )
        control = AdaptiveCoverControlSensorEntity(
            config_entry.entry_id, hass, config_entry, name, coordinator, room_id=room_id
        )
        entities.extend([sensor, start, end, control])

        # Add cloud coverage sensor only for standalone covers
        if not room_id:
            cloud_entity = config_entry.options.get(CONF_CLOUD_ENTITY)
            if cloud_entity:
                cloud_sensor = AdaptiveCoverCloudSensorEntity(
                    config_entry.entry_id, hass, config_entry, name, coordinator
                )
                entities.append(cloud_sensor)

    async_add_entities(entities)


class AdaptiveCoverSensorEntity(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity
):
    """Adaptive Cover Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:sun-compass"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: AdaptiveDataUpdateCoordinator,
        room_id: str | None = None,
    ) -> None:
        """Initialize adaptive_cover Sensor."""
        super().__init__(coordinator=coordinator)
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._attr_name = "Cover Position"
        self._attr_unique_id = f"{unique_id}_{self._attr_name}"
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._device_id = unique_id
        self._room_id = room_id

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Cover position sensor is unavailable when control mode is OFF.
        """
        return self.coordinator.control_mode != CONTROL_MODE_DISABLED

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states["state"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
        if self._room_id:
            info["via_device"] = (DOMAIN, f"room_{self._room_id}")
        return info

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        return self.data.attributes


class AdaptiveCoverTimeSensorEntity(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity
):
    """Adaptive Cover Time Sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        sensor_name: str,
        key: str,
        icon: str,
        coordinator: AdaptiveDataUpdateCoordinator,
        room_id: str | None = None,
    ) -> None:
        """Initialize adaptive_cover Sensor."""
        super().__init__(coordinator=coordinator)
        self._attr_icon = icon
        self.key = key
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._attr_unique_id = f"{unique_id}_{sensor_name}"
        self._attr_name = sensor_name
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._room_id = room_id

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states[self.key]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
        if self._room_id:
            info["via_device"] = (DOMAIN, f"room_{self._room_id}")
        return info


class AdaptiveCoverControlSensorEntity(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity
):
    """Adaptive Cover Control method Sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "control"

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: AdaptiveDataUpdateCoordinator,
        room_id: str | None = None,
    ) -> None:
        """Initialize adaptive_cover Sensor."""
        super().__init__(coordinator=coordinator)
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._attr_name = "Control Method"
        self._attr_unique_id = f"{unique_id}_{self._attr_name}"
        self._device_id = unique_id
        self.id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._room_id = room_id

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states["control"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
        if self._room_id:
            info["via_device"] = (DOMAIN, f"room_{self._room_id}")
        return info


class AdaptiveCoverCloudSensorEntity(CoordinatorEntity[CoordinatorType], SensorEntity):
    """Adaptive Cover Cloud Coverage Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:weather-cloudy"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: CoordinatorType,
        is_room: bool = False,
    ) -> None:
        """Initialize adaptive_cover Cloud Sensor."""
        super().__init__(coordinator=coordinator)
        self.coordinator = coordinator
        self._attr_name = "Cloud Coverage"
        self._attr_unique_id = f"{unique_id}_{self._attr_name}"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._is_room = is_room

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the cloud coverage percentage."""
        if isinstance(self.coordinator, RoomCoordinator):
            # For room coordinator, get from last_known if available
            if self.coordinator.data is None:
                return None
            return self.coordinator.data.last_known.get("cloud")
        return self.coordinator.data.states.get("cloud_coverage")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        if self._is_room:
            return DeviceInfo(
                entry_type=DeviceEntryType.SERVICE,
                identifiers={(DOMAIN, f"room_{self._device_id}")},
                name=f"Room: {self._name}",
            )
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
