from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from noveland.worlds.clock import (
    ClockSpeedInput,
    ClockTransition,
    WorldClockState,
    WorldClockStatus,
    WorldClockTransitionType,
    advance_clock,
    current_world_time_at,
    pause_clock,
    resume_clock,
    skip_clock,
)
from noveland.worlds.models import WorldClockStateModel, WorldClockTransitionModel
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class WorldClockView:
    state: WorldClockState
    effective_world_time: datetime


class WorldClockService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_initialized(
        self,
        world_id: uuid.UUID,
        wall_time: datetime | None = None,
        actor_ref: str | None = None,
        reason: str | None = None,
    ) -> WorldClockState:
        existing_state = self._state_model_for_world(world_id)
        if existing_state is not None:
            return _state_from_model(existing_state)

        initialized_at = _utc(wall_time)
        state = WorldClockState(
            world_id=world_id,
            status=WorldClockStatus.PAUSED,
            current_world_time=initialized_at,
            wall_time_anchor=None,
            speed_multiplier=Decimal("1"),
            revision=0,
        )
        state_model = _state_model_from_state(state)
        self._session.add(state_model)
        self._session.add(
            _transition_model(
                transition_type=WorldClockTransitionType.INITIALIZE,
                world_id=world_id,
                previous_status=None,
                new_status=state.status,
                previous_world_time=None,
                new_world_time=state.current_world_time,
                wall_time=initialized_at,
                previous_revision=None,
                new_revision=state.revision,
                actor_ref=actor_ref,
                reason=reason,
            ),
        )
        self._session.flush()
        return state

    def view(self, world_id: uuid.UUID, wall_time: datetime | None = None) -> WorldClockView:
        state = self.ensure_initialized(world_id, wall_time)
        effective_at = _utc(wall_time)
        return WorldClockView(
            state=state,
            effective_world_time=current_world_time_at(state, effective_at),
        )

    def pause(
        self,
        world_id: uuid.UUID,
        wall_time: datetime | None = None,
        actor_ref: str | None = None,
        reason: str | None = None,
    ) -> WorldClockView:
        transition = pause_clock(
            self.ensure_initialized(world_id, wall_time),
            _utc(wall_time),
            reason,
        )
        return self._persist_transition(transition, actor_ref)

    def resume(
        self,
        world_id: uuid.UUID,
        wall_time: datetime | None = None,
        speed_multiplier: ClockSpeedInput | None = None,
        actor_ref: str | None = None,
        reason: str | None = None,
    ) -> WorldClockView:
        transition = resume_clock(
            self.ensure_initialized(world_id, wall_time),
            _utc(wall_time),
            speed_multiplier,
            reason,
        )
        return self._persist_transition(transition, actor_ref)

    def advance(
        self,
        world_id: uuid.UUID,
        wall_time: datetime | None = None,
        actor_ref: str | None = None,
        reason: str | None = None,
    ) -> WorldClockView:
        transition = advance_clock(
            self.ensure_initialized(world_id, wall_time),
            _utc(wall_time),
            reason,
        )
        return self._persist_transition(transition, actor_ref)

    def skip(
        self,
        world_id: uuid.UUID,
        target_world_time: datetime,
        wall_time: datetime | None = None,
        actor_ref: str | None = None,
        reason: str | None = None,
    ) -> WorldClockView:
        transition = skip_clock(
            self.ensure_initialized(world_id, wall_time),
            target_world_time,
            _utc(wall_time),
            reason,
        )
        return self._persist_transition(transition, actor_ref)

    def _persist_transition(
        self,
        transition: ClockTransition,
        actor_ref: str | None,
    ) -> WorldClockView:
        state_model = self._state_model_for_world(transition.new_state.world_id)
        if state_model is None:
            state_model = _state_model_from_state(transition.new_state)
            self._session.add(state_model)
        else:
            _apply_state_to_model(state_model, transition.new_state)

        self._session.add(
            _transition_model(
                transition_type=transition.transition_type,
                world_id=transition.new_state.world_id,
                previous_status=transition.previous_state.status,
                new_status=transition.new_state.status,
                previous_world_time=transition.previous_world_time,
                new_world_time=transition.new_world_time,
                wall_time=transition.wall_time,
                previous_revision=transition.previous_state.revision,
                new_revision=transition.new_state.revision,
                actor_ref=actor_ref,
                reason=transition.reason,
            ),
        )
        self._session.flush()
        return WorldClockView(
            state=transition.new_state,
            effective_world_time=transition.new_world_time,
        )

    def _state_model_for_world(self, world_id: uuid.UUID) -> WorldClockStateModel | None:
        return self._session.scalars(
            select(WorldClockStateModel).where(WorldClockStateModel.world_id == world_id),
        ).one_or_none()


def _state_from_model(model: WorldClockStateModel) -> WorldClockState:
    return WorldClockState(
        world_id=model.world_id,
        status=WorldClockStatus(model.status),
        current_world_time=_utc(model.current_world_time),
        wall_time_anchor=None if model.wall_time_anchor is None else _utc(model.wall_time_anchor),
        speed_multiplier=model.speed_multiplier,
        revision=model.revision,
    )


def _state_model_from_state(state: WorldClockState) -> WorldClockStateModel:
    return WorldClockStateModel(
        id=uuid.uuid4(),
        world_id=state.world_id,
        status=state.status.value,
        current_world_time=state.current_world_time,
        wall_time_anchor=state.wall_time_anchor,
        speed_multiplier=state.speed_multiplier,
        revision=state.revision,
    )


def _apply_state_to_model(model: WorldClockStateModel, state: WorldClockState) -> None:
    model.status = state.status.value
    model.current_world_time = state.current_world_time
    model.wall_time_anchor = state.wall_time_anchor
    model.speed_multiplier = state.speed_multiplier
    model.revision = state.revision


def _transition_model(
    *,
    transition_type: WorldClockTransitionType,
    world_id: uuid.UUID,
    previous_status: WorldClockStatus | None,
    new_status: WorldClockStatus,
    previous_world_time: datetime | None,
    new_world_time: datetime,
    wall_time: datetime,
    previous_revision: int | None,
    new_revision: int,
    actor_ref: str | None,
    reason: str | None,
) -> WorldClockTransitionModel:
    return WorldClockTransitionModel(
        id=uuid.uuid4(),
        world_id=world_id,
        transition_type=transition_type.value,
        previous_status=previous_status.value if previous_status is not None else None,
        new_status=new_status.value,
        previous_world_time=previous_world_time,
        new_world_time=new_world_time,
        wall_time=wall_time,
        previous_revision=previous_revision,
        new_revision=new_revision,
        actor_ref=actor_ref,
        reason=reason,
    )


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
