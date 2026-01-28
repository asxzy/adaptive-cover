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
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Adaptive Cover config entry."""

    name = config_entry.data["name"]
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    sensor = AdaptiveCoverSensorEntity(
        config_entry.entry_id, hass, config_entry, name, coordinator
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
    control = AdaptiveCoverControlSensorEntity(
        config_entry.entry_id, hass, config_entry, name, coordinator
    )
    entities = [sensor, start, end, control]

    # Add cloud coverage sensor if cloud entity is configured
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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states["state"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )

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
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )


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
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )


class AdaptiveCoverCloudSensorEntity(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity
):
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
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize adaptive_cover Cloud Sensor."""
        super().__init__(coordinator=coordinator)
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._attr_name = "Cloud Coverage"
        self._attr_unique_id = f"{unique_id}_{self._attr_name}"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the cloud coverage percentage."""
        return self.data.states.get("cloud_coverage")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
        )
