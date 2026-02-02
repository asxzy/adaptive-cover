"""Integration tests for AdaptiveDataUpdateCoordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock


from custom_components.adaptive_cover.coordinator import (
    AdaptiveCoverManager,
    StateChangedData,
    inverse_state,
)

if TYPE_CHECKING:
    from custom_components.adaptive_cover.config_context_adapter import (
        ConfigContextAdapter,
    )


class TestInverseState:
    """Tests for inverse_state function."""

    def test_inverse_state_zero(self) -> None:
        """Test inverting 0 returns 100."""
        assert inverse_state(0) == 100

    def test_inverse_state_100(self) -> None:
        """Test inverting 100 returns 0."""
        assert inverse_state(100) == 0

    def test_inverse_state_50(self) -> None:
        """Test inverting 50 returns 50."""
        assert inverse_state(50) == 50

    def test_inverse_state_25(self) -> None:
        """Test inverting 25 returns 75."""
        assert inverse_state(25) == 75


class TestStateChangedData:
    """Tests for StateChangedData dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test StateChangedData can be created with all fields."""
        old_state = MagicMock()
        new_state = MagicMock()

        data = StateChangedData(
            entity_id="cover.test", old_state=old_state, new_state=new_state
        )

        assert data.entity_id == "cover.test"
        assert data.old_state is old_state
        assert data.new_state is new_state

    def test_creates_with_none_states(self) -> None:
        """Test StateChangedData can be created with None states."""
        data = StateChangedData(entity_id="cover.test", old_state=None, new_state=None)

        assert data.entity_id == "cover.test"
        assert data.old_state is None
        assert data.new_state is None


class TestAdaptiveCoverManager:
    """Tests for AdaptiveCoverManager class."""

    def test_add_covers(self, mock_logger: ConfigContextAdapter) -> None:
        """Test adding covers to manager."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)

        manager.add_covers(["cover.living_room", "cover.bedroom"])

        assert "cover.living_room" in manager.covers
        assert "cover.bedroom" in manager.covers

    def test_add_covers_updates_existing(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test adding covers updates existing set."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)

        manager.add_covers(["cover.living_room"])
        manager.add_covers(["cover.bedroom"])

        assert len(manager.covers) == 2
        assert "cover.living_room" in manager.covers
        assert "cover.bedroom" in manager.covers

    def test_handle_state_change_none_event(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change with None event."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)

        # Should not raise error
        manager.handle_state_change(
            None,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={},
            manual_threshold=5,
        )

    def test_handle_state_change_entity_not_tracked(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change with untracked entity."""
        coordinator = MagicMock()
        coordinator.control_mode = "auto"  # Initial state
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        event = StateChangedData(
            entity_id="cover.other_room",
            old_state=MagicMock(),
            new_state=MagicMock(),
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={},
            manual_threshold=5,
        )

        # Should not change control mode for untracked entity
        assert coordinator.control_mode == "auto"

    def test_handle_state_change_waiting_for_target(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when waiting for target position."""
        coordinator = MagicMock()
        coordinator.control_mode = "auto"  # Initial state
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=MagicMock(),
        )

        # When wait_target_call is True for entity, should skip
        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": True},
            manual_threshold=5,
        )

        # Should not change control mode when waiting for target
        assert coordinator.control_mode == "auto"

    def test_handle_state_change_manual_change_detected(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when manual change is detected."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 80}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Should set control mode to disabled (OFF) due to manual change
        # The change of 30 (80 - 50) exceeds threshold of 5
        assert coordinator.control_mode == "disabled"

    def test_handle_state_change_below_threshold(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when change is below threshold."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 52}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Should not change control mode - change of 2 is below threshold of 5
        # Note: control_mode should not be set
        # We need to check it wasn't set to disabled
        assert coordinator.control_mode != "disabled"

    def test_handle_state_change_tilt_cover(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change for tilt covers uses tilt_position."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {
            "current_position": 100,
            "current_tilt_position": 80,
        }

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_tilt",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Should detect manual change using tilt position (80 vs 50 = 30)
        assert coordinator.control_mode == "disabled"

    def test_handle_state_change_no_threshold(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change with no threshold set."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 51}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=None,
        )

        # With no threshold, any change should trigger manual detection
        assert coordinator.control_mode == "disabled"

    def test_handle_state_change_same_position(
        self, mock_logger: ConfigContextAdapter
    ) -> None:
        """Test handle_state_change when position matches our state."""
        coordinator = MagicMock()
        manager = AdaptiveCoverManager(mock_logger, coordinator)
        manager.add_covers(["cover.living_room"])

        new_state = MagicMock()
        new_state.attributes = {"current_position": 50}

        event = StateChangedData(
            entity_id="cover.living_room",
            old_state=MagicMock(),
            new_state=new_state,
        )

        manager.handle_state_change(
            event,
            our_state=50,
            blind_type="cover_blind",
            wait_target_call={"cover.living_room": False},
            manual_threshold=5,
        )

        # Position matches, should not trigger manual detection
        assert coordinator.control_mode != "disabled"
