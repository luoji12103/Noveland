from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from noveland.calendar.contracts import (
    CalendarEntryCreate,
    CalendarEntryRecord,
    CalendarEntryStatus,
    CalendarEntryUpdate,
    ScheduleRuleCreate,
    ScheduleRuleKind,
    ScheduleRulePreviewMatch,
    ScheduleRulePreviewResult,
    ScheduleRuleRecord,
    ScheduleRuleUpdate,
)
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from sqlalchemy import select
from sqlalchemy.orm import Session


class CalendarService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_entries(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> list[CalendarEntryRecord]:
        entries = self._session.scalars(
            select(AgentCalendarEntry)
            .where(
                AgentCalendarEntry.world_id == world_id,
                AgentCalendarEntry.agent_id == agent_id,
            )
            .order_by(AgentCalendarEntry.starts_at, AgentCalendarEntry.title),
        ).all()
        return [_entry_record(entry) for entry in entries]

    def create_entry(self, entry_create: CalendarEntryCreate) -> CalendarEntryRecord:
        entry = AgentCalendarEntry(
            id=uuid.uuid4(),
            world_id=entry_create.world_id,
            agent_id=entry_create.agent_id,
            title=entry_create.title,
            description=entry_create.description,
            starts_at=entry_create.starts_at,
            ends_at=entry_create.ends_at,
            recurrence_rule=entry_create.recurrence_rule,
            status=CalendarEntryStatus.ACTIVE.value,
            metadata_json=entry_create.metadata,
        )
        self._session.add(entry)
        self._session.flush()
        return _entry_record(entry)

    def update_entry(
        self,
        entry: AgentCalendarEntry,
        entry_update: CalendarEntryUpdate,
    ) -> CalendarEntryRecord:
        if "title" in entry_update.model_fields_set and entry_update.title is not None:
            entry.title = entry_update.title
        if "description" in entry_update.model_fields_set:
            entry.description = entry_update.description
        if "starts_at" in entry_update.model_fields_set and entry_update.starts_at is not None:
            entry.starts_at = entry_update.starts_at
        if "ends_at" in entry_update.model_fields_set:
            entry.ends_at = entry_update.ends_at
        if "recurrence_rule" in entry_update.model_fields_set:
            entry.recurrence_rule = entry_update.recurrence_rule
        if "status" in entry_update.model_fields_set and entry_update.status is not None:
            entry.status = entry_update.status.value
        if "metadata" in entry_update.model_fields_set:
            entry.metadata_json = entry_update.metadata or {}
        if entry.ends_at is not None and entry.ends_at < entry.starts_at:
            raise ValueError("ends_at must be greater than or equal to starts_at")
        self._session.flush()
        return _entry_record(entry)

    def cancel_entry(self, entry: AgentCalendarEntry) -> None:
        entry.status = CalendarEntryStatus.CANCELLED.value
        self._session.flush()

    def list_rules(self, world_id: uuid.UUID) -> list[ScheduleRuleRecord]:
        rules = self._session.scalars(
            select(WorldScheduleRule)
            .where(WorldScheduleRule.world_id == world_id)
            .order_by(WorldScheduleRule.rule_key),
        ).all()
        return [_rule_record(rule) for rule in rules]

    def create_rule(self, rule_create: ScheduleRuleCreate) -> ScheduleRuleRecord:
        rule = WorldScheduleRule(
            id=uuid.uuid4(),
            world_id=rule_create.world_id,
            rule_key=rule_create.rule_key,
            name=rule_create.name,
            kind=rule_create.kind.value,
            config=rule_create.config,
            is_enabled=True,
        )
        self._session.add(rule)
        self._session.flush()
        return _rule_record(rule)

    def update_rule(
        self,
        rule: WorldScheduleRule,
        rule_update: ScheduleRuleUpdate,
    ) -> ScheduleRuleRecord:
        if "name" in rule_update.model_fields_set and rule_update.name is not None:
            rule.name = rule_update.name
        if "kind" in rule_update.model_fields_set and rule_update.kind is not None:
            rule.kind = rule_update.kind.value
        if "config" in rule_update.model_fields_set:
            rule.config = rule_update.config or {}
        if "is_enabled" in rule_update.model_fields_set:
            rule.is_enabled = bool(rule_update.is_enabled)
        self._session.flush()
        return _rule_record(rule)

    def disable_rule(self, rule: WorldScheduleRule) -> None:
        rule.is_enabled = False
        self._session.flush()

    def due_entries(
        self,
        world_id: uuid.UUID,
        world_time: datetime,
        agent_id: uuid.UUID | None = None,
    ) -> list[CalendarEntryRecord]:
        normalized_world_time = _utc(world_time)
        statement = select(AgentCalendarEntry).where(
            AgentCalendarEntry.world_id == world_id,
            AgentCalendarEntry.status == CalendarEntryStatus.ACTIVE.value,
            AgentCalendarEntry.starts_at <= normalized_world_time,
        )
        statement = statement.where(
            (AgentCalendarEntry.ends_at.is_(None))
            | (AgentCalendarEntry.ends_at >= normalized_world_time),
        )
        if agent_id is not None:
            statement = statement.where(AgentCalendarEntry.agent_id == agent_id)
        entries = self._session.scalars(statement.order_by(AgentCalendarEntry.starts_at)).all()
        return [_entry_record(entry) for entry in entries]

    def due_rules(self, world_id: uuid.UUID, world_time: datetime) -> list[ScheduleRuleRecord]:
        normalized_world_time = _utc(world_time)
        rules = self._session.scalars(
            select(WorldScheduleRule).where(
                WorldScheduleRule.world_id == world_id,
                WorldScheduleRule.is_enabled.is_(True),
            ),
        ).all()
        return [_rule_record(rule) for rule in rules if _rule_matches(rule, normalized_world_time)]

    def preview_rule(
        self,
        *,
        kind: ScheduleRuleKind,
        config: dict[str, object],
        start_world_time: datetime,
        horizon_hours: int,
        limit: int,
    ) -> ScheduleRulePreviewResult:
        normalized_start = _utc(start_world_time)
        matches: list[ScheduleRulePreviewMatch] = []
        match_count = 0
        for offset in range(horizon_hours + 1):
            world_time = normalized_start + timedelta(hours=offset)
            if _rule_input_matches(kind, config, world_time):
                match_count += 1
                if len(matches) < limit:
                    matches.append(
                        ScheduleRulePreviewMatch(
                            world_time=world_time,
                            reason=_rule_match_reason(kind, config, world_time),
                        ),
                    )
        return ScheduleRulePreviewResult(
            kind=kind,
            config=config,
            start_world_time=normalized_start,
            horizon_hours=horizon_hours,
            match_count=match_count,
            matches=matches,
        )


def _rule_matches(rule: WorldScheduleRule, world_time: datetime) -> bool:
    kind = ScheduleRuleKind(rule.kind)
    return _rule_input_matches(kind, rule.config, world_time)


def _rule_input_matches(
    kind: ScheduleRuleKind,
    config: dict[str, object],
    world_time: datetime,
) -> bool:
    if kind is ScheduleRuleKind.WEEKDAY:
        return world_time.weekday() < 5
    if kind is ScheduleRuleKind.WEEKEND:
        return world_time.weekday() >= 5
    hours = config.get("hours")
    if isinstance(hours, Sequence) and not isinstance(hours, str | bytes):
        return world_time.hour in {int(hour) for hour in hours}
    return False


def _rule_match_reason(
    kind: ScheduleRuleKind,
    config: dict[str, object],
    world_time: datetime,
) -> str:
    if kind is ScheduleRuleKind.WEEKDAY:
        return "weekday"
    if kind is ScheduleRuleKind.WEEKEND:
        return "weekend"
    hours = config.get("hours")
    if isinstance(hours, Sequence) and not isinstance(hours, str | bytes):
        return f"hour {world_time.hour}"
    return "no match"


def _entry_record(entry: AgentCalendarEntry) -> CalendarEntryRecord:
    return CalendarEntryRecord(
        id=entry.id,
        world_id=entry.world_id,
        agent_id=entry.agent_id,
        title=entry.title,
        description=entry.description,
        starts_at=_utc(entry.starts_at),
        ends_at=None if entry.ends_at is None else _utc(entry.ends_at),
        recurrence_rule=entry.recurrence_rule,
        status=CalendarEntryStatus(entry.status),
        metadata=entry.metadata_json,
    )


def _rule_record(rule: WorldScheduleRule) -> ScheduleRuleRecord:
    return ScheduleRuleRecord(
        id=rule.id,
        world_id=rule.world_id,
        rule_key=rule.rule_key,
        name=rule.name,
        kind=ScheduleRuleKind(rule.kind),
        config=rule.config,
        is_enabled=rule.is_enabled,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
