"""Sensor platform for Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    _LOGGER,
    CONF_CLOUD_ENTITY,
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    CONF_TEMP_ENTITY,
    CONTROL_MODE_DISABLED,
    DOMAIN,
    EntryType,
    SIGNAL_COVER_REGISTERED,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .room_coordinator import RoomCoordinator

CoordinatorType = AdaptiveDataUpdateCoordinator | RoomCoordinator


def _cleanup_orphaned_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    entry_type: str | None,
) -> None:
    """Remove sensors that should no longer exist based on config."""
    if entry_type != EntryType.ROOM:
        return

    ent_reg = er.async_get(hass)
    entry_id = config_entry.entry_id

    # Remove cloud sensor if not configured
    if not config_entry.options.get(CONF_CLOUD_ENTITY):
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, f"{entry_id}_Cloud Coverage"
        )
        if entity_id:
            ent_reg.async_remove(entity_id)

    # Remove comfort status sensor if temp entity not configured
    if not config_entry.options.get(CONF_TEMP_ENTITY):
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, f"{entry_id}_Comfort Status"
        )
        if entity_id:
            ent_reg.async_remove(entity_id)


class ProxySensorEntity(SensorEntity):
    """Base class for proxy sensors that display data from a different coordinator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        source_coordinator: CoordinatorType,
        device_info: DeviceInfo,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize proxy sensor."""
        self._source_coordinator = source_coordinator
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._unsub: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to source coordinator updates."""
        self._unsub = self._source_coordinator.async_add_listener(
            self._handle_source_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from source coordinator."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_source_update(self) -> None:
        """Handle update from source coordinator."""
        self.async_write_ha_state()


# Cover-to-Room Proxy Sensors


class CoverRoomCloudProxySensor(ProxySensorEntity):
    """Proxy sensor showing room's cloud coverage on cover device."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:weather-cloudy"

    def __init__(
        self,
        room_coordinator: RoomCoordinator,
        cover_entry_id: str,
        cover_name: str,
        room_id: str,
    ) -> None:
        """Initialize the proxy sensor."""
        device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, cover_entry_id)},
            name=cover_name,
            via_device=(DOMAIN, f"room_{room_id}"),
        )
        super().__init__(
            source_coordinator=room_coordinator,
            device_info=device_info,
            unique_id=f"{cover_entry_id}_room_proxy_cloud",
            name="Cloud Coverage (Room)",
        )

    @property
    def native_value(self) -> float | None:
        """Return the cloud coverage from room."""
        if self._source_coordinator.data is None:
            return None
        return self._source_coordinator.data.cloud_coverage

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._source_coordinator.data is None:
            return False
        return self._source_coordinator.data.cloud_coverage is not None


class CoverRoomComfortProxySensor(ProxySensorEntity):
    """Proxy sensor showing room's comfort status on cover device."""

    _attr_translation_key = "comfort_status"

    def __init__(
        self,
        room_coordinator: RoomCoordinator,
        cover_entry_id: str,
        cover_name: str,
        room_id: str,
    ) -> None:
        """Initialize the proxy sensor."""
        device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, cover_entry_id)},
            name=cover_name,
            via_device=(DOMAIN, f"room_{room_id}"),
        )
        super().__init__(
            source_coordinator=room_coordinator,
            device_info=device_info,
            unique_id=f"{cover_entry_id}_room_proxy_comfort",
            name="Comfort Status (Room)",
        )

    @property
    def native_value(self) -> str | None:
        """Return the comfort status from room."""
        return self._source_coordinator.comfort_status

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._source_coordinator.data is not None


# Room-to-Cover Proxy Sensors


class RoomCoverPositionProxySensor(ProxySensorEntity):
    """Proxy sensor showing a cover's position on room device."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:sun-compass"

    def __init__(
        self,
        cover_coordinator: AdaptiveDataUpdateCoordinator,
        room_coordinator: RoomCoordinator,
    ) -> None:
        """Initialize the proxy sensor."""
        cover_name = cover_coordinator.config_entry.data["name"]
        room_id = room_coordinator.config_entry.entry_id
        room_name = room_coordinator.config_entry.data["name"]

        device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"room_{room_id}")},
            name=f"Room: {room_name}",
        )
        super().__init__(
            source_coordinator=cover_coordinator,
            device_info=device_info,
            unique_id=f"room_{room_id}_proxy_{cover_coordinator.config_entry.entry_id}_position",
            name=f"{cover_name} Position",
        )
        self._cover_coordinator = cover_coordinator
        self._room_coordinator = room_coordinator

    @property
    def native_value(self) -> int | None:
        """Return the cover position."""
        if self._cover_coordinator.data is None:
            return None
        return self._cover_coordinator.data.states.get("state")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._cover_coordinator not in self._room_coordinator._child_coordinators:
            return False
        if self._cover_coordinator.data is None:
            return False
        return self._cover_coordinator.data.states.get("state") is not None


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

    # Clean up orphaned sensors from previous configurations
    _cleanup_orphaned_sensors(hass, config_entry, entry_type)

    entities = []

    # Room entry - room-level sensors
    if entry_type == EntryType.ROOM:
        # Cloud coverage sensor (if configured)
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

        # Comfort Status sensor for room (if temp entity configured)
        temp_entity = config_entry.options.get(CONF_TEMP_ENTITY)
        if temp_entity:
            comfort_status = AdaptiveRoomComfortStatusSensorEntity(
                config_entry.entry_id,
                hass,
                config_entry,
                name,
                coordinator,
            )
            entities.append(comfort_status)

        # Store callback for dynamic proxy sensor creation
        hass.data[DOMAIN][f"room_{config_entry.entry_id}_add_sensors"] = (
            async_add_entities
        )

        # Create proxy sensors for already-registered covers
        for cover_coord in coordinator._child_coordinators:
            entities.append(RoomCoverPositionProxySensor(cover_coord, coordinator))

        # Listen for future cover registrations
        @callback
        def _handle_cover_registered(
            cover_coordinator: AdaptiveDataUpdateCoordinator,
        ) -> None:
            """Handle new cover registration by creating proxy sensors."""
            add_entities = hass.data[DOMAIN].get(
                f"room_{config_entry.entry_id}_add_sensors"
            )
            if add_entities:
                add_entities(
                    [RoomCoverPositionProxySensor(cover_coordinator, coordinator)]
                )

        config_entry.async_on_unload(
            async_dispatcher_connect(
                hass,
                f"{SIGNAL_COVER_REGISTERED}_{config_entry.entry_id}",
                _handle_cover_registered,
            )
        )

    # Cover entry - position sensor and time sensors
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

        # Time sensors for ALL covers
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
        entities.extend([start, end])

        # Covers in a room get proxy sensors for room data
        if room_id:
            room_coordinator = hass.data[DOMAIN].get(f"room_{room_id}")
            if room_coordinator:
                room_options = room_coordinator.config_entry.options

                # Cloud coverage proxy (only if room has cloud entity configured)
                if room_options.get(CONF_CLOUD_ENTITY):
                    cloud_proxy = CoverRoomCloudProxySensor(
                        room_coordinator,
                        config_entry.entry_id,
                        name,
                        room_id,
                    )
                    entities.append(cloud_proxy)

                # Comfort status proxy (only if room has temp entity configured)
                if room_options.get(CONF_TEMP_ENTITY):
                    comfort_proxy = CoverRoomComfortProxySensor(
                        room_coordinator,
                        config_entry.entry_id,
                        name,
                        room_id,
                    )
                    entities.append(comfort_proxy)
        else:
            # Standalone covers get their own comfort status and cloud sensors

            # Comfort status sensor (only if temp entity configured)
            temp_entity = config_entry.options.get(CONF_TEMP_ENTITY)
            if temp_entity:
                control = AdaptiveCoverControlSensorEntity(
                    config_entry.entry_id,
                    hass,
                    config_entry,
                    name,
                    coordinator,
                )
                entities.append(control)

            # Add cloud coverage sensor only for standalone covers (if configured)
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
        """Return if entity is available."""
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
        """Return the comfort status calculated from inside temp vs thresholds."""
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
