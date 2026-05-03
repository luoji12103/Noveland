from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from noveland.calendar.contracts import (
    CalendarEntryCreate,
    CalendarEntryRecord,
    CalendarEntryStatus,
    CalendarEntryUpdate,
    CalendarConflictRecord,
    CalendarConflictReport,
    CalendarConflictSource,
    ScheduleRuleCreate,
    ScheduleRuleKind,
    ScheduleRulePreviewMatch,
    ScheduleRulePreviewResult,
    ScheduleRuleRecord,
    ScheduleRuleUpdate,
)
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.agents.models import Agent
from sqlalchemy import select
from sqlalchemy.orm import Session


class _RuleWindow(TypedDict):
    agent_id: uuid.UUID
    rule_id: uuid.UUID
    rule_key: str
    name: str
    starts_at: datetime
    ends_at: datetime


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

    def detect_conflicts(
        self,
        *,
        world_id: uuid.UUID,
        start_world_time: datetime,
        horizon_hours: int,
        limit: int,
    ) -> CalendarConflictReport:
        normalized_start = _utc(start_world_time)
        end_world_time = normalized_start + timedelta(hours=horizon_hours)
        entries = self._active_entries_in_window(world_id, normalized_start, end_world_time)
        rule_windows = self._rule_windows(world_id, normalized_start, horizon_hours)
        conflicts: list[CalendarConflictRecord] = []

        for index, left in enumerate(entries):
            for right in entries[index + 1 :]:
                if left.agent_id != right.agent_id or not _ranges_overlap(
                    left.starts_at,
                    left.ends_at or left.starts_at + timedelta(hours=1),
                    right.starts_at,
                    right.ends_at or right.starts_at + timedelta(hours=1),
                ):
                    continue
                conflicts.append(
                    CalendarConflictRecord(
                        conflict_type="calendar_entry_overlap",
                        world_id=world_id,
                        agent_id=left.agent_id,
                        starts_at=max(left.starts_at, right.starts_at),
                        ends_at=min(
                            left.ends_at or left.starts_at + timedelta(hours=1),
                            right.ends_at or right.starts_at + timedelta(hours=1),
                        ),
                        reason="calendar entries overlap for the same agent",
                        sources=[
                            _entry_conflict_source(left),
                            _entry_conflict_source(right),
                        ],
                    ),
                )
                if len(conflicts) >= limit:
                    return _conflict_report(world_id, normalized_start, horizon_hours, conflicts)

        for index, left in enumerate(rule_windows):
            for right in rule_windows[index + 1 :]:
                if left["agent_id"] != right["agent_id"] or left["starts_at"] != right["starts_at"]:
                    continue
                conflicts.append(
                    CalendarConflictRecord(
                        conflict_type="schedule_rule_overlap",
                        world_id=world_id,
                        agent_id=left["agent_id"],
                        starts_at=left["starts_at"],
                        ends_at=left["ends_at"],
                        reason="schedule rules match the same hourly window for the same agent",
                        sources=[
                            _rule_conflict_source(left),
                            _rule_conflict_source(right),
                        ],
                    ),
                )
                if len(conflicts) >= limit:
                    return _conflict_report(world_id, normalized_start, horizon_hours, conflicts)

        for entry in entries:
            entry_start = entry.starts_at
            entry_end = entry.ends_at or entry.starts_at + timedelta(hours=1)
            for window in rule_windows:
                if window["agent_id"] != entry.agent_id or not _ranges_overlap(
                    entry_start,
                    entry_end,
                    window["starts_at"],
                    window["ends_at"],
                ):
                    continue
                conflicts.append(
                    CalendarConflictRecord(
                        conflict_type="schedule_rule_calendar_overlap",
                        world_id=world_id,
                        agent_id=entry.agent_id,
                        starts_at=max(entry_start, window["starts_at"]),
                        ends_at=min(entry_end, window["ends_at"]),
                        reason="schedule rule window overlaps an active calendar entry",
                        sources=[
                            _entry_conflict_source(entry),
                            _rule_conflict_source(window),
                        ],
                    ),
                )
                if len(conflicts) >= limit:
                    return _conflict_report(world_id, normalized_start, horizon_hours, conflicts)

        return _conflict_report(world_id, normalized_start, horizon_hours, conflicts)

    def _active_entries_in_window(
        self,
        world_id: uuid.UUID,
        start_world_time: datetime,
        end_world_time: datetime,
    ) -> list[CalendarEntryRecord]:
        entries = self._session.scalars(
            select(AgentCalendarEntry)
            .where(
                AgentCalendarEntry.world_id == world_id,
                AgentCalendarEntry.status == CalendarEntryStatus.ACTIVE.value,
                AgentCalendarEntry.starts_at <= end_world_time,
                (AgentCalendarEntry.ends_at.is_(None))
                | (AgentCalendarEntry.ends_at >= start_world_time),
            )
            .order_by(AgentCalendarEntry.agent_id, AgentCalendarEntry.starts_at),
        ).all()
        return [_entry_record(entry) for entry in entries]

    def _rule_windows(
        self,
        world_id: uuid.UUID,
        start_world_time: datetime,
        horizon_hours: int,
    ) -> list[_RuleWindow]:
        agent_ids = self._session.scalars(
            select(Agent.id)
            .where(Agent.world_id == world_id, Agent.is_enabled.is_(True))
            .order_by(Agent.agent_key),
        ).all()
        rules = self._session.scalars(
            select(WorldScheduleRule)
            .where(
                WorldScheduleRule.world_id == world_id,
                WorldScheduleRule.is_enabled.is_(True),
            )
            .order_by(WorldScheduleRule.rule_key),
        ).all()
        windows: list[_RuleWindow] = []
        for offset in range(horizon_hours + 1):
            world_time = start_world_time + timedelta(hours=offset)
            for rule in rules:
                if not _rule_matches(rule, world_time):
                    continue
                for agent_id in agent_ids:
                    windows.append(
                        {
                            "agent_id": agent_id,
                            "rule_id": rule.id,
                            "rule_key": rule.rule_key,
                            "name": rule.name,
                            "starts_at": world_time,
                            "ends_at": world_time + timedelta(hours=1),
                        },
                    )
        return windows


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


def _ranges_overlap(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    return left_start < right_end and right_start < left_end


def _entry_conflict_source(entry: CalendarEntryRecord) -> CalendarConflictSource:
    return CalendarConflictSource(
        source_kind="calendar_entry",
        source_id=entry.id,
        agent_id=entry.agent_id,
        label=entry.title,
    )


def _rule_conflict_source(window: _RuleWindow) -> CalendarConflictSource:
    return CalendarConflictSource(
        source_kind="schedule_rule",
        source_id=window["rule_id"],
        agent_id=window["agent_id"],
        label=str(window["name"]),
    )


def _conflict_report(
    world_id: uuid.UUID,
    start_world_time: datetime,
    horizon_hours: int,
    conflicts: list[CalendarConflictRecord],
) -> CalendarConflictReport:
    return CalendarConflictReport(
        world_id=world_id,
        start_world_time=start_world_time,
        horizon_hours=horizon_hours,
        conflict_count=len(conflicts),
        conflicts=conflicts,
    )


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
