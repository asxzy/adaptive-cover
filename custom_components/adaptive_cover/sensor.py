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
    _LOGGER,
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

    # Room entry - cloud coverage sensor and aggregated time sensors
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

        # Aggregated Start Sun and End Sun sensors for room
        start = AdaptiveRoomTimeSensorEntity(
            config_entry.entry_id,
            hass,
            config_entry,
            name,
            "Start Sun",
            "start_sun",
            "mdi:sun-clock-outline",
            coordinator,
        )
        end = AdaptiveRoomTimeSensorEntity(
            config_entry.entry_id,
            hass,
            config_entry,
            name,
            "End Sun",
            "end_sun",
            "mdi:sun-clock",
            coordinator,
        )
        entities.extend([start, end])

        # Comfort Status sensor for room (aggregates from child covers)
        comfort_status = AdaptiveRoomComfortStatusSensorEntity(
            config_entry.entry_id,
            hass,
            config_entry,
            name,
            coordinator,
        )
        entities.append(comfort_status)

    # Cover entry - position sensor always, time sensors only for standalone
    else:
        sensor = AdaptiveCoverSensorEntity(
            config_entry.entry_id,
            hass,
            config_entry,
            name,
            coordinator,
            room_id=room_id,
        )
        entities.append(sensor)

        # Time sensors only for standalone covers (room provides aggregated values)
        if not room_id:
            start = AdaptiveCoverTimeSensorEntity(
                config_entry.entry_id,
                hass,
                config_entry,
                name,
                "Start Sun",
                "start",
                "mdi:sun-clock-outline",
                coordinator,
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
            )
            entities.extend([start, end])

            # Comfort Status only for standalone covers (room handles this)
            control = AdaptiveCoverControlSensorEntity(
                config_entry.entry_id,
                hass,
                config_entry,
                name,
                coordinator,
            )
            entities.append(control)

            # Add cloud coverage sensor only for standalone covers
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
        self._attr_unique_id = f"{unique_id}_Cover Position"
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._device_id = unique_id
        self._room_id = room_id

        # When cover belongs to a room, include cover name in entity name
        if room_id:
            self._attr_has_entity_name = False
            self._attr_name = f"{name} Cover Position"
        else:
            self._attr_name = "Cover Position"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Cover position sensor is unavailable when control mode is OFF or data not ready.
        """
        if self.coordinator.control_mode == CONTROL_MODE_DISABLED:
            return False
        data = self.coordinator.data
        if data is None:
            return False
        return data.states.get("state") is not None

    @property
    def native_value(self) -> int | None:
        """Return the cover position."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.states.get("state")

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
        data = self.coordinator.data
        if data is None:
            return None
        return data.attributes


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
        self._attr_unique_id = f"{unique_id}_{sensor_name}"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._room_id = room_id

        # When cover belongs to a room, include cover name in entity name
        if room_id:
            self._attr_has_entity_name = False
            self._attr_name = f"{name} {sensor_name}"
        else:
            self._attr_name = sensor_name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the time value."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.states.get(self.key)

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


class AdaptiveRoomTimeSensorEntity(CoordinatorEntity[RoomCoordinator], SensorEntity):
    """Adaptive Cover Room Time Sensor for aggregated Start/End Sun times."""

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
        coordinator: RoomCoordinator,
    ) -> None:
        """Initialize adaptive_cover Room Time Sensor."""
        super().__init__(coordinator=coordinator)
        self._attr_icon = icon
        self.key = key
        self.coordinator = coordinator
        self._attr_unique_id = f"{unique_id}_{sensor_name}"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._attr_name = sensor_name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(
            "RoomTimeSensor[%s] _handle_coordinator_update called", self.key
        )
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the aggregated time value from room coordinator."""
        value = getattr(self.coordinator, self.key, None)
        _LOGGER.debug("RoomTimeSensor[%s] native_value: %s", self.key, value)
        return value

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"room_{self._device_id}")},
            name=f"Room: {self._name}",
        )


class AdaptiveCoverControlSensorEntity(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity
):
    """Adaptive Cover Comfort Status Sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "comfort_status"

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
        self._attr_unique_id = f"{unique_id}_Comfort Status"
        self._device_id = unique_id
        self.id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._room_id = room_id

        # When cover belongs to a room, include cover name in entity name
        if room_id:
            self._attr_has_entity_name = False
            self._attr_name = f"{name} Comfort Status"
        else:
            self._attr_name = "Comfort Status"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the comfort status."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.states.get("comfort_status")

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


class AdaptiveRoomComfortStatusSensorEntity(
    CoordinatorEntity[RoomCoordinator], SensorEntity
):
    """Adaptive Cover Room Comfort Status Sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "comfort_status"

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: RoomCoordinator,
    ) -> None:
        """Initialize the room comfort status sensor."""
        super().__init__(coordinator=coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{unique_id}_Comfort Status"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._attr_name = "Comfort Status"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("RoomComfortStatusSensor _handle_coordinator_update called")
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the comfort status aggregated from child covers."""
        value = self.coordinator.comfort_status
        _LOGGER.debug("RoomComfortStatusSensor native_value: %s", value)
        return value

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"room_{self._device_id}")},
            name=f"Room: {self._name}",
        )


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
                _LOGGER.debug("Cloud sensor: coordinator.data is None")
                return None
            value = self.coordinator.data.last_known.get("cloud")
            _LOGGER.debug("Cloud sensor (room): last_known.cloud = %s", value)
            return value
        value = self.coordinator.data.states.get("cloud_coverage")
        _LOGGER.debug("Cloud sensor (cover): cloud_coverage = %s", value)
        return value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            return False
        if isinstance(self.coordinator, RoomCoordinator):
            if self.coordinator.data is None:
                return False
            return self.coordinator.data.last_known.get("cloud") is not None
        return self.coordinator.data.states.get("cloud_coverage") is not None

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
