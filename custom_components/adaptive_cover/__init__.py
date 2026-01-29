"""The Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import (
    CONF_CLOUD_ENTITY,
    CONF_END_ENTITY,
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_PRESENCE_ENTITY,
    CONF_ROOM_ID,
    CONF_TEMP_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
    EntryType,
    _LOGGER,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .room_coordinator import RoomCoordinator

# Platforms for room entries
ROOM_PLATFORMS = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]

# Platforms for cover entries that are part of a room
COVER_IN_ROOM_PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

# Platforms for standalone cover entries (all platforms)
STANDALONE_COVER_PLATFORMS = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

# All possible platforms (for unload)
ALL_PLATFORMS = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_initialize_integration(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> bool:
    """Initialize the integration."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Cover from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    entry_type = entry.data.get(CONF_ENTRY_TYPE)
    _LOGGER.debug("Setting up entry %s (type: %s)", entry.data.get("name"), entry_type)

    # Handle room entry
    if entry_type == EntryType.ROOM:
        return await _async_setup_room_entry(hass, entry)

    # Handle cover entry (standalone or part of room)
    return await _async_setup_cover_entry(hass, entry)


async def _async_setup_room_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a room entry."""
    coordinator = RoomCoordinator(hass, entry)

    # Get entities to track from room options
    _temp_entity = entry.options.get(CONF_TEMP_ENTITY)
    _presence_entity = entry.options.get(CONF_PRESENCE_ENTITY)
    _weather_entity = entry.options.get(CONF_WEATHER_ENTITY)
    _end_time_entity = entry.options.get(CONF_END_ENTITY)
    _cloud_entity = entry.options.get(CONF_CLOUD_ENTITY)

    _entities = ["sun.sun"]
    for entity in [
        _temp_entity,
        _presence_entity,
        _weather_entity,
        _end_time_entity,
        _cloud_entity,
    ]:
        if entity is not None:
            _entities.append(entity)

    # Track state changes for room-level entities
    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            _entities,
            coordinator.async_check_entity_state_change,
        )
    )

    await coordinator.async_config_entry_first_refresh()

    # Store room coordinator with room_ prefix for lookup by covers
    hass.data[DOMAIN][f"room_{entry.entry_id}"] = coordinator
    # Also store with entry_id for standard lookup
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ROOM_PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_setup_cover_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a cover entry (standalone or part of room)."""
    room_id = entry.data.get(CONF_ROOM_ID)
    room_coordinator = None

    # If part of a room, get the room coordinator
    if room_id:
        room_coordinator = hass.data[DOMAIN].get(f"room_{room_id}")
        if room_coordinator is None:
            _LOGGER.warning(
                "Room %s not found for cover %s, treating as standalone",
                room_id,
                entry.data.get("name"),
            )

    # Create cover coordinator
    coordinator = AdaptiveDataUpdateCoordinator(hass, entry, room_coordinator)

    # Determine which options to use for entity tracking
    if room_coordinator:
        # Use room's options for shared entities
        options = room_coordinator.config_entry.options
        platforms = COVER_IN_ROOM_PLATFORMS
    else:
        # Use cover's own options
        options = entry.options
        platforms = STANDALONE_COVER_PLATFORMS

    # Get entities to track
    _temp_entity = options.get(CONF_TEMP_ENTITY)
    _presence_entity = options.get(CONF_PRESENCE_ENTITY)
    _weather_entity = options.get(CONF_WEATHER_ENTITY)
    _end_time_entity = options.get(CONF_END_ENTITY)
    _cloud_entity = options.get(CONF_CLOUD_ENTITY)
    _cover_entities = entry.options.get(CONF_ENTITIES, [])

    _entities = ["sun.sun"]
    for entity in [
        _temp_entity,
        _presence_entity,
        _weather_entity,
        _end_time_entity,
        _cloud_entity,
    ]:
        if entity is not None:
            _entities.append(entity)

    # Track state changes for entities
    # Only track if standalone (room handles tracking for room members)
    if not room_coordinator:
        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                _entities,
                coordinator.async_check_entity_state_change,
            )
        )

    # Always track cover entity changes
    if _cover_entities:
        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                _cover_entities,
                coordinator.async_check_cover_state_change,
            )
        )

    await coordinator.async_config_entry_first_refresh()

    # Register with room coordinator if part of a room
    if room_coordinator:
        room_coordinator.register_cover(coordinator)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_type = entry.data.get(CONF_ENTRY_TYPE)

    # Determine which platforms to unload
    if entry_type == EntryType.ROOM:
        platforms = ROOM_PLATFORMS
    elif entry.data.get(CONF_ROOM_ID):
        platforms = COVER_IN_ROOM_PLATFORMS
    else:
        platforms = STANDALONE_COVER_PLATFORMS

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, platforms):
        # Unregister cover from room if part of a room
        room_id = entry.data.get(CONF_ROOM_ID)
        if room_id:
            room_coordinator = hass.data[DOMAIN].get(f"room_{room_id}")
            coordinator = hass.data[DOMAIN].get(entry.entry_id)
            if room_coordinator and coordinator:
                room_coordinator.unregister_cover(coordinator)

        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Also remove room_ prefixed key for room entries
        if entry_type == EntryType.ROOM:
            hass.data[DOMAIN].pop(f"room_{entry.entry_id}", None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
