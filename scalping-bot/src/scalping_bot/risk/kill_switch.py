"""Kill switch — emergency shutdown with three states.

States:
  RUNNING   — normal operation, trading allowed
  PAUSED    — soft pause, automatically recoverable after cooldown
  KILLED    — hard stop, requires explicit manual reset by operator

Transitions are one-directional-ish:
  RUNNING --trigger_pause--> PAUSED --cooldown--> RUNNING
  RUNNING --trigger_kill---> KILLED --manual_reset--> RUNNING
  PAUSED  --trigger_kill---> KILLED

Every transition is recorded as a KillEvent with timestamp and reason.
This gives us an audit trail for post-mortem analysis after incidents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum


class SwitchState(Enum):
    """Kill switch states. Order reflects increasing severity."""

    RUNNING = "running"
    PAUSED = "paused"
    KILLED = "killed"


@dataclass(frozen=True)
class KillEvent:
    """Immutable record of a state transition."""

    timestamp: datetime
    trigger: str
    state_before: SwitchState
    state_after: SwitchState
    details: dict[str, object] = field(default_factory=dict)


class KillSwitch:
    """Thread-unsafe kill switch. Wrap in a lock if used across threads."""

    def __init__(self) -> None:
        self._state: SwitchState = SwitchState.RUNNING
        self._events: list[KillEvent] = []
        self._pause_until: datetime | None = None

    # --- State queries ------------------------------------------------------

    @property
    def state(self) -> SwitchState:
        """Current state, with automatic pause-expiration handling."""
        if (
            self._state == SwitchState.PAUSED
            and self._pause_until is not None
            and self._now() >= self._pause_until
        ):
            self._transition(
                SwitchState.RUNNING,
                trigger="pause_cooldown_expired",
                details={"pause_until": self._pause_until.isoformat()},
            )
            self._pause_until = None
        return self._state

    def can_trade(self) -> bool:
        """True iff state is RUNNING (after auto-expiration check)."""
        return self.state == SwitchState.RUNNING

    @property
    def events(self) -> tuple[KillEvent, ...]:
        """Immutable view of the event log."""
        return tuple(self._events)

    # --- Transitions --------------------------------------------------------

    def trigger_kill(self, reason: str, details: dict[str, object] | None = None) -> None:
        """Hard stop. Requires explicit manual reset to recover."""
        self._transition(
            SwitchState.KILLED,
            trigger=f"kill:{reason}",
            details=details or {},
        )

    def trigger_pause(
        self,
        reason: str,
        duration_seconds: int,
        details: dict[str, object] | None = None,
    ) -> None:
        """Soft pause with automatic recovery after `duration_seconds`.

        If currently KILLED, this is a no-op (kill supersedes pause).
        If currently PAUSED, extends pause if new duration is longer.
        """
        if self._state == SwitchState.KILLED:
            return

        if duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be positive, got {duration_seconds}")

        new_pause_until = self._now() + timedelta(seconds=duration_seconds)

        # Extend pause, never shorten
        if self._pause_until is None or new_pause_until > self._pause_until:
            self._pause_until = new_pause_until

        if self._state != SwitchState.PAUSED:
            payload: dict[str, object] = {
                "duration_seconds": duration_seconds,
                "pause_until": self._pause_until.isoformat(),
            }
            payload.update(details or {})
            self._transition(
                SwitchState.PAUSED,
                trigger=f"pause:{reason}",
                details=payload,
            )

    def manual_reset(self, by: str) -> bool:
        """Reset from KILLED back to RUNNING. Requires operator identity.

        Returns True if the reset happened, False if no-op (not KILLED).
        """
        if self._state != SwitchState.KILLED:
            return False
        self._transition(
            SwitchState.RUNNING,
            trigger=f"manual_reset:{by}",
            details={"reset_by": by},
        )
        self._pause_until = None
        return True

    # --- Internals ----------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def _transition(
        self,
        new_state: SwitchState,
        trigger: str,
        details: dict[str, object],
    ) -> None:
        before = self._state
        self._state = new_state
        event = KillEvent(
            timestamp=self._now(),
            trigger=trigger,
            state_before=before,
            state_after=new_state,
            details=dict(details),
        )
        self._events.append(event)
