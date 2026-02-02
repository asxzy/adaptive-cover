"""Tests for diagnostics module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_cover.diagnostics import (
    async_get_config_entry_diagnostics,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestDiagnostics:
    """Tests for diagnostics functions."""

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics(
        self, hass: HomeAssistant
    ) -> None:
        """Test getting config entry diagnostics."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_123"
        mock_entry.data = {"name": "Test Cover", "sensor_type": "cover_blind"}
        mock_entry.options = {"azimuth": 180, "fov_left": 90}

        result = await async_get_config_entry_diagnostics(hass, mock_entry)

        assert result["title"] == "Adaptive Cover Configuration"
        assert result["type"] == "config_entry"
        assert result["identifier"] == "test_entry_123"
        assert result["config_data"] == {
            "name": "Test Cover",
            "sensor_type": "cover_blind",
        }
        assert result["config_options"] == {"azimuth": 180, "fov_left": 90}

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_empty_data(
        self, hass: HomeAssistant
    ) -> None:
        """Test getting diagnostics with empty data."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "empty_entry"
        mock_entry.data = {}
        mock_entry.options = {}

        result = await async_get_config_entry_diagnostics(hass, mock_entry)

        assert result["identifier"] == "empty_entry"
        assert result["config_data"] == {}
        assert result["config_options"] == {}
