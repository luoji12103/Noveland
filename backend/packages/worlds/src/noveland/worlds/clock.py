from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from enum import StrEnum


class WorldClockStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"


class WorldClockTransitionType(StrEnum):
    INITIALIZE = "initialize"
    PAUSE = "pause"
    RESUME = "resume"
    ADVANCE = "advance"
    SKIP = "skip"


class WorldClockError(ValueError):
    """Base error for invalid world clock state or transition inputs."""


class WorldClockStateError(WorldClockError):
    """Raised when clock state invariants are violated."""


class WorldClockTimeError(WorldClockError):
    """Raised when wall-time or world-time inputs are invalid."""


ClockSpeedInput = Decimal | int | float | str


@dataclass(frozen=True, slots=True)
class WorldClockState:
    world_id: uuid.UUID
    status: WorldClockStatus
    current_world_time: datetime
    wall_time_anchor: datetime | None
    speed_multiplier: Decimal = Decimal("1")
    revision: int = 0

    def __post_init__(self) -> None:
        try:
            status = WorldClockStatus(self.status)
        except ValueError as exc:
            raise WorldClockStateError("status must be a valid world clock status") from exc

        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "current_world_time",
            _normalize_datetime(self.current_world_time, "current_world_time"),
        )

        if self.wall_time_anchor is not None:
            object.__setattr__(
                self,
                "wall_time_anchor",
                _normalize_datetime(self.wall_time_anchor, "wall_time_anchor"),
            )

        object.__setattr__(
            self,
            "speed_multiplier",
            _coerce_multiplier(self.speed_multiplier),
        )

        if self.revision < 0:
            raise WorldClockStateError("revision must be non-negative")

        if self.status is WorldClockStatus.RUNNING and self.wall_time_anchor is None:
            raise WorldClockStateError("running clocks require a wall_time_anchor")

        if self.status is WorldClockStatus.PAUSED and self.wall_time_anchor is not None:
            raise WorldClockStateError("paused clocks must not keep a wall_time_anchor")


@dataclass(frozen=True, slots=True)
class ClockTransition:
    transition_type: WorldClockTransitionType
    previous_state: WorldClockState
    new_state: WorldClockState
    wall_time: datetime
    previous_world_time: datetime
    new_world_time: datetime
    reason: str | None = None

    def __post_init__(self) -> None:
        try:
            transition_type = WorldClockTransitionType(self.transition_type)
        except ValueError as exc:
            raise WorldClockStateError("transition_type must be a valid clock transition") from exc

        object.__setattr__(self, "transition_type", transition_type)
        object.__setattr__(self, "wall_time", _normalize_datetime(self.wall_time, "wall_time"))
        object.__setattr__(
            self,
            "previous_world_time",
            _normalize_datetime(self.previous_world_time, "previous_world_time"),
        )
        object.__setattr__(
            self,
            "new_world_time",
            _normalize_datetime(self.new_world_time, "new_world_time"),
        )


def current_world_time_at(state: WorldClockState, wall_time: datetime) -> datetime:
    normalized_wall_time = _normalize_datetime(wall_time, "wall_time")

    if state.status is WorldClockStatus.PAUSED:
        return state.current_world_time

    wall_time_anchor = state.wall_time_anchor
    if wall_time_anchor is None:
        raise WorldClockStateError("running clocks require a wall_time_anchor")

    if normalized_wall_time < wall_time_anchor:
        raise WorldClockTimeError("wall_time cannot be earlier than the state's wall_time_anchor")

    wall_elapsed = normalized_wall_time - wall_time_anchor
    return state.current_world_time + _scale_elapsed(wall_elapsed, state.speed_multiplier)


def pause_clock(
    state: WorldClockState,
    wall_time: datetime,
    reason: str | None = None,
) -> ClockTransition:
    _require_status(state, WorldClockStatus.RUNNING, "pause")
    normalized_wall_time = _normalize_datetime(wall_time, "wall_time")
    effective_world_time = current_world_time_at(state, normalized_wall_time)
    new_state = WorldClockState(
        world_id=state.world_id,
        status=WorldClockStatus.PAUSED,
        current_world_time=effective_world_time,
        wall_time_anchor=None,
        speed_multiplier=state.speed_multiplier,
        revision=state.revision + 1,
    )
    return _transition(
        WorldClockTransitionType.PAUSE,
        state,
        new_state,
        normalized_wall_time,
        effective_world_time,
        reason,
    )


def resume_clock(
    state: WorldClockState,
    wall_time: datetime,
    speed_multiplier: ClockSpeedInput | None = None,
    reason: str | None = None,
) -> ClockTransition:
    _require_status(state, WorldClockStatus.PAUSED, "resume")
    normalized_wall_time = _normalize_datetime(wall_time, "wall_time")
    new_state = WorldClockState(
        world_id=state.world_id,
        status=WorldClockStatus.RUNNING,
        current_world_time=state.current_world_time,
        wall_time_anchor=normalized_wall_time,
        speed_multiplier=state.speed_multiplier
        if speed_multiplier is None
        else _coerce_multiplier(speed_multiplier),
        revision=state.revision + 1,
    )
    return _transition(
        WorldClockTransitionType.RESUME,
        state,
        new_state,
        normalized_wall_time,
        state.current_world_time,
        reason,
    )


def advance_clock(
    state: WorldClockState,
    wall_time: datetime,
    reason: str | None = None,
) -> ClockTransition:
    _require_status(state, WorldClockStatus.RUNNING, "advance")
    normalized_wall_time = _normalize_datetime(wall_time, "wall_time")
    effective_world_time = current_world_time_at(state, normalized_wall_time)
    new_state = WorldClockState(
        world_id=state.world_id,
        status=WorldClockStatus.RUNNING,
        current_world_time=effective_world_time,
        wall_time_anchor=normalized_wall_time,
        speed_multiplier=state.speed_multiplier,
        revision=state.revision + 1,
    )
    return _transition(
        WorldClockTransitionType.ADVANCE,
        state,
        new_state,
        normalized_wall_time,
        effective_world_time,
        reason,
    )


def skip_clock(
    state: WorldClockState,
    target_world_time: datetime,
    wall_time: datetime,
    reason: str | None = None,
) -> ClockTransition:
    normalized_wall_time = _normalize_datetime(wall_time, "wall_time")
    normalized_target_world_time = _normalize_datetime(target_world_time, "target_world_time")
    previous_world_time = current_world_time_at(state, normalized_wall_time)
    wall_time_anchor = (
        normalized_wall_time if state.status is WorldClockStatus.RUNNING else None
    )
    new_state = WorldClockState(
        world_id=state.world_id,
        status=state.status,
        current_world_time=normalized_target_world_time,
        wall_time_anchor=wall_time_anchor,
        speed_multiplier=state.speed_multiplier,
        revision=state.revision + 1,
    )
    return _transition(
        WorldClockTransitionType.SKIP,
        state,
        new_state,
        normalized_wall_time,
        previous_world_time,
        reason,
    )


def _transition(
    transition_type: WorldClockTransitionType,
    previous_state: WorldClockState,
    new_state: WorldClockState,
    wall_time: datetime,
    previous_world_time: datetime,
    reason: str | None,
) -> ClockTransition:
    return ClockTransition(
        transition_type=transition_type,
        previous_state=previous_state,
        new_state=new_state,
        wall_time=wall_time,
        previous_world_time=previous_world_time,
        new_world_time=new_state.current_world_time,
        reason=reason,
    )


def _require_status(
    state: WorldClockState,
    expected_status: WorldClockStatus,
    action: str,
) -> None:
    if state.status is not expected_status:
        raise WorldClockStateError(f"cannot {action} a {state.status.value} clock")


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise WorldClockTimeError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _coerce_multiplier(value: ClockSpeedInput) -> Decimal:
    try:
        multiplier = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise WorldClockStateError("speed_multiplier must be a positive finite number") from exc

    if not multiplier.is_finite() or multiplier <= 0:
        raise WorldClockStateError("speed_multiplier must be a positive finite number")

    return multiplier


def _scale_elapsed(elapsed: timedelta, multiplier: Decimal) -> timedelta:
    if elapsed < timedelta(0):
        raise WorldClockTimeError("elapsed wall time must be non-negative")

    elapsed_microseconds = (
        elapsed.days * 86_400_000_000
        + elapsed.seconds * 1_000_000
        + elapsed.microseconds
    )
    scaled_microseconds = (Decimal(elapsed_microseconds) * multiplier).to_integral_value(
        rounding=ROUND_HALF_EVEN,
    )
    return timedelta(microseconds=int(scaled_microseconds))
