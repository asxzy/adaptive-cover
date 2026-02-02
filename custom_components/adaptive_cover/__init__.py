"""The Adaptive Cover integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
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
    SIGNAL_ROOM_LOADED,
    _LOGGER,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .room_coordinator import RoomCoordinator

# Timeout for waiting for room to load (in seconds)
ROOM_WAIT_TIMEOUT = 30

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

    # Store room coordinator early so covers can find it during their setup
    hass.data[DOMAIN][f"room_{entry.entry_id}"] = coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    # Discover existing covers that belong to this room (handles reload case)
    await coordinator.async_discover_existing_covers()

    await hass.config_entries.async_forward_entry_setups(entry, ROOM_PLATFORMS)

    # Fire signal to notify any covers waiting for this room
    async_dispatcher_send(hass, f"{SIGNAL_ROOM_LOADED}_{entry.entry_id}")

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_setup_cover_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a cover entry (standalone or part of room)."""
    room_id = entry.data.get(CONF_ROOM_ID)
    room_coordinator = None

    # If part of a room, wait for room coordinator to be ready
    if room_id:
        room_coordinator = hass.data[DOMAIN].get(f"room_{room_id}")
        if room_coordinator is None:
            # Room not loaded yet - wait for signal with timeout
            _LOGGER.debug(
                "Room %s not yet loaded for cover %s, waiting...",
                room_id,
                entry.data.get("name"),
            )
            room_coordinator = await _async_wait_for_room(hass, room_id, entry)
            if room_coordinator is None:
                _LOGGER.error(
                    "Timeout waiting for room %s to load for cover %s. "
                    "Cover will operate in standalone mode.",
                    room_id,
                    entry.data.get("name"),
                )
                # Fall back to standalone mode - clear room_id for this session
                room_id = None

    # Create cover coordinator
    coordinator = AdaptiveDataUpdateCoordinator(hass, entry, room_coordinator)

    # Store coordinator so it's available for room discovery on reload
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Determine which options/platforms to use
    if room_coordinator:
        # Use room's options for shared entities
        options = room_coordinator.config_entry.options
        platforms = COVER_IN_ROOM_PLATFORMS
    else:
        # Standalone cover
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
        await room_coordinator.async_refresh()  # Trigger room sensors to update

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_wait_for_room(
    hass: HomeAssistant, room_id: str, entry: ConfigEntry
) -> RoomCoordinator | None:
    """Wait for room coordinator to become available.

    Uses dispatcher signal with asyncio.Event for synchronization.
    Returns the room coordinator if found within timeout, None otherwise.
    """
    room_ready = asyncio.Event()
    room_coordinator_holder: list[RoomCoordinator | None] = [None]

    @callback
    def _room_loaded_callback() -> None:
        """Handle room loaded signal."""
        room_coordinator_holder[0] = hass.data[DOMAIN].get(f"room_{room_id}")
        room_ready.set()

    # Subscribe to room loaded signal
    unsub = async_dispatcher_connect(
        hass, f"{SIGNAL_ROOM_LOADED}_{room_id}", _room_loaded_callback
    )

    try:
        # Check if room became available while we were setting up
        room_coordinator = hass.data[DOMAIN].get(f"room_{room_id}")
        if room_coordinator is not None:
            _LOGGER.debug(
                "Room %s became available during setup for cover %s",
                room_id,
                entry.data.get("name"),
            )
            return room_coordinator

        # Wait for room signal with timeout
        await asyncio.wait_for(room_ready.wait(), timeout=ROOM_WAIT_TIMEOUT)
        _LOGGER.debug(
            "Room %s loaded, continuing setup for cover %s",
            room_id,
            entry.data.get("name"),
        )
        return room_coordinator_holder[0]
    except TimeoutError:
        return None
    finally:
        unsub()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_type = entry.data.get(CONF_ENTRY_TYPE)

    # Get old room_id from runtime_data if available (set by _async_update_listener)
    # This handles the case where cover was moved between rooms or removed from a room
    old_room_id = None
    if hasattr(entry, "runtime_data") and entry.runtime_data:
        old_room_id = entry.runtime_data.get("_old_room_id")

    # Use old room_id for determining platforms and unregistering
    room_id_for_unload = (
        old_room_id if old_room_id is not None else entry.data.get(CONF_ROOM_ID)
    )

    # Determine which platforms to unload based on the OLD state
    if entry_type == EntryType.ROOM:
        platforms = ROOM_PLATFORMS
    elif room_id_for_unload:
        platforms = COVER_IN_ROOM_PLATFORMS
    else:
        platforms = STANDALONE_COVER_PLATFORMS

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, platforms):
        # Unregister cover from room if it was part of a room
        if room_id_for_unload:
            room_coordinator = hass.data[DOMAIN].get(f"room_{room_id_for_unload}")
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
    # Capture old room_id before reload so unload can unregister from correct room
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    old_room_id = None
    if (
        coordinator
        and hasattr(coordinator, "room_coordinator")
        and coordinator.room_coordinator
    ):
        old_room_id = coordinator.room_coordinator.config_entry.entry_id

    # Store old room_id in runtime_data for async_unload_entry to use
    entry.runtime_data = {"_old_room_id": old_room_id}

    await hass.config_entries.async_reload(entry.entry_id)
