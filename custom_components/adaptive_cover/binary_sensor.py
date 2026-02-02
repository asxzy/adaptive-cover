"""Binary Sensor platform for the Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENTRY_TYPE,
    CONF_ROOM_ID,
    DOMAIN,
    SIGNAL_COVER_REGISTERED,
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
    """Set up the Adaptive Cover binary sensor platform."""
    coordinator: CoordinatorType = hass.data[DOMAIN][config_entry.entry_id]
    entry_type = config_entry.data.get(CONF_ENTRY_TYPE)
    room_id = config_entry.data.get(CONF_ROOM_ID)

    entities: list[BinarySensorEntity] = []

    # Room entry - presence sensor + per-cover proxy sensors
    if entry_type == EntryType.ROOM:
        is_presence = AdaptiveCoverBinarySensor(
            config_entry,
            config_entry.entry_id,
            "Room Occupied",
            False,
            "is_presence",
            BinarySensorDeviceClass.OCCUPANCY,
            coordinator,
            is_room=True,
        )
        has_direct_sun = AdaptiveCoverBinarySensor(
            config_entry,
            config_entry.entry_id,
            "Weather Has Direct Sun",
            False,
            "has_direct_sun",
            BinarySensorDeviceClass.LIGHT,
            coordinator,
            is_room=True,
        )
        entities.extend([is_presence, has_direct_sun])

        # Create proxy sensors for already-registered covers
        for cover_coord in coordinator._child_coordinators:
            entities.append(
                RoomCoverSunInfrontProxySensor(
                    source_coordinator=cover_coord,
                    room_coordinator=coordinator,
                    cover_name=cover_coord.config_entry.data.get("name", "Cover"),
                    cover_id=cover_coord.config_entry.entry_id,
                    room_id=config_entry.entry_id,
                )
            )

        # Listen for future cover registrations
        @callback
        def _create_room_cover_proxies(
            cover_coordinator: AdaptiveDataUpdateCoordinator,
        ) -> None:
            """Create proxy sensors when a new cover registers."""
            cover_name = cover_coordinator.config_entry.data.get("name", "Cover")
            cover_id = cover_coordinator.config_entry.entry_id
            async_add_entities(
                [
                    RoomCoverSunInfrontProxySensor(
                        source_coordinator=cover_coordinator,
                        room_coordinator=coordinator,
                        cover_name=cover_name,
                        cover_id=cover_id,
                        room_id=config_entry.entry_id,
                    ),
                ]
            )

        config_entry.async_on_unload(
            async_dispatcher_connect(
                hass,
                f"{SIGNAL_COVER_REGISTERED}_{config_entry.entry_id}",
                _create_room_cover_proxies,
            )
        )

    # Cover entry (standalone or part of room) - sun motion sensor
    else:
        binary_sensor = AdaptiveCoverBinarySensor(
            config_entry,
            config_entry.entry_id,
            "Sun Infront",
            False,
            "sun_motion",
            BinarySensorDeviceClass.MOTION,
            coordinator,
            room_id=room_id,
        )
        entities.append(binary_sensor)

        # Covers in a room get proxy sensors for room data
        if room_id and coordinator.room_coordinator:
            room_coordinator = coordinator.room_coordinator
            cover_name = config_entry.data.get("name", "Cover")

            # Occupied proxy
            entities.append(
                CoverRoomOccupiedProxySensor(
                    source_coordinator=room_coordinator,
                    cover_coordinator=coordinator,
                    cover_name=cover_name,
                    cover_id=config_entry.entry_id,
                    room_id=room_id,
                )
            )
            # Direct Sun proxy
            entities.append(
                CoverRoomDirectSunProxySensor(
                    source_coordinator=room_coordinator,
                    cover_coordinator=coordinator,
                    cover_name=cover_name,
                    cover_id=config_entry.entry_id,
                    room_id=room_id,
                )
            )

        # Standalone cover also gets presence and weather sensors
        elif not room_id:
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
            entities.extend([is_presence, has_direct_sun])

    async_add_entities(entities)


class ProxyBinarySensorEntity(BinarySensorEntity):
    """Binary sensor that displays data from a different coordinator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        source_coordinator: CoordinatorType,
        device_info: DeviceInfo,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize the proxy binary sensor."""
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

    @callback
    def _handle_source_update(self) -> None:
        """Handle source coordinator update."""
        self.async_write_ha_state()


class CoverRoomOccupiedProxySensor(ProxyBinarySensorEntity):
    """Proxy sensor showing room's occupied status on cover device."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_translation_key = "room_proxy_occupied"

    def __init__(
        self,
        source_coordinator: RoomCoordinator,
        cover_coordinator: AdaptiveDataUpdateCoordinator,
        cover_name: str,
        cover_id: str,
        room_id: str,
    ) -> None:
        """Initialize the proxy sensor."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, cover_id)},
            name=cover_name,
            via_device=(DOMAIN, f"room_{room_id}"),
        )
        super().__init__(
            source_coordinator=source_coordinator,
            device_info=device_info,
            unique_id=f"{cover_id}_room_proxy_occupied",
            name="Room Occupied (Room)",
        )
        self._attr_has_entity_name = False
        self._attr_name = f"{cover_name} Room Occupied (Room)"

    @property
    def is_on(self) -> bool | None:
        """Return room's occupied status."""
        if self._source_coordinator.data is None:
            return None
        return self._source_coordinator.data.is_presence

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._source_coordinator.data is None:
            return False
        sensor_avail = self._source_coordinator.data.sensor_available.get(
            "is_presence", False
        )
        has_value = (
            self._source_coordinator.data.last_known.get("is_presence") is not None
        )
        return sensor_avail or has_value


class CoverRoomDirectSunProxySensor(ProxyBinarySensorEntity):
    """Proxy sensor showing room's direct sun status on cover device."""

    _attr_device_class = BinarySensorDeviceClass.LIGHT
    _attr_translation_key = "room_proxy_direct_sun"

    def __init__(
        self,
        source_coordinator: RoomCoordinator,
        cover_coordinator: AdaptiveDataUpdateCoordinator,
        cover_name: str,
        cover_id: str,
        room_id: str,
    ) -> None:
        """Initialize the proxy sensor."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, cover_id)},
            name=cover_name,
            via_device=(DOMAIN, f"room_{room_id}"),
        )
        super().__init__(
            source_coordinator=source_coordinator,
            device_info=device_info,
            unique_id=f"{cover_id}_room_proxy_direct_sun",
            name="Has Direct Sun (Room)",
        )
        self._attr_has_entity_name = False
        self._attr_name = f"{cover_name} Has Direct Sun (Room)"

    @property
    def is_on(self) -> bool | None:
        """Return room's direct sun status."""
        if self._source_coordinator.data is None:
            return None
        return self._source_coordinator.data.has_direct_sun

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._source_coordinator.data is None:
            return False
        sensor_avail = self._source_coordinator.data.sensor_available.get(
            "has_direct_sun", False
        )
        has_value = (
            self._source_coordinator.data.last_known.get("has_direct_sun") is not None
        )
        return sensor_avail or has_value


class RoomCoverSunInfrontProxySensor(ProxyBinarySensorEntity):
    """Proxy sensor showing cover's sun infront status on room device."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "cover_proxy_sun_infront"

    def __init__(
        self,
        source_coordinator: AdaptiveDataUpdateCoordinator,
        room_coordinator: RoomCoordinator,
        cover_name: str,
        cover_id: str,
        room_id: str,
    ) -> None:
        """Initialize the proxy sensor."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"room_{room_id}")},
            name=f"Room: {room_coordinator.config_entry.data.get('name', 'Room')}",
        )
        super().__init__(
            source_coordinator=source_coordinator,
            device_info=device_info,
            unique_id=f"room_{room_id}_proxy_{cover_id}_sun_infront",
            name=f"{cover_name} Sun Infront",
        )

    @property
    def is_on(self) -> bool | None:
        """Return cover's sun infront status."""
        if self._source_coordinator.data is None:
            return None
        return self._source_coordinator.data.states.get("sun_motion")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._source_coordinator.data is None:
            return False
        return self._source_coordinator.data.states.get("sun_motion") is not None


class AdaptiveCoverBinarySensor(CoordinatorEntity[CoordinatorType], BinarySensorEntity):
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
        coordinator: CoordinatorType,
        is_room: bool = False,
        room_id: str | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator=coordinator)
        self._key = key
        self._attr_translation_key = key
        self._name = config_entry.data["name"]
        self._attr_unique_id = f"{unique_id}_{binary_name}"
        self._device_id = unique_id
        self._state = state
        self._attr_device_class = device_class
        self._is_room = is_room
        self._room_id = room_id

        # When cover belongs to a room, include cover name in entity name
        if room_id and not is_room:
            self._attr_has_entity_name = False
            self._attr_name = f"{self._name} {binary_name}"
        else:
            self._attr_name = binary_name

        # Set device info based on entry type
        if is_room:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"room_{self._device_id}")},
                name=f"Room: {self._name}",
            )
        else:
            info = DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=self._name,
            )
            if room_id:
                info["via_device"] = (DOMAIN, f"room_{room_id}")
            self._attr_device_info = info

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        # For room coordinator, data might not have states in same format
        if isinstance(self.coordinator, RoomCoordinator):
            if self.coordinator.data is None:
                return None
            if self._key == "is_presence":
                return self.coordinator.data.is_presence
            if self._key == "has_direct_sun":
                return self.coordinator.data.has_direct_sun
            return None
        return self.coordinator.data.states[self._key]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if coordinator is available first
        if not super().available:
            return False

        # For room coordinator
        if isinstance(self.coordinator, RoomCoordinator):
            if self.coordinator.data is None:
                return False
            if self._key == "has_direct_sun":
                # Available if sensor is available OR we have a last known value
                sensor_avail = self.coordinator.data.sensor_available.get(
                    "has_direct_sun", False
                )
                has_value = (
                    self.coordinator.data.last_known.get("has_direct_sun") is not None
                )
                return sensor_avail or has_value
            if self._key == "is_presence":
                # Available if sensor is available OR we have a last known value
                sensor_avail = self.coordinator.data.sensor_available.get(
                    "is_presence", False
                )
                has_value = (
                    self.coordinator.data.last_known.get("is_presence") is not None
                )
                return sensor_avail or has_value
            return True

        # For cover coordinator - check availability status
        if self._key == "has_direct_sun":
            return self.coordinator.data.states.get("has_direct_sun") is not None
        if self._key == "is_presence":
            return self.coordinator.data.states.get("is_presence") is not None
        return True

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        # For room coordinator
        if isinstance(self.coordinator, RoomCoordinator):
            if self.coordinator.data is None:
                return None
            if self._key == "has_direct_sun":
                return {
                    "sensor_available": self.coordinator.data.sensor_available.get(
                        "has_direct_sun"
                    ),
                    "using_last_known": not self.coordinator.data.sensor_available.get(
                        "has_direct_sun", True
                    ),
                    "current_value": self.coordinator.data.has_direct_sun,
                }
            if self._key == "is_presence":
                return {
                    "sensor_available": self.coordinator.data.sensor_available.get(
                        "is_presence"
                    ),
                    "using_last_known": not self.coordinator.data.sensor_available.get(
                        "is_presence", True
                    ),
                    "current_value": self.coordinator.data.is_presence,
                }
            return None

        # For cover coordinator
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
