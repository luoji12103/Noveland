from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.events import WorldEventAppend, WorldEventImportance, WorldEventStore
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.worlds.models import (
    AuthoringImportJob,
    AuthoringTemplate,
    BetaChecklistItem,
    BetaChecklistRun,
    CharacterKnowledgeFact,
    DailyLifeEventCandidate,
    EndingCandidate,
    FactionProgressTrack,
    GMAgenda,
    GMEventProposal,
    GMStyleReview,
    InWorldNotification,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
    NarrativeContinuityReview,
    OffscreenEventQueueItem,
    PlayerChoiceRecord,
    PlayerInterventionRecord,
    PlayerJournalEntry,
    PlotThread,
    RouteAffinity,
    RouteMilestone,
    SecretRecord,
    WorldBible,
    Worldline,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class EndingDryRun:
    ending_id: uuid.UUID
    ending_key: str
    matched: bool
    satisfied: list[str]
    unsatisfied: list[str]
    evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReleaseGateDecision:
    status: str
    allowed: bool
    blockers: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    evidence_refs: list[dict[str, Any]]
    worldline_id: uuid.UUID | None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "evidence_refs": self.evidence_refs,
            "worldline_id": None if self.worldline_id is None else str(self.worldline_id),
        }


class LivingWorldBetaService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def worldline_or_404(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> Worldline:
        return worldline_or_404(self._session, world_id, worldline_id)

    def create_route_milestone(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        milestone_key: str,
        title: str,
        description: str | None,
        stage: int,
        status: str,
        route_affinity_id: uuid.UUID | None,
        plot_thread_id: uuid.UUID | None,
        agent_id: uuid.UUID | None,
        conditions: dict[str, Any],
        evidence_metadata: dict[str, Any],
        metadata: dict[str, Any],
    ) -> RouteMilestone:
        worldline = self.worldline_or_404(world_id, worldline_id)
        self._ensure_unique_key(RouteMilestone, world_id, worldline.id, milestone_key)
        self._ensure_route_refs(
            world_id=world_id,
            worldline_id=worldline.id,
            route_affinity_id=route_affinity_id,
            plot_thread_id=plot_thread_id,
            agent_id=agent_id,
        )
        milestone = RouteMilestone(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            route_affinity_id=route_affinity_id,
            plot_thread_id=plot_thread_id,
            agent_id=agent_id,
            milestone_key=milestone_key,
            title=title,
            description=description,
            stage=max(0, stage),
            status=status,
            conditions=conditions,
            evidence_metadata=evidence_metadata,
            metadata_json=metadata,
        )
        self._session.add(milestone)
        self._session.flush()
        return milestone

    def create_ending_candidate(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        ending_key: str,
        title: str,
        ending_type: str,
        status: str,
        route_affinity_id: uuid.UUID | None,
        plot_thread_id: uuid.UUID | None,
        agent_id: uuid.UUID | None,
        requirements: dict[str, Any],
        outcome_summary: str | None,
        evidence_metadata: dict[str, Any],
        metadata: dict[str, Any],
    ) -> EndingCandidate:
        worldline = self.worldline_or_404(world_id, worldline_id)
        self._ensure_unique_key(EndingCandidate, world_id, worldline.id, ending_key)
        issues = self._validate_ending_requirements(requirements)
        if issues:
            raise ValueError("; ".join(issue["message"] for issue in issues))
        self._ensure_route_refs(
            world_id=world_id,
            worldline_id=worldline.id,
            route_affinity_id=route_affinity_id,
            plot_thread_id=plot_thread_id,
            agent_id=agent_id,
        )
        ending = EndingCandidate(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            route_affinity_id=route_affinity_id,
            plot_thread_id=plot_thread_id,
            agent_id=agent_id,
            ending_key=ending_key,
            title=title,
            ending_type=ending_type,
            status=status,
            requirements=requirements,
            outcome_summary=outcome_summary,
            evidence_metadata=evidence_metadata,
            metadata_json=metadata,
        )
        self._session.add(ending)
        self._session.flush()
        return ending

    def dry_run_ending(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        ending: EndingCandidate,
    ) -> EndingDryRun:
        worldline = self.worldline_or_404(world_id, worldline_id or ending.worldline_id)
        if ending.world_id != world_id or ending.worldline_id != worldline.id:
            raise ValueError("ending candidate not found")
        requirements = ending.requirements
        satisfied: list[str] = []
        unsatisfied: list[str] = []
        evidence: dict[str, Any] = {}

        min_route_affinity = _optional_int(requirements.get("min_route_affinity"))
        if min_route_affinity is not None:
            route = self._route_for_ending(ending)
            value = None if route is None else route.affinity
            evidence["route_affinity"] = value
            _record_threshold("route affinity", value, min_route_affinity, satisfied, unsatisfied)

        min_route_stage = _optional_int(requirements.get("min_route_stage"))
        if min_route_stage is not None:
            route = self._route_for_ending(ending)
            value = None if route is None else route.stage
            evidence["route_stage"] = value
            _record_threshold("route stage", value, min_route_stage, satisfied, unsatisfied)

        required_flags = _string_list(requirements.get("required_flags"))
        if required_flags:
            route = self._route_for_ending(ending)
            flags = set(route.flags if route is not None else [])
            missing = sorted(flag for flag in required_flags if flag not in flags)
            evidence["route_flags"] = sorted(flags)
            if missing:
                unsatisfied.append(f"Missing route flag(s): {', '.join(missing)}.")
            else:
                satisfied.append("Required route flags are present.")

        forbidden_flags = _string_list(requirements.get("forbidden_flags"))
        if forbidden_flags:
            route = self._route_for_ending(ending)
            flags = set(route.flags if route is not None else [])
            present = sorted(flag for flag in forbidden_flags if flag in flags)
            evidence["forbidden_route_flags"] = forbidden_flags
            if present:
                unsatisfied.append(f"Forbidden route flag(s) present: {', '.join(present)}.")
            else:
                satisfied.append("Forbidden route flags are absent.")

        completed_milestones = _optional_int(requirements.get("min_completed_milestones"))
        if completed_milestones is not None:
            count = self._count(
                select(func.count(RouteMilestone.id)).where(
                    RouteMilestone.world_id == world_id,
                    RouteMilestone.worldline_id == worldline.id,
                    RouteMilestone.status == "completed",
                )
            )
            evidence["completed_milestones"] = count
            _record_threshold(
                "completed route milestones", count, completed_milestones, satisfied, unsatisfied
            )

        required_plot_status = requirements.get("plot_thread_status")
        if isinstance(required_plot_status, str) and ending.plot_thread_id is not None:
            thread = self._session.get(PlotThread, ending.plot_thread_id)
            status = None if thread is None else thread.status
            evidence["plot_thread_status"] = status
            if status == required_plot_status:
                satisfied.append(f"Plot thread status is {required_plot_status}.")
            else:
                unsatisfied.append(f"Plot thread status is not {required_plot_status}.")

        min_choices = _optional_int(requirements.get("min_player_choices"))
        if min_choices is not None:
            count = self._count(
                select(func.count(PlayerChoiceRecord.id)).where(
                    PlayerChoiceRecord.world_id == world_id,
                    PlayerChoiceRecord.worldline_id == worldline.id,
                )
            )
            evidence["player_choices"] = count
            _record_threshold("player choices", count, min_choices, satisfied, unsatisfied)

        if not requirements:
            satisfied.append("No explicit ending requirements configured.")
        return EndingDryRun(
            ending_id=ending.id,
            ending_key=ending.ending_key,
            matched=not unsatisfied,
            satisfied=satisfied,
            unsatisfied=unsatisfied,
            evidence=evidence,
        )

    def run_long_eval(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        eval_key: str,
        horizon_days: int,
        metadata: dict[str, Any],
    ) -> LongRunEvalRun:
        worldline = self.worldline_or_404(world_id, worldline_id)
        started_at = datetime.now(UTC)
        metrics = self._eval_metrics(world_id, worldline.id, horizon_days)
        blockers, recommendations = self._eval_recommendations(metrics)
        status = "failed" if blockers else "warning" if recommendations else "completed"
        run = LongRunEvalRun(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            eval_key=eval_key,
            horizon_days=horizon_days,
            status=status,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            metrics=metrics,
            blockers=blockers,
            recommendations=recommendations,
            metadata_json=metadata,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def create_authoring_template(
        self,
        *,
        world_id: uuid.UUID,
        template_key: str,
        template_kind: str,
        name: str,
        description: str | None,
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> AuthoringTemplate:
        if (
            self._session.scalars(
                select(AuthoringTemplate.id).where(
                    AuthoringTemplate.world_id == world_id,
                    AuthoringTemplate.template_key == template_key,
                )
            ).first()
            is not None
        ):
            raise ValueError("authoring template key already exists")
        issues = self._validate_template(template_kind, content)
        template = AuthoringTemplate(
            id=uuid.uuid4(),
            world_id=world_id,
            template_key=template_key,
            template_kind=template_kind,
            name=name,
            description=description,
            content=content,
            validation_issues=issues,
            is_active=True,
            metadata_json=metadata,
        )
        self._session.add(template)
        self._session.flush()
        return template

    def preview_authoring_template(
        self,
        *,
        world_id: uuid.UUID,
        template: AuthoringTemplate,
        target_worldline_id: uuid.UUID | None = None,
        metadata: dict[str, Any],
    ) -> AuthoringImportJob:
        if template.world_id != world_id:
            raise ValueError("authoring template not found")
        target_worldline = self.worldline_or_404(world_id, target_worldline_id)
        issues = self._validate_template(template.template_kind, template.content)
        summary = self._template_preview_summary(template, target_worldline.id)
        job = AuthoringImportJob(
            id=uuid.uuid4(),
            world_id=world_id,
            template_id=template.id,
            status="preview",
            preview_summary=summary,
            applied_refs={},
            validation_issues=issues,
            metadata_json={
                **metadata,
                "target_worldline_id": str(target_worldline.id),
                "audit": {
                    "action": "preview",
                    "schema_version": summary["schema_version"],
                    "template_id": str(template.id),
                    "target_worldline_id": str(target_worldline.id),
                },
            },
        )
        self._session.add(job)
        self._session.flush()
        return job

    def apply_authoring_template(
        self,
        *,
        world_id: uuid.UUID,
        template: AuthoringTemplate,
        target_worldline_id: uuid.UUID | None = None,
        duplicate_policy: str = "upsert",
        metadata: dict[str, Any],
    ) -> AuthoringImportJob:
        if template.world_id != world_id:
            raise ValueError("authoring template not found")
        if duplicate_policy not in {"upsert", "skip", "fail"}:
            raise ValueError("duplicate policy must be upsert, skip, or fail")
        target_worldline = self.worldline_or_404(world_id, target_worldline_id)
        issues = self._validate_template(template.template_kind, template.content)
        applied_refs: dict[str, Any] = {}
        status = (
            "failed"
            if any(issue.get("severity") == "error" for issue in issues)
            else "applied"
        )
        if status == "applied":
            try:
                applied_refs = self._apply_template_content(
                    world_id,
                    target_worldline.id,
                    template,
                    duplicate_policy=duplicate_policy,
                )
            except ValueError as exc:
                status = "failed"
                issues = [
                    *issues,
                    {
                        "code": "apply_failed",
                        "severity": "error",
                        "message": str(exc),
                    },
                ]
                applied_refs = {}
        audit_event_id: str | None = None
        if status == "applied":
            audit_event = WorldEventStore(self._session).append_event(
                WorldEventAppend(
                    world_id=world_id,
                    worldline_id=target_worldline.id,
                    event_name="authoring.template_applied",
                    importance=WorldEventImportance.SYSTEM,
                    payload={
                        "template_id": str(template.id),
                        "template_key": template.template_key,
                        "template_kind": template.template_kind,
                        "applied_refs": applied_refs,
                        "duplicate_policy": duplicate_policy,
                    },
                    wall_time=datetime.now(UTC),
                    actor_ref="system:authoring",
                )
            )
            audit_event_id = str(audit_event.id)
            applied_refs = {
                **applied_refs,
                "audit_event_id": audit_event_id,
                "target_worldline_id": str(target_worldline.id),
            }
        summary = self._template_preview_summary(template, target_worldline.id)
        job = AuthoringImportJob(
            id=uuid.uuid4(),
            world_id=world_id,
            template_id=template.id,
            status=status,
            preview_summary=summary,
            applied_refs=applied_refs,
            validation_issues=issues,
            metadata_json={
                **metadata,
                "target_worldline_id": str(target_worldline.id),
                "duplicate_policy": duplicate_policy,
                "audit": {
                    "action": "apply",
                    "schema_version": summary["schema_version"],
                    "template_id": str(template.id),
                    "target_worldline_id": str(target_worldline.id),
                    "audit_event_id": audit_event_id,
                },
            },
        )
        self._session.add(job)
        self._session.flush()
        return job

    def upsert_release_profile(
        self,
        *,
        world_id: uuid.UUID,
        profile_key: str,
        status: str,
        branch_policy: dict[str, Any],
        backup_policy: dict[str, Any],
        content_review_policy: dict[str, Any],
        player_permission_policy: dict[str, Any],
        worldline_policy: dict[str, Any],
        checklist: dict[str, Any],
        metadata: dict[str, Any],
    ) -> LivingWorldReleaseProfile:
        gate_decision = self.evaluate_release_gate(
            world_id=world_id,
            requested_status=status,
            checklist=checklist,
            metadata=metadata,
        )
        if not gate_decision.allowed:
            blocker_messages = ", ".join(
                (
                    f"{blocker.get('code')}: {blocker.get('message')}"
                    if blocker.get("code") and blocker.get("message")
                    else str(blocker.get("message") or blocker.get("code"))
                )
                for blocker in gate_decision.blockers
            )
            raise ValueError(blocker_messages or "release gate blocked status change")
        profile = self._session.scalars(
            select(LivingWorldReleaseProfile).where(LivingWorldReleaseProfile.world_id == world_id)
        ).one_or_none()
        if profile is None:
            profile = LivingWorldReleaseProfile(id=uuid.uuid4(), world_id=world_id)
            self._session.add(profile)
        profile.profile_key = profile_key
        profile.status = status
        profile.branch_policy = branch_policy
        profile.backup_policy = backup_policy
        profile.content_review_policy = content_review_policy
        profile.player_permission_policy = player_permission_policy
        profile.worldline_policy = worldline_policy
        profile.checklist = {**checklist, "gate_decision": gate_decision.to_metadata()}
        profile.metadata_json = {**metadata, "gate_decision": gate_decision.to_metadata()}
        self._session.flush()
        return profile

    def get_release_profile(self, *, world_id: uuid.UUID) -> LivingWorldReleaseProfile | None:
        return self._session.scalars(
            select(LivingWorldReleaseProfile).where(LivingWorldReleaseProfile.world_id == world_id)
        ).one_or_none()

    def evaluate_release_gate(
        self,
        *,
        world_id: uuid.UUID,
        requested_status: str,
        checklist: dict[str, Any],
        metadata: dict[str, Any],
    ) -> ReleaseGateDecision:
        target_worldline_id = _uuid_or_none(
            checklist.get("worldline_id")
            or metadata.get("worldline_id")
            or _dict(checklist.get("gate_decision")).get("worldline_id")
        )
        worldline = self.worldline_or_404(world_id, target_worldline_id)
        evidence_refs = _list_of_dicts(checklist.get("evidence_refs"))
        latest_checklist = self._latest_checklist_run(
            world_id=world_id,
            worldline_id=worldline.id,
        )
        latest_eval = self._latest_long_eval(
            world_id=world_id,
            worldline_id=worldline.id,
        )
        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        if requested_status == "released":
            blockers.append(
                {
                    "code": "release_launch_gate_missing",
                    "message": "Released status is blocked until a separate launch gate exists.",
                }
            )
        if requested_status == "ready":
            if latest_checklist is None:
                blockers.append(
                    {
                        "code": "missing_beta_checklist",
                        "message": "Run a beta checklist for the target worldline before ready.",
                    }
                )
            elif latest_checklist.status != "passed":
                blockers.append(
                    {
                        "code": "beta_checklist_not_passing",
                        "message": "Latest beta checklist must be passed before ready.",
                        "run_id": str(latest_checklist.id),
                        "status": latest_checklist.status,
                    }
                )
            if latest_eval is None:
                blockers.append(
                    {
                        "code": "missing_long_run_eval",
                        "message": "Run a long-run eval for the target worldline before ready.",
                    }
                )
            elif latest_eval.status != "completed":
                blockers.append(
                    {
                        "code": "long_run_eval_not_completed",
                        "message": "Latest long-run eval must be completed before ready.",
                        "eval_run_id": str(latest_eval.id),
                        "status": latest_eval.status,
                    }
                )
            required_kinds = {
                "snapshot",
                "worldline",
                "publication",
                "continuity_review",
                "beta_checklist",
                "long_run_eval",
            }
            available_kinds = {str(ref.get("kind")) for ref in evidence_refs}
            missing_kinds = sorted(required_kinds - available_kinds)
            if missing_kinds:
                blockers.append(
                    {
                        "code": "missing_required_evidence_refs",
                        "message": (
                            "Ready status requires structured evidence refs for "
                            + ", ".join(missing_kinds)
                            + "."
                        ),
                        "missing_kinds": missing_kinds,
                    }
                )
            unresolved_refs = [
                ref
                for ref in evidence_refs
                if str(ref.get("kind")) in required_kinds
                and not self._evidence_ref_exists(
                    world_id=world_id,
                    worldline_id=worldline.id,
                    ref=ref,
                )
            ]
            if unresolved_refs:
                blockers.append(
                    {
                        "code": "unresolved_required_evidence_refs",
                        "message": (
                            "Ready status requires evidence refs that resolve in this "
                            "worldline."
                        ),
                        "refs": unresolved_refs,
                    }
                )
            if not _dict(checklist.get("warning_decisions")):
                warnings.append(
                    {
                        "code": "warning_decisions_not_recorded",
                        "message": "Record explicit warning decisions before operator release.",
                    }
                )
        return ReleaseGateDecision(
            status=requested_status,
            allowed=not blockers,
            blockers=blockers,
            warnings=warnings,
            evidence_refs=evidence_refs,
            worldline_id=worldline.id,
        )

    def run_beta_checklist(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        run_key: str,
        actor_ref: str,
        metadata: dict[str, Any],
    ) -> BetaChecklistRun:
        worldline = self.worldline_or_404(world_id, worldline_id)
        items = self._beta_items(world_id, worldline.id)
        blocker_count = sum(1 for item in items if item["status"] == "blocked")
        warning_count = sum(1 for item in items if item["status"] == "warning")
        status = "blocked" if blocker_count else "warning" if warning_count else "passed"
        run = BetaChecklistRun(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            run_key=run_key,
            status=status,
            summary=_beta_summary(status, blocker_count, warning_count),
            evidence={
                "refs": _merge_refs(*(item["evidence"].get("refs", []) for item in items)),
                "items": {item["item_key"]: item["evidence"] for item in items},
                "worldline_id": str(worldline.id),
            },
            blocker_count=blocker_count,
            created_by_actor_ref=actor_ref,
            metadata_json=metadata,
        )
        self._session.add(run)
        self._session.flush()
        for item in items:
            self._session.add(
                BetaChecklistItem(
                    id=uuid.uuid4(),
                    run_id=run.id,
                    item_key=item["item_key"],
                    title=item["title"],
                    status=item["status"],
                    evidence=item["evidence"],
                    recommendation=item["recommendation"],
                )
            )
        self._session.flush()
        return run

    def _ensure_unique_key(
        self,
        model: type[RouteMilestone] | type[EndingCandidate],
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        key: str,
    ) -> None:
        if model is RouteMilestone:
            key_column = RouteMilestone.milestone_key
        else:
            key_column = EndingCandidate.ending_key
        if (
            self._session.scalars(
                select(model.id).where(
                    model.world_id == world_id,
                    model.worldline_id == worldline_id,
                    key_column == key,
                )
            ).first()
            is not None
        ):
            raise ValueError("key already exists")

    def _ensure_route_refs(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        route_affinity_id: uuid.UUID | None,
        plot_thread_id: uuid.UUID | None,
        agent_id: uuid.UUID | None,
    ) -> None:
        if route_affinity_id is not None:
            route = self._session.get(RouteAffinity, route_affinity_id)
            if route is None or route.world_id != world_id or route.worldline_id != worldline_id:
                raise ValueError("route affinity not found")
        if plot_thread_id is not None:
            thread = self._session.get(PlotThread, plot_thread_id)
            if thread is None or thread.world_id != world_id or thread.worldline_id != worldline_id:
                raise ValueError("plot thread not found")
        if agent_id is not None:
            agent = self._session.get(Agent, agent_id)
            if agent is None or agent.world_id != world_id:
                raise ValueError("agent not found")

    def _validate_ending_requirements(
        self,
        requirements: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for field in (
            "min_route_affinity",
            "max_route_affinity",
            "min_route_stage",
            "max_route_stage",
            "min_completed_milestones",
            "min_player_choices",
        ):
            if field in requirements:
                value = _optional_int(requirements.get(field))
                if value is None:
                    issues.append(
                        {
                            "code": "invalid_requirement_type",
                            "field": field,
                            "message": f"{field} must be an integer.",
                        }
                    )
                    continue
                if "affinity" in field and not -100 <= value <= 100:
                    issues.append(
                        {
                            "code": "invalid_affinity_range",
                            "field": field,
                            "message": f"{field} must be between -100 and 100.",
                        }
                    )
                if "stage" in field and value < 0:
                    issues.append(
                        {
                            "code": "invalid_stage_range",
                            "field": field,
                            "message": f"{field} must be non-negative.",
                        }
                    )
                if ("milestones" in field or "choices" in field) and value < 0:
                    issues.append(
                        {
                            "code": "invalid_count_range",
                            "field": field,
                            "message": f"{field} must be non-negative.",
                        }
                    )
        min_affinity = _optional_int(requirements.get("min_route_affinity"))
        max_affinity = _optional_int(requirements.get("max_route_affinity"))
        if min_affinity is not None and max_affinity is not None and min_affinity > max_affinity:
            issues.append(
                {
                    "code": "contradictory_affinity_range",
                    "message": "min_route_affinity cannot exceed max_route_affinity.",
                }
            )
        min_stage = _optional_int(requirements.get("min_route_stage"))
        max_stage = _optional_int(requirements.get("max_route_stage"))
        if min_stage is not None and max_stage is not None and min_stage > max_stage:
            issues.append(
                {
                    "code": "contradictory_stage_range",
                    "message": "min_route_stage cannot exceed max_route_stage.",
                }
            )
        required_flags = _strict_string_list(requirements.get("required_flags"))
        forbidden_flags = _strict_string_list(requirements.get("forbidden_flags"))
        if required_flags is None:
            issues.append(
                {
                    "code": "invalid_required_flags",
                    "field": "required_flags",
                    "message": "required_flags must be a list of strings.",
                }
            )
        if forbidden_flags is None:
            issues.append(
                {
                    "code": "invalid_forbidden_flags",
                    "field": "forbidden_flags",
                    "message": "forbidden_flags must be a list of strings.",
                }
            )
        if required_flags is not None and forbidden_flags is not None:
            overlap = sorted(set(required_flags) & set(forbidden_flags))
            if overlap:
                issues.append(
                    {
                        "code": "contradictory_route_flags",
                        "message": "Route flags cannot be both required and forbidden.",
                        "flags": overlap,
                    }
                )
        return issues

    def _route_for_ending(self, ending: EndingCandidate) -> RouteAffinity | None:
        if ending.route_affinity_id is not None:
            route = self._session.get(RouteAffinity, ending.route_affinity_id)
            if route is not None and route.world_id == ending.world_id:
                return route
        if ending.agent_id is None:
            return None
        return self._session.scalars(
            select(RouteAffinity)
            .where(
                RouteAffinity.world_id == ending.world_id,
                RouteAffinity.worldline_id == ending.worldline_id,
                RouteAffinity.agent_id == ending.agent_id,
            )
            .order_by(RouteAffinity.stage.desc(), RouteAffinity.affinity.desc())
        ).first()

    def _eval_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        horizon_days: int,
    ) -> dict[str, Any]:
        event_rows = self._session.scalars(
            select(WorldEventModel).where(
                WorldEventModel.world_id == world_id,
                WorldEventModel.worldline_id == worldline_id,
            )
        ).all()
        events_by_importance: dict[str, int] = {}
        events_by_day: dict[str, int] = {}
        events_by_actor: dict[str, int] = {}
        for event in event_rows:
            events_by_importance[event.importance] = (
                events_by_importance.get(event.importance, 0) + 1
            )
            day_key = event.world_time.date().isoformat() if event.world_time else "wall-time-only"
            events_by_day[day_key] = events_by_day.get(day_key, 0) + 1
            actor_group = event.actor_ref.split(":", 1)[0]
            events_by_actor[actor_group] = events_by_actor.get(actor_group, 0) + 1
        choice_events = sum(
            1 for event in event_rows if event.event_name == "player.choice_recorded"
        )
        resolved_proposals = self._count(
            select(func.count(GMEventProposal.id)).where(
                GMEventProposal.world_id == world_id,
                GMEventProposal.worldline_id == worldline_id,
                GMEventProposal.status == "resolved",
            )
        )
        executed_macro_items = self._count(
            select(func.count(GMEventProposal.id)).where(
                GMEventProposal.world_id == world_id,
                GMEventProposal.worldline_id == worldline_id,
                GMEventProposal.source_context["source"].as_string() == "gm_macro_planner",
            )
        ) + self._count(
            select(func.count(OffscreenEventQueueItem.id)).where(
                OffscreenEventQueueItem.world_id == world_id,
                OffscreenEventQueueItem.worldline_id == worldline_id,
                OffscreenEventQueueItem.payload_json["source"].as_string()
                == "gm_macro_planner",
            )
        )
        committed_gm_events = sum(
            1 for event in event_rows if _is_committed_gm_event(event)
        )
        failed_reviews = self._count(
            select(func.count(NarrativeContinuityReview.id)).where(
                NarrativeContinuityReview.world_id == world_id,
                NarrativeContinuityReview.worldline_id == worldline_id,
                NarrativeContinuityReview.status == "fail",
            )
        )
        warning_reviews = self._count(
            select(func.count(NarrativeContinuityReview.id)).where(
                NarrativeContinuityReview.world_id == world_id,
                NarrativeContinuityReview.worldline_id == worldline_id,
                NarrativeContinuityReview.status == "warning",
            )
        ) + self._count(
            select(func.count(GMStyleReview.id)).where(
                GMStyleReview.world_id == world_id,
                GMStyleReview.worldline_id == worldline_id,
                GMStyleReview.status == "warning",
            )
        )
        traceability_refs = self._traceability_refs(world_id, worldline_id)
        publication_refs = _refs_by_kind(traceability_refs, "publication")
        publication_gate_warnings = sum(
            1
            for publication in self._reader_visible_publications(world_id, worldline_id)
            if _publication_gate_status(publication) == "warning"
        )
        snapshot_refs = self._entity_refs(
            WorldSnapshotModel,
            world_id=world_id,
            worldline_id=worldline_id,
            kind="snapshot",
            label_attr="schema_version",
            limit=3,
        )
        event_refs = [
            _evidence_ref(
                "world_event",
                event.id,
                event.event_name,
                worldline_id=worldline_id,
                api_path=f"/worlds/{world_id}/events",
            )
            for event in event_rows[:5]
        ]
        return {
            "horizon_days": horizon_days,
            "events": len(event_rows),
            "snapshots": len(snapshot_refs),
            "schedule_rules": self._count_world(WorldScheduleRule, world_id),
            "calendar_entries": self._count_world(AgentCalendarEntry, world_id),
            "gm_agendas": self._count_worldline(GMAgenda, world_id, worldline_id),
            "gm_proposals": self._count_worldline(GMEventProposal, world_id, worldline_id),
            "resolved_gm_proposals": resolved_proposals,
            "executed_macro_items": executed_macro_items,
            "committed_gm_events": committed_gm_events,
            "daily_candidates": self._count_worldline(
                DailyLifeEventCandidate,
                world_id,
                worldline_id,
            ),
            "relationships": self._count_worldline(
                AgentRelationshipEdge,
                world_id,
                worldline_id,
            ),
            "faction_tracks": self._count_worldline(FactionProgressTrack, world_id, worldline_id),
            "knowledge_facts": self._count_worldline(
                CharacterKnowledgeFact,
                world_id,
                worldline_id,
            ),
            "secrets": self._count_worldline(SecretRecord, world_id, worldline_id),
            "route_affinities": self._count_worldline(RouteAffinity, world_id, worldline_id),
            "route_milestones": self._count_worldline(RouteMilestone, world_id, worldline_id),
            "ending_candidates": self._count_worldline(EndingCandidate, world_id, worldline_id),
            "player_choices": self._count_worldline(PlayerChoiceRecord, world_id, worldline_id),
            "player_interventions": self._count_worldline(
                PlayerInterventionRecord,
                world_id,
                worldline_id,
            ),
            "journal_entries": self._count_worldline(PlayerJournalEntry, world_id, worldline_id),
            "notifications": self._count_worldline(InWorldNotification, world_id, worldline_id),
            "narrative_artifacts": self._count_narrative_artifacts(world_id, worldline_id),
            "publications": len(publication_refs),
            "diagnostics": self._count_world(RuntimeDiagnosticEvent, world_id),
            "distribution": {
                "events_by_importance": dict(sorted(events_by_importance.items())),
                "events_by_day": dict(sorted(events_by_day.items())),
                "events_by_actor": dict(sorted(events_by_actor.items())),
                "day_coverage": len(events_by_day),
            },
            "traceability": {
                "choice_event_count": choice_events,
                "event_ref_count": len(event_refs),
                "snapshot_ref_count": len(snapshot_refs),
                "refs": [*event_refs, *snapshot_refs, *traceability_refs],
            },
            "review_warnings": {
                "continuity_or_style_warning_count": warning_reviews,
                "continuity_fail_count": failed_reviews,
                "publication_gate_warning_count": publication_gate_warnings,
            },
        }

    def _eval_recommendations(
        self,
        metrics: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        blockers: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []
        if metrics["events"] == 0:
            blockers.append(
                {
                    "code": "no_worldline_events",
                    "message": "Run or import at least one world event before beta validation.",
                }
            )
        if metrics["relationships"] == 0:
            recommendations.append(
                {
                    "code": "relationship_graph_sparse",
                    "message": (
                        "Add relationship edges so route and daily evaluations can detect "
                        "tension."
                    ),
                }
            )
        if metrics["gm_proposals"] == 0 and metrics["daily_candidates"] == 0:
            recommendations.append(
                {
                    "code": "gm_loop_unproven",
                    "message": (
                        "Generate GM proposals or daily candidates to prove autonomous pacing."
                    ),
                }
            )
        if metrics["route_milestones"] == 0 or metrics["ending_candidates"] == 0:
            recommendations.append(
                {
                    "code": "route_endings_incomplete",
                    "message": (
                        "Add route milestones and ending candidates before beta story review."
                    ),
                }
            )
        if metrics["journal_entries"] == 0 or metrics["notifications"] == 0:
            recommendations.append(
                {
                    "code": "player_surface_missing_evidence",
                    "message": (
                        "Create player journal and notification evidence for player-facing beta."
                    ),
                }
            )
        return blockers, recommendations

    def _validate_template(
        self,
        template_kind: str,
        content: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if not content:
            issues.append(
                {"code": "empty_content", "severity": "warning", "message": "Template is empty."}
            )
        if template_kind == "character":
            characters = _template_items(content, "characters")
            if not characters:
                issues.append(
                    {
                        "code": "missing_characters",
                        "severity": "error",
                        "message": "Character templates require at least one character.",
                    }
                )
            for index, character in enumerate(characters):
                if not character.get("agent_key") or not character.get("display_name"):
                    issues.append(
                        {
                            "code": "character_identity_missing",
                            "severity": "error",
                            "message": (
                                f"Character template item {index + 1} lacks agent_key or "
                                "display_name."
                            ),
                        }
                    )
        if template_kind == "route" and not _template_items(content, "routes"):
            issues.append(
                {
                    "code": "missing_routes",
                    "severity": "warning",
                    "message": "Route template has no route entries.",
                }
            )
        return issues

    def _latest_checklist_run(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> BetaChecklistRun | None:
        return self._session.scalars(
            select(BetaChecklistRun)
            .where(
                BetaChecklistRun.world_id == world_id,
                BetaChecklistRun.worldline_id == worldline_id,
            )
            .order_by(BetaChecklistRun.created_at.desc())
            .limit(1)
        ).first()

    def _latest_long_eval(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> LongRunEvalRun | None:
        return self._session.scalars(
            select(LongRunEvalRun)
            .where(
                LongRunEvalRun.world_id == world_id,
                LongRunEvalRun.worldline_id == worldline_id,
            )
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(1)
        ).first()

    def _traceability_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        refs.extend(
            self._entity_refs(
                AgentRelationshipEdge,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="relationship",
                label_attr="relationship_type",
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                FactionProgressTrack,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="faction_track",
                label_attr="track_key",
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                GMEventProposal,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="gm_proposal",
                label_attr="title",
                limit=2,
                status_filter=("resolved",),
            )
        )
        refs.extend(
            self._gm_event_refs(
                world_id=world_id,
                worldline_id=worldline_id,
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                PlayerChoiceRecord,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="player_choice",
                label_attr="choice_key",
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                PlayerInterventionRecord,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="intervention",
                label_attr="intervention_kind",
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                PlayerJournalEntry,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="journal_entry",
                label_attr="title",
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                InWorldNotification,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="notification",
                label_attr="title",
                limit=2,
            )
        )
        refs.extend(
            self._entity_refs(
                NarrativeContinuityReview,
                world_id=world_id,
                worldline_id=worldline_id,
                kind="continuity_review",
                label_attr="status",
                limit=2,
            )
        )
        refs.extend(self._publication_refs(world_id, worldline_id, limit=2))
        return refs

    def _entity_refs(
        self,
        model: type[Any],
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        kind: str,
        label_attr: str,
        limit: int,
        status_filter: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        statement = select(model).where(
            model.world_id == world_id,
            model.worldline_id == worldline_id,
        )
        if status_filter is not None:
            statement = statement.where(model.status.in_(status_filter))
        statement = statement.order_by(model.created_at.desc()).limit(limit)
        rows = self._session.scalars(statement).all()
        return [
            _evidence_ref(
                kind,
                row.id,
                str(getattr(row, label_attr, kind)),
                worldline_id=worldline_id,
                api_path=f"/worlds/{world_id}",
            )
            for row in rows
        ]

    def _gm_event_refs(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = self._session.scalars(
            select(WorldEventModel)
            .where(
                WorldEventModel.world_id == world_id,
                WorldEventModel.worldline_id == worldline_id,
            )
            .order_by(WorldEventModel.created_at.desc())
        ).all()
        committed_rows = [
            row
            for row in rows
            if _is_committed_gm_event(row)
        ][:limit]
        return [
            _evidence_ref(
                "world_event",
                row.id,
                row.event_name,
                worldline_id=worldline_id,
                api_path=f"/worlds/{world_id}/events",
            )
            for row in committed_rows
        ]

    def _publication_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = self._reader_visible_publications(world_id, worldline_id)[:limit]
        return [
            _evidence_ref(
                "publication",
                row.id,
                "published narrative artifact",
                worldline_id=worldline_id,
                api_path=f"/worlds/{world_id}/reader",
            )
            for row in rows
        ]

    def _reader_visible_publications(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> list[NarrativePublication]:
        rows = self._session.scalars(
            select(NarrativePublication)
            .where(
                NarrativePublication.world_id == world_id,
                NarrativePublication.status == "published",
                NarrativePublication.reader_visible.is_(True),
            )
            .order_by(NarrativePublication.created_at.desc())
        ).all()
        return [
            row
            for row in rows
            if self._publication_matches_worldline(row, world_id, worldline_id)
            and self._publication_gate_allows_ready(row)
        ]

    def _count_narrative_artifacts(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> int:
        rows = self._session.scalars(
            select(NarrativeArtifact).where(NarrativeArtifact.world_id == world_id)
        ).all()
        return sum(
            1
            for row in rows
            if self._artifact_matches_worldline(row, world_id, worldline_id)
        )

    def _publication_matches_worldline(
        self,
        publication: NarrativePublication,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> bool:
        artifact = self._session.get(NarrativeArtifact, publication.artifact_id)
        if artifact is None or artifact.world_id != world_id:
            return False
        return self._artifact_matches_worldline(artifact, world_id, worldline_id)

    def _artifact_matches_worldline(
        self,
        artifact: NarrativeArtifact,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> bool:
        raw_worldline_id = (artifact.artifact_metadata or {}).get("worldline_id")
        if raw_worldline_id is None:
            return self.worldline_or_404(world_id, None).id == worldline_id
        artifact_worldline_id = _uuid_or_none(raw_worldline_id)
        return artifact_worldline_id == worldline_id

    def _publication_gate_allows_ready(self, publication: NarrativePublication) -> bool:
        gate = _dict((publication.published_metadata or {}).get("publication_gate"))
        status = str(gate.get("status") or "")
        if status == "pass":
            return True
        if status == "warning":
            return bool(gate.get("override_style_warning"))
        return False

    def _evidence_ref_exists(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        ref: dict[str, Any],
    ) -> bool:
        ref_worldline_id = _uuid_or_none(ref.get("worldline_id"))
        if ref_worldline_id is not None and ref_worldline_id != worldline_id:
            return False
        ref_id = _uuid_or_none(ref.get("id"))
        if ref_id is None:
            return False
        kind = str(ref.get("kind") or "")
        if kind == "worldline":
            return (
                self._session.scalars(
                    select(Worldline.id).where(
                        Worldline.id == ref_id,
                        Worldline.world_id == world_id,
                    )
                ).first()
                is not None
            )
        if kind == "snapshot":
            return (
                self._session.scalars(
                    select(WorldSnapshotModel.id).where(
                        WorldSnapshotModel.id == ref_id,
                        WorldSnapshotModel.world_id == world_id,
                        WorldSnapshotModel.worldline_id == worldline_id,
                    )
                ).first()
                is not None
            )
        if kind == "publication":
            publication = self._session.get(NarrativePublication, ref_id)
            return (
                publication is not None
                and publication.world_id == world_id
                and publication.status == "published"
                and publication.reader_visible
                and self._publication_matches_worldline(publication, world_id, worldline_id)
                and self._publication_gate_allows_ready(publication)
            )
        if kind == "continuity_review":
            return (
                self._session.scalars(
                    select(NarrativeContinuityReview.id).where(
                        NarrativeContinuityReview.id == ref_id,
                        NarrativeContinuityReview.world_id == world_id,
                        NarrativeContinuityReview.worldline_id == worldline_id,
                    )
                ).first()
                is not None
            )
        if kind == "beta_checklist":
            return (
                self._session.scalars(
                    select(BetaChecklistRun.id).where(
                        BetaChecklistRun.id == ref_id,
                        BetaChecklistRun.world_id == world_id,
                        BetaChecklistRun.worldline_id == worldline_id,
                    )
                ).first()
                is not None
            )
        if kind == "long_run_eval":
            return (
                self._session.scalars(
                    select(LongRunEvalRun.id).where(
                        LongRunEvalRun.id == ref_id,
                        LongRunEvalRun.world_id == world_id,
                        LongRunEvalRun.worldline_id == worldline_id,
                    )
                ).first()
                is not None
            )
        return True

    def _template_preview_summary(
        self,
        template: AuthoringTemplate,
        target_worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        content = template.content
        issues = self._validate_template(template.template_kind, content)
        characters = _template_items(content, "characters")
        routes = _template_items(content, "routes")
        events = _template_items(content, "events")
        return {
            "schema_version": str(content.get("schema_version") or "living-world-template/v2"),
            "template_kind": template.template_kind,
            "source_notes": bool(content.get("source_notes") or content.get("world_bible")),
            "character_count": len(characters),
            "event_template_count": len(events),
            "route_template_count": len(routes),
            "validation_issue_count": len(issues),
            "target_worldline_id": str(target_worldline_id),
            "diff": {
                "source_notes": bool(content.get("source_notes") or content.get("source_material")),
                "characters": [str(item.get("agent_key") or "") for item in characters],
                "events": [
                    str(item.get("event_key") or item.get("event_name") or "")
                    for item in events
                ],
                "routes": [str(item.get("route_key") or "") for item in routes],
            },
            "audit": {
                "template_id": str(template.id),
                "template_key": template.template_key,
                "schema_version": str(content.get("schema_version") or "living-world-template/v2"),
            },
        }

    def _apply_template_content(
        self,
        world_id: uuid.UUID,
        target_worldline_id: uuid.UUID,
        template: AuthoringTemplate,
        *,
        duplicate_policy: str,
    ) -> dict[str, Any]:
        applied_refs: dict[str, Any] = {"refs": []}
        content = template.content
        if template.template_kind in {"source_notes", "world_bundle"}:
            bible = self._session.scalars(
                select(WorldBible).where(WorldBible.world_id == world_id)
            ).one_or_none()
            if bible is not None and duplicate_policy == "fail":
                raise ValueError("world bible already exists")
            if bible is not None and duplicate_policy == "skip":
                applied_refs["world_bible_id"] = str(bible.id)
            elif bible is None:
                bible = WorldBible(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    source_material="",
                    canon_timeline=[],
                    setting_rules={},
                    forbidden_changes=[],
                    sequel_boundaries={},
                    continuity_config={},
                    metadata_json={},
                )
                self._session.add(bible)
            if bible is not None and duplicate_policy != "skip":
                bible.source_material = str(
                    content.get("source_notes") or content.get("source_material") or ""
                )
                bible.canon_timeline = _list_of_dicts(content.get("canon_timeline"))
                bible.setting_rules = _dict(content.get("setting_rules"))
                bible.forbidden_changes = _list_of_dicts(content.get("forbidden_changes"))
                bible.sequel_boundaries = _dict(content.get("sequel_boundaries"))
                bible.continuity_config = _dict(content.get("continuity_config"))
                bible.metadata_json = {
                    **(bible.metadata_json or {}),
                    "last_authoring_template_id": str(template.id),
                }
                applied_refs["world_bible_id"] = str(bible.id)
            if bible is not None:
                applied_refs["refs"].append(
                    _evidence_ref(
                        "world_bible",
                        bible.id,
                        "world bible",
                        api_path=f"/worlds/{world_id}/bible",
                    )
                )
        if template.template_kind in {"character", "world_bundle"}:
            agents = self._apply_character_templates(
                world_id,
                content,
                duplicate_policy=duplicate_policy,
            )
            applied_refs["agents"] = [ref["id"] for ref in agents]
            applied_refs["refs"].extend(agents)
        if template.template_kind in {"route", "world_bundle"}:
            routes = self._apply_route_templates(
                world_id,
                target_worldline_id,
                content,
                duplicate_policy=duplicate_policy,
            )
            applied_refs["routes"] = [ref["id"] for ref in routes]
            applied_refs["refs"].extend(routes)
        return applied_refs

    def _apply_character_templates(
        self,
        world_id: uuid.UUID,
        content: dict[str, Any],
        *,
        duplicate_policy: str,
    ) -> list[dict[str, Any]]:
        applied: list[dict[str, Any]] = []
        for character in _template_items(content, "characters"):
            agent_key = _safe_key(character.get("agent_key"))
            display_name = str(character.get("display_name") or agent_key)
            if not agent_key:
                continue
            agent = self._session.scalars(
                select(Agent).where(Agent.world_id == world_id, Agent.agent_key == agent_key)
            ).one_or_none()
            profile = _dict(character.get("character_profile"))
            if agent is None:
                agent = Agent(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    agent_key=agent_key,
                    display_name=display_name,
                    kind=str(character.get("kind") or "role_agent"),
                    narrative_role=character.get("narrative_role") or "original_character",
                    importance=character.get("importance") or "minor",
                    canon_status=character.get("canon_status") or "original_expansion",
                    character_category=character.get("character_category") or "original_character",
                    character_profile=profile,
                    config=_dict(character.get("config")),
                    is_enabled=True,
                )
                self._session.add(agent)
                action = "created"
            else:
                if duplicate_policy == "fail":
                    raise ValueError(f"agent {agent_key} already exists")
                if duplicate_policy == "skip":
                    applied.append(
                        _evidence_ref(
                            "agent",
                            agent.id,
                            agent.display_name,
                            key=agent.agent_key,
                            api_path=f"/worlds/{world_id}/agents/{agent.id}",
                            action="skipped",
                        )
                    )
                    continue
                agent.display_name = display_name
                agent.character_profile = {**agent.character_profile, **profile}
                action = "updated"
            self._session.flush()
            applied.append(
                _evidence_ref(
                    "agent",
                    agent.id,
                    agent.display_name,
                    key=agent.agent_key,
                    api_path=f"/worlds/{world_id}/agents/{agent.id}",
                    action=action,
                )
            )
        self._session.flush()
        return applied

    def _apply_route_templates(
        self,
        world_id: uuid.UUID,
        target_worldline_id: uuid.UUID,
        content: dict[str, Any],
        *,
        duplicate_policy: str,
    ) -> list[dict[str, Any]]:
        applied: list[dict[str, Any]] = []
        for route in _template_items(content, "routes"):
            agent = self._agent_from_route(world_id, route)
            if agent is None:
                continue
            route_key = _safe_key(route.get("route_key")) or f"{agent.agent_key}-route"
            affinity = self._session.scalars(
                select(RouteAffinity).where(
                    RouteAffinity.world_id == world_id,
                    RouteAffinity.worldline_id == target_worldline_id,
                    RouteAffinity.agent_id == agent.id,
                    RouteAffinity.route_key == route_key,
                )
            ).one_or_none()
            if affinity is None:
                affinity = RouteAffinity(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target_worldline_id,
                    agent_id=agent.id,
                    route_key=route_key,
                )
                self._session.add(affinity)
                action = "created"
            else:
                if duplicate_policy == "fail":
                    raise ValueError(f"route {route_key} already exists")
                if duplicate_policy == "skip":
                    applied.append(
                        _evidence_ref(
                            "route_affinity",
                            affinity.id,
                            affinity.route_key,
                            worldline_id=target_worldline_id,
                            key=affinity.route_key,
                            api_path=f"/worlds/{world_id}/route-affinities",
                            action="skipped",
                        )
                    )
                    continue
                action = "updated"
            affinity.status = str(route.get("status") or "available")
            affinity.affinity = _bounded(_optional_int(route.get("affinity")) or 0, -100, 100)
            affinity.stage = max(0, _optional_int(route.get("stage")) or 0)
            affinity.flags = _string_list(route.get("flags"))
            affinity.metadata_json = _dict(route.get("metadata"))
            self._session.flush()
            applied.append(
                _evidence_ref(
                    "route_affinity",
                    affinity.id,
                    affinity.route_key,
                    worldline_id=target_worldline_id,
                    key=affinity.route_key,
                    api_path=f"/worlds/{world_id}/route-affinities",
                    action=action,
                )
            )
        self._session.flush()
        return applied

    def _agent_from_route(self, world_id: uuid.UUID, route: dict[str, Any]) -> Agent | None:
        agent_id = _uuid_or_none(route.get("agent_id"))
        if agent_id is not None:
            agent = self._session.get(Agent, agent_id)
            if agent is not None and agent.world_id == world_id:
                return agent
        agent_key = _safe_key(route.get("agent_key"))
        if not agent_key:
            return None
        return self._session.scalars(
            select(Agent).where(Agent.world_id == world_id, Agent.agent_key == agent_key)
        ).one_or_none()

    def _beta_items(self, world_id: uuid.UUID, worldline_id: uuid.UUID) -> list[dict[str, Any]]:
        metrics = self._eval_metrics(world_id, worldline_id, 7)
        worldline_count = self._count(
            select(func.count(Worldline.id)).where(Worldline.world_id == world_id)
        )
        traceability_refs = _list_of_dicts(_dict(metrics.get("traceability")).get("refs"))
        worldline_refs = [
            _evidence_ref(
                "worldline",
                worldline_id,
                "target worldline",
                worldline_id=worldline_id,
                api_path=f"/worlds/{world_id}/worldlines",
            )
        ]
        event_refs = _refs_by_kind(traceability_refs, "world_event")
        snapshot_refs = _refs_by_kind(traceability_refs, "snapshot")
        relationship_refs = _refs_by_kind(traceability_refs, "relationship")
        faction_refs = _refs_by_kind(traceability_refs, "faction_track")
        gm_refs = _refs_by_kind(traceability_refs, "gm_proposal")
        gm_committed_refs = [
            ref
            for ref in _refs_by_kind(traceability_refs, "gm_proposal", "world_event")
            if ref in gm_refs
            or str(ref.get("label") or "").startswith(("gm.", "living_world.offscreen"))
        ]
        player_refs = _refs_by_kind(traceability_refs, "player_choice", "intervention")
        journal_refs = _refs_by_kind(traceability_refs, "journal_entry", "notification")
        narrative_refs = _refs_by_kind(traceability_refs, "publication")
        checks = [
            _check(
                "seven_day_simulation",
                "7-day simulation",
                metrics["events"] >= 7 or metrics["daily_candidates"] >= 7,
                metrics["events"] > 0,
                {
                    "events": metrics["events"],
                    "daily_candidates": metrics["daily_candidates"],
                    "refs": event_refs,
                },
                "Run a 7-day worldline simulation or generate daily candidates for seven days.",
            ),
            _check(
                "branch_saves",
                "Branch saves",
                worldline_count >= 2 and metrics["snapshots"] > 0,
                worldline_count >= 2 or metrics["snapshots"] > 0,
                {
                    "worldlines": worldline_count,
                    "snapshots": metrics["snapshots"],
                    "refs": [*worldline_refs, *snapshot_refs],
                },
                "Create at least one forked worldline and snapshot evidence.",
            ),
            _check(
                "relationship_changes",
                "Relationship changes",
                metrics["relationships"] > 0,
                False,
                {"relationships": metrics["relationships"], "refs": relationship_refs},
                "Add relationship edges and record relationship-changing events.",
            ),
            _check(
                "faction_progress",
                "Faction progress",
                metrics["faction_tracks"] > 0,
                False,
                {"faction_tracks": metrics["faction_tracks"], "refs": faction_refs},
                "Add organization faction tracks and progress evidence.",
            ),
            _check(
                "gm_event_loop",
                "GM/event loop",
                metrics["resolved_gm_proposals"] > 0
                or metrics["executed_macro_items"] > 0
                or metrics["committed_gm_events"] > 0,
                metrics["gm_agendas"] > 0 or metrics["gm_proposals"] > 0,
                {
                    "gm_agendas": metrics["gm_agendas"],
                    "gm_proposals": metrics["gm_proposals"],
                    "resolved_gm_proposals": metrics["resolved_gm_proposals"],
                    "executed_macro_items": metrics["executed_macro_items"],
                    "committed_gm_events": metrics["committed_gm_events"],
                    "refs": gm_committed_refs,
                },
                "Resolve a GM proposal or execute a traceable GM/offscreen event.",
            ),
            _check(
                "player_interventions",
                "Player interventions",
                metrics["player_choices"] > 0 and metrics["player_interventions"] > 0,
                metrics["player_choices"] > 0 or metrics["player_interventions"] > 0,
                {
                    "player_choices": metrics["player_choices"],
                    "player_interventions": metrics["player_interventions"],
                    "refs": player_refs,
                },
                "Record a player choice and intervention in this worldline.",
            ),
            _check(
                "journal_notifications",
                "Journal and notifications",
                metrics["journal_entries"] > 0 and metrics["notifications"] > 0,
                metrics["journal_entries"] > 0 or metrics["notifications"] > 0,
                {
                    "journal_entries": metrics["journal_entries"],
                    "notifications": metrics["notifications"],
                    "refs": journal_refs,
                },
                "Add player journal and notification evidence.",
            ),
            _check(
                "narrative_output",
                "Narrative output",
                metrics["narrative_artifacts"] > 0 and metrics["publications"] > 0,
                metrics["narrative_artifacts"] > 0,
                {
                    "narrative_artifacts": metrics["narrative_artifacts"],
                    "publications": metrics["publications"],
                    "refs": narrative_refs,
                },
                "Publish at least one narrative artifact for reader validation.",
            ),
        ]
        return checks

    def _count_world(self, model: type[Any], world_id: uuid.UUID) -> int:
        return self._count(select(func.count(model.id)).where(model.world_id == world_id))

    def _count_worldline(
        self,
        model: type[Any],
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> int:
        return self._count(
            select(func.count(model.id)).where(
                model.world_id == world_id,
                model.worldline_id == worldline_id,
            )
        )

    def _count(self, statement: Any) -> int:
        value = self._session.execute(statement).scalar_one()
        return int(value or 0)


def _check(
    item_key: str,
    title: str,
    passed: bool,
    warning: bool,
    evidence: dict[str, Any],
    recommendation: str,
) -> dict[str, Any]:
    status = "passed" if passed else "warning" if warning else "blocked"
    return {
        "item_key": item_key,
        "title": title,
        "status": status,
        "evidence": evidence,
        "recommendation": None if status == "passed" else recommendation,
    }


def _publication_gate_status(publication: NarrativePublication) -> str:
    gate = _dict((publication.published_metadata or {}).get("publication_gate"))
    return str(gate.get("status") or "")


def _is_committed_gm_event(event: WorldEventModel) -> bool:
    return (
        event.actor_ref.startswith("gm:")
        or event.event_name.startswith("gm.")
        or event.event_name.startswith("living_world.offscreen")
        or str((event.payload or {}).get("source"))
        in {"gm_macro_planner", "offscreen_resolution"}
    )


def _beta_summary(status: str, blocker_count: int, warning_count: int) -> str:
    if status == "passed":
        return "Beta checklist passed with required living-world evidence."
    if status == "warning":
        return f"Beta checklist has {warning_count} warning item(s) and no hard blockers."
    return f"Beta checklist is blocked by {blocker_count} item(s)."


def _record_threshold(
    label: str,
    value: int | None,
    threshold: int,
    satisfied: list[str],
    unsatisfied: list[str],
) -> None:
    if value is not None and value >= threshold:
        satisfied.append(f"{label} meets threshold {threshold}.")
    else:
        unsatisfied.append(f"{label} is below threshold {threshold}.")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, float | str | bytes | bytearray):
            return int(value)
    except (TypeError, ValueError):
        return None
    return None


def _uuid_or_none(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _evidence_ref(
    kind: str,
    entity_id: uuid.UUID,
    label: str,
    *,
    worldline_id: uuid.UUID | None = None,
    key: str | None = None,
    api_path: str | None = None,
    action: str | None = None,
) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "kind": kind,
        "id": str(entity_id),
        "label": label,
    }
    if worldline_id is not None:
        ref["worldline_id"] = str(worldline_id)
    if key is not None:
        ref["key"] = key
    if api_path is not None:
        ref["api_path"] = api_path
    if action is not None:
        ref["action"] = action
    return ref


def _merge_refs(*groups: object) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            if not isinstance(item, dict):
                continue
            ref = dict(item)
            identity = (
                str(ref.get("kind") or ""),
                str(ref.get("id") or ref.get("key") or ref.get("label") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(ref)
    return merged


def _refs_by_kind(refs: list[dict[str, Any]], *kinds: str) -> list[dict[str, Any]]:
    allowed = set(kinds)
    return [ref for ref in refs if str(ref.get("kind") or "") in allowed]


def _strict_string_list(value: object) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list):
        return None
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            return None
        strings.append(item)
    return strings


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _template_items(content: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = content.get(key)
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if key == "characters" and all(name in content for name in ("agent_key", "display_name")):
        return [content]
    if key == "routes" and "route_key" in content:
        return [content]
    return []


def _safe_key(value: object) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    return "".join(character for character in text if character.isalnum() or character == "-")


def _bounded(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
