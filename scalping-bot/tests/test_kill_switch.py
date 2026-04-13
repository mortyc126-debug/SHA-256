"""Tests for the kill switch state machine.

Critical properties under test:
  - Starts in RUNNING
  - trigger_kill is irreversible without manual_reset
  - trigger_pause auto-expires after cooldown
  - can_trade reflects state correctly
  - Events are recorded for every transition
"""

from __future__ import annotations

import time

import pytest

from scalping_bot.risk.kill_switch import KillSwitch, SwitchState


class TestInitialState:
    def test_starts_running(self) -> None:
        ks = KillSwitch()
        assert ks.state == SwitchState.RUNNING
        assert ks.can_trade()

    def test_starts_with_empty_event_log(self) -> None:
        ks = KillSwitch()
        assert ks.events == ()


class TestKillTrigger:
    def test_trigger_kill_changes_state(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("daily_loss_exceeded")
        assert ks.state == SwitchState.KILLED
        assert not ks.can_trade()

    def test_trigger_kill_records_event(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("test_reason", details={"extra": "info"})
        events = ks.events
        assert len(events) == 1
        event = events[0]
        assert event.state_before == SwitchState.RUNNING
        assert event.state_after == SwitchState.KILLED
        assert event.trigger == "kill:test_reason"
        assert event.details == {"extra": "info"}

    def test_kill_is_sticky_without_reset(self) -> None:
        """Once KILLED, state stays KILLED no matter what."""
        ks = KillSwitch()
        ks.trigger_kill("reason_a")
        # Attempting to pause should be no-op
        ks.trigger_pause("reason_b", duration_seconds=60)
        assert ks.state == SwitchState.KILLED
        assert not ks.can_trade()

    def test_multiple_kills_record_multiple_events(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("first")
        ks.trigger_kill("second")  # stays KILLED but logged
        assert len(ks.events) == 2
        assert ks.events[1].state_before == SwitchState.KILLED
        assert ks.events[1].state_after == SwitchState.KILLED


class TestPauseTrigger:
    def test_pause_changes_state(self) -> None:
        ks = KillSwitch()
        ks.trigger_pause("consecutive_losses", duration_seconds=60)
        assert ks.state == SwitchState.PAUSED
        assert not ks.can_trade()

    def test_pause_auto_expires(self) -> None:
        ks = KillSwitch()
        # Very short pause so we can actually wait
        ks.trigger_pause("test", duration_seconds=1)
        assert ks.state == SwitchState.PAUSED
        time.sleep(1.1)
        # Accessing .state triggers the auto-expire check
        assert ks.state == SwitchState.RUNNING
        assert ks.can_trade()

    def test_pause_can_be_extended(self) -> None:
        ks = KillSwitch()
        ks.trigger_pause("first", duration_seconds=1)
        ks.trigger_pause("extended", duration_seconds=60)
        assert ks.state == SwitchState.PAUSED
        time.sleep(1.1)
        # First pause would have expired, but extended one hasn't
        assert ks.state == SwitchState.PAUSED

    def test_pause_cannot_be_shortened(self) -> None:
        ks = KillSwitch()
        ks.trigger_pause("long", duration_seconds=60)
        ks.trigger_pause("short", duration_seconds=1)
        # Short attempt should not undo long pause
        time.sleep(1.1)
        assert ks.state == SwitchState.PAUSED

    def test_pause_rejects_non_positive_duration(self) -> None:
        ks = KillSwitch()
        with pytest.raises(ValueError, match="positive"):
            ks.trigger_pause("test", duration_seconds=0)
        with pytest.raises(ValueError, match="positive"):
            ks.trigger_pause("test", duration_seconds=-5)

    def test_pause_does_not_fire_when_killed(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("urgent")
        ks.trigger_pause("whatever", duration_seconds=60)
        assert ks.state == SwitchState.KILLED

    def test_pause_expiry_records_event(self) -> None:
        ks = KillSwitch()
        ks.trigger_pause("test", duration_seconds=1)
        time.sleep(1.1)
        _ = ks.state  # trigger expiry check
        events = ks.events
        assert len(events) == 2
        assert events[-1].trigger == "pause_cooldown_expired"
        assert events[-1].state_after == SwitchState.RUNNING


class TestManualReset:
    def test_manual_reset_restores_running_from_killed(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("emergency")
        assert ks.state == SwitchState.KILLED
        reset_ok = ks.manual_reset(by="operator")
        assert reset_ok
        assert ks.state == SwitchState.RUNNING
        assert ks.can_trade()

    def test_manual_reset_records_event_with_operator(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("reason")
        ks.manual_reset(by="alice")
        event = ks.events[-1]
        assert event.trigger == "manual_reset:alice"
        assert event.details["reset_by"] == "alice"

    def test_manual_reset_is_noop_when_running(self) -> None:
        ks = KillSwitch()
        reset_ok = ks.manual_reset(by="operator")
        assert not reset_ok
        assert ks.state == SwitchState.RUNNING

    def test_manual_reset_is_noop_when_paused(self) -> None:
        """Paused should auto-recover; no manual reset needed or allowed."""
        ks = KillSwitch()
        ks.trigger_pause("test", duration_seconds=60)
        reset_ok = ks.manual_reset(by="operator")
        assert not reset_ok
        assert ks.state == SwitchState.PAUSED


class TestEventImmutability:
    def test_events_tuple_is_a_snapshot(self) -> None:
        ks = KillSwitch()
        ks.trigger_kill("first")
        snapshot = ks.events
        ks.trigger_kill("second")  # another event, log grows
        # Previous snapshot should be unchanged (tuple)
        assert len(snapshot) == 1
        assert len(ks.events) == 2

    def test_event_details_are_isolated(self) -> None:
        """Mutating the dict passed in shouldn't affect the stored event."""
        ks = KillSwitch()
        my_dict: dict[str, object] = {"key": "original"}
        ks.trigger_kill("test", details=my_dict)
        my_dict["key"] = "changed"
        assert ks.events[0].details["key"] == "original"
