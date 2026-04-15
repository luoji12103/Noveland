from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from noveland.worlds.clock import (
    WorldClockState,
    WorldClockStateError,
    WorldClockStatus,
    WorldClockTimeError,
    WorldClockTransitionType,
    advance_clock,
    current_world_time_at,
    pause_clock,
    resume_clock,
    skip_clock,
)

WORLD_ID = uuid.uuid4()
WALL_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
WORLD_TIME = datetime(2180, 1, 1, 8, 0, tzinfo=UTC)


def running_state(speed_multiplier: Decimal = Decimal("1")) -> WorldClockState:
    return WorldClockState(
        world_id=WORLD_ID,
        status=WorldClockStatus.RUNNING,
        current_world_time=WORLD_TIME,
        wall_time_anchor=WALL_TIME,
        speed_multiplier=speed_multiplier,
        revision=4,
    )


def paused_state(speed_multiplier: Decimal = Decimal("1")) -> WorldClockState:
    return WorldClockState(
        world_id=WORLD_ID,
        status=WorldClockStatus.PAUSED,
        current_world_time=WORLD_TIME,
        wall_time_anchor=None,
        speed_multiplier=speed_multiplier,
        revision=4,
    )


def test_running_clock_advances_by_wall_elapsed_and_multiplier() -> None:
    state = running_state(Decimal("2.5"))

    assert current_world_time_at(state, WALL_TIME + timedelta(seconds=4)) == (
        WORLD_TIME + timedelta(seconds=10)
    )


def test_paused_clock_does_not_advance_with_wall_time() -> None:
    state = paused_state(Decimal("3"))

    assert current_world_time_at(state, WALL_TIME + timedelta(days=30)) == WORLD_TIME


def test_pause_materializes_effective_world_time_and_clears_anchor() -> None:
    state = running_state(Decimal("2"))

    transition = pause_clock(state, WALL_TIME + timedelta(minutes=5), reason="operator pause")

    assert transition.transition_type is WorldClockTransitionType.PAUSE
    assert transition.reason == "operator pause"
    assert transition.previous_world_time == WORLD_TIME + timedelta(minutes=10)
    assert transition.new_state.status is WorldClockStatus.PAUSED
    assert transition.new_state.current_world_time == WORLD_TIME + timedelta(minutes=10)
    assert transition.new_state.wall_time_anchor is None
    assert transition.new_state.revision == 5


def test_resume_anchors_wall_time_and_can_update_multiplier() -> None:
    state = paused_state(Decimal("1"))
    resume_at = WALL_TIME + timedelta(hours=1)

    transition = resume_clock(
        state,
        resume_at,
        speed_multiplier=Decimal("4"),
        reason="resume faster",
    )

    assert transition.transition_type is WorldClockTransitionType.RESUME
    assert transition.new_state.status is WorldClockStatus.RUNNING
    assert transition.new_state.current_world_time == WORLD_TIME
    assert transition.new_state.wall_time_anchor == resume_at
    assert transition.new_state.speed_multiplier == Decimal("4")
    assert transition.new_state.revision == 5


def test_advance_checkpoints_running_state_deterministically() -> None:
    state = running_state(Decimal("1.5"))
    advance_at = WALL_TIME + timedelta(minutes=2)

    transition = advance_clock(state, advance_at)

    assert transition.transition_type is WorldClockTransitionType.ADVANCE
    assert transition.new_state.status is WorldClockStatus.RUNNING
    assert transition.new_state.current_world_time == WORLD_TIME + timedelta(minutes=3)
    assert transition.new_state.wall_time_anchor == advance_at
    assert transition.new_state.revision == 5


def test_skip_jumps_to_target_world_time_and_records_transition_metadata() -> None:
    state = running_state(Decimal("2"))
    skip_at = WALL_TIME + timedelta(minutes=3)
    target_world_time = datetime(2190, 6, 1, 9, 30, tzinfo=UTC)

    transition = skip_clock(
        state,
        target_world_time,
        skip_at,
        reason="narrative jump",
    )

    assert transition.transition_type is WorldClockTransitionType.SKIP
    assert transition.previous_state == state
    assert transition.previous_world_time == WORLD_TIME + timedelta(minutes=6)
    assert transition.new_world_time == target_world_time
    assert transition.new_state.current_world_time == target_world_time
    assert transition.new_state.wall_time_anchor == skip_at
    assert transition.new_state.revision == 5
    assert transition.reason == "narrative jump"


def test_invalid_multiplier_fails_with_typed_domain_error() -> None:
    with pytest.raises(WorldClockStateError):
        running_state(Decimal("0"))


def test_backwards_wall_time_fails_with_typed_domain_error() -> None:
    with pytest.raises(WorldClockTimeError):
        current_world_time_at(running_state(), WALL_TIME - timedelta(microseconds=1))


def test_naive_datetimes_fail_with_typed_domain_error() -> None:
    with pytest.raises(WorldClockTimeError):
        WorldClockState(
            world_id=WORLD_ID,
            status=WorldClockStatus.RUNNING,
            current_world_time=datetime(2180, 1, 1, 8, 0),
            wall_time_anchor=WALL_TIME,
        )
