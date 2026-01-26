# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adaptive Cover is a Home Assistant custom integration that calculates optimal blind/cover positions based on sun position to filter direct sunlight. It supports three cover types: vertical blinds, horizontal awnings, and venetian (tilted) blinds.

## Development Commands

```bash
# Setup development environment (install deps + pre-commit hooks)
./scripts/setup

# Run linter with auto-fix
./scripts/lint

# Start Home Assistant dev server (port 8123)
./scripts/develop

# Format code manually
ruff check . --fix
ruff format .
```

## Architecture

### Core Components

- **`coordinator.py`** - `AdaptiveDataUpdateCoordinator`: Central hub that tracks state changes from sun, temperature, weather, and cover entities. Triggers position recalculations and manages cover control.

- **`calculation.py`** - Cover position calculation classes:
  - `AdaptiveVerticalCover` - Up/down blinds
  - `AdaptiveHorizontalCover` - In/out awnings
  - `AdaptiveTiltCover` - Venetian blind slat angles
  - `ClimateCoverState` / `NormalCoverState` - Strategy patterns for climate vs basic mode

- **`sun.py`** - `SunData`: Uses astral library to calculate solar azimuth/elevation at 5-minute intervals throughout the day.

- **`config_flow.py`** - Configuration UI with extensive options for window parameters, climate settings, and automation rules.

### Platform Entities

The integration creates entities across four platforms:
- `sensor` - Position values, start/end times, control method
- `switch` - Toggle control, climate mode, manual override detection
- `binary_sensor` - Manual override status, sun-in-front detection
- `button` - Reset manual override

### Data Flow

1. `sun.sun` state changes trigger `coordinator.async_check_entity_state_change`
2. Coordinator retrieves current sun position, temperature, weather, presence
3. Calculation classes compute optimal position based on mode (basic/climate)
4. Position sensor updates; if control is enabled, cover service calls are made

## Key Dependencies

- `astral` - Solar position calculations via Home Assistant's `get_astral_location`
- `pandas` - Time series for solar position data throughout the day
- `numpy` - Trigonometric calculations for shade angles

## Configuration Constants

All configuration keys are in `const.py`. Key prefixes:
- `CONF_*` - Configuration option keys
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
