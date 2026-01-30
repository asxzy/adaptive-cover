# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adaptive Cover is a Home Assistant custom integration that calculates optimal blind/cover positions based on sun position to filter direct sunlight. It supports three cover types: vertical blinds, horizontal awnings, and venetian (tilted) blinds.

## Development Commands

```bash
# Setup development environment (install deps + pre-commit hooks)
./scripts/setup

# Run linter with auto-fix
uvx ruff check . --fix

# Format code
uvx ruff format .

# Start Home Assistant dev server (port 8123)
./scripts/develop
```

## Architecture

### Entry Type Hierarchy

The integration uses a **Room → Cover** hierarchy defined in `__init__.py`:

- **Room Entry** (`EntryType.ROOM`): Container for shared settings (climate sensors, presence, weather). Creates `RoomCoordinator`. Stored with `room_{entry_id}` prefix for cover lookups.
- **Cover Entry**: Can be standalone or belong to a room via `CONF_ROOM_ID`. Creates `AdaptiveDataUpdateCoordinator`.

Platform assignment varies by entry type:
- Room: `ROOM_PLATFORMS` (sensor, select, switch, binary_sensor)
- Cover in room: `COVER_IN_ROOM_PLATFORMS` (sensor, binary_sensor, button)
- Standalone cover: `STANDALONE_COVER_PLATFORMS` (all platforms)

### Core Components

- **`room_coordinator.py`** - `RoomCoordinator`: Manages room-level shared state (control mode, sensor toggles, climate data). Aggregates data from child covers via `start_sun`, `end_sun`, `comfort_status` properties. Child coordinators register via `register_cover()`.

- **`coordinator.py`** - `AdaptiveDataUpdateCoordinator`: Per-cover coordinator that tracks state changes from sun, temperature, weather, and cover entities. References `room_coordinator` if part of a room. Triggers position recalculations and manages cover control.

- **`calculation.py`** - Cover position calculation classes:
  - `AdaptiveVerticalCover` - Up/down blinds
  - `AdaptiveHorizontalCover` - In/out awnings
  - `AdaptiveTiltCover` - Venetian blind slat angles
  - `ClimateCoverState` / `NormalCoverState` - Strategy patterns for climate vs basic mode

- **`sun.py`** - `SunData`: Uses astral library to calculate solar azimuth/elevation at 5-minute intervals throughout the day.

- **`config_flow.py`** - Configuration UI with extensive options for window parameters, climate settings, and automation rules.

### Data Flow

1. `sun.sun` state changes trigger coordinator's `async_check_entity_state_change`
2. For room members: Room coordinator notifies children via `async_notify_children()`
3. Coordinator retrieves current sun position, temperature, weather, presence
4. Calculation classes compute optimal position based on mode (basic/climate)
5. Position sensor updates; if control is enabled, cover service calls are made
6. Room aggregates child data for room-level sensors (start/end sun times, comfort status)

### Coordinator Registration Flow

When a cover belongs to a room (`CONF_ROOM_ID` set):
1. Room entry sets up first, stores coordinator at `hass.data[DOMAIN][f"room_{entry_id}"]`
2. Cover entry looks up room coordinator, passes to `AdaptiveDataUpdateCoordinator`
3. After cover's first refresh, `room_coordinator.register_cover(coordinator)` is called
4. Room's `async_refresh()` triggers to update aggregated sensors

## Key Dependencies

- `astral` - Solar position calculations via Home Assistant's `get_astral_location`
- `pandas` - Time series for solar position data throughout the day
- `numpy` - Trigonometric calculations for shade angles

## Configuration Constants

All configuration keys are in `const.py`. Key prefixes:
- `CONF_*` - Configuration option keys
- `CONF_ENTRY_TYPE` / `CONF_ROOM_ID` - Entry hierarchy identifiers
- Window geometry: `CONF_AZIMUTH`, `CONF_HEIGHT_WIN`, `CONF_FOV_LEFT/RIGHT`
- Climate: `CONF_TEMP_ENTITY`, `CONF_TEMP_LOW/HIGH`, `CONF_WEATHER_ENTITY`
- Automation: `CONF_DELTA_POSITION`, `CONF_DELTA_TIME`, `CONF_MANUAL_OVERRIDE_*`

## Testing

No unit test framework. Testing is done via:
1. Home Assistant dev server (`./scripts/develop`)
2. CI validation: hassfest (manifest) and HACS checks
3. Jupyter notebook at `notebooks/test_env.ipynb` for simulation/visualization

## Code Style

- Ruff with `select = ["ALL"]` (aggressive linting)
- Pre-commit hooks enforce formatting
- Target Python 3.12
- Follow Home Assistant integration patterns (DataUpdateCoordinator, ConfigEntry, etc.)

## Debugging

Use `ConfigContextAdapter` logger wrapper (from `config_context_adapter.py`) for context-aware logging. Room and cover coordinators use this to prefix logs with entry name.

Enable debug logging in Home Assistant:
```yaml
logger:
  logs:
    custom_components.adaptive_cover: debug
```
