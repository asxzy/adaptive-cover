"""Tests for ConfigContextAdapter."""

from __future__ import annotations

import logging

from custom_components.adaptive_cover.config_context_adapter import ConfigContextAdapter


class TestConfigContextAdapter:
    """Tests for ConfigContextAdapter class."""

    def test_init_with_logger(self) -> None:
        """Test initialization with a logger."""
        logger = logging.getLogger("test")
        adapter = ConfigContextAdapter(logger)

        assert adapter.config_name is None
        assert adapter.logger is logger

    def test_init_with_extra(self) -> None:
        """Test initialization with extra context."""
        logger = logging.getLogger("test")
        extra = {"key": "value"}
        adapter = ConfigContextAdapter(logger, extra)

        assert adapter.extra == extra

    def test_set_config_name(self) -> None:
        """Test setting config name."""
        adapter = ConfigContextAdapter(logging.getLogger("test"))
        adapter.set_config_name("my_config")

        assert adapter.config_name == "my_config"

    def test_process_with_config_name(self) -> None:
        """Test process adds config name prefix when set."""
        adapter = ConfigContextAdapter(logging.getLogger("test"))
        adapter.set_config_name("my_cover")

        msg, kwargs = adapter.process("Test message", {})

        assert msg == "[my_cover] Test message"
        assert kwargs == {}

    def test_process_without_config_name(self) -> None:
        """Test process adds Unknown prefix when config name not set."""
        adapter = ConfigContextAdapter(logging.getLogger("test"))
        # Don't set config_name, so it remains None

        msg, kwargs = adapter.process("Test message", {})

        assert msg == "[Unknown] Test message"
        assert kwargs == {}

    def test_process_preserves_kwargs(self) -> None:
        """Test that process preserves kwargs."""
        adapter = ConfigContextAdapter(logging.getLogger("test"))
        adapter.set_config_name("test")
        input_kwargs = {"extra_key": "extra_value"}

        msg, kwargs = adapter.process("Message", input_kwargs)

        assert kwargs == input_kwargs
