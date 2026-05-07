from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
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
    InWorldNotification,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
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
        metadata: dict[str, Any],
    ) -> AuthoringImportJob:
        if template.world_id != world_id:
            raise ValueError("authoring template not found")
        summary = self._template_preview_summary(template)
        job = AuthoringImportJob(
            id=uuid.uuid4(),
            world_id=world_id,
            template_id=template.id,
            status="preview",
            preview_summary=summary,
            applied_refs={},
            validation_issues=template.validation_issues,
            metadata_json=metadata,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def apply_authoring_template(
        self,
        *,
        world_id: uuid.UUID,
        template: AuthoringTemplate,
        metadata: dict[str, Any],
    ) -> AuthoringImportJob:
        if template.world_id != world_id:
            raise ValueError("authoring template not found")
        issues = self._validate_template(template.template_kind, template.content)
        applied_refs: dict[str, Any] = {}
        status = (
            "failed"
            if any(issue.get("severity") == "error" for issue in issues)
            else "applied"
        )
        if status == "applied":
            applied_refs = self._apply_template_content(world_id, template)
        job = AuthoringImportJob(
            id=uuid.uuid4(),
            world_id=world_id,
            template_id=template.id,
            status=status,
            preview_summary=self._template_preview_summary(template),
            applied_refs=applied_refs,
            validation_issues=issues,
            metadata_json=metadata,
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
        profile.checklist = checklist
        profile.metadata_json = metadata
        self._session.flush()
        return profile

    def get_release_profile(self, *, world_id: uuid.UUID) -> LivingWorldReleaseProfile | None:
        return self._session.scalars(
            select(LivingWorldReleaseProfile).where(LivingWorldReleaseProfile.world_id == world_id)
        ).one_or_none()

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
            evidence={item["item_key"]: item["evidence"] for item in items},
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
        return {
            "horizon_days": horizon_days,
            "events": self._count_worldline(WorldEventModel, world_id, worldline_id),
            "snapshots": self._count_worldline(WorldSnapshotModel, world_id, worldline_id),
            "schedule_rules": self._count_world(WorldScheduleRule, world_id),
            "calendar_entries": self._count_world(AgentCalendarEntry, world_id),
            "gm_agendas": self._count_worldline(GMAgenda, world_id, worldline_id),
            "gm_proposals": self._count_worldline(GMEventProposal, world_id, worldline_id),
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
            "narrative_artifacts": self._count_world(NarrativeArtifact, world_id),
            "publications": self._count_world(NarrativePublication, world_id),
            "diagnostics": self._count_world(RuntimeDiagnosticEvent, world_id),
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

    def _template_preview_summary(self, template: AuthoringTemplate) -> dict[str, Any]:
        content = template.content
        return {
            "template_kind": template.template_kind,
            "source_notes": bool(content.get("source_notes") or content.get("world_bible")),
            "character_count": len(_template_items(content, "characters")),
            "event_template_count": len(_template_items(content, "events")),
            "route_template_count": len(_template_items(content, "routes")),
            "validation_issue_count": len(template.validation_issues),
        }

    def _apply_template_content(
        self,
        world_id: uuid.UUID,
        template: AuthoringTemplate,
    ) -> dict[str, Any]:
        applied_refs: dict[str, Any] = {}
        content = template.content
        if template.template_kind in {"source_notes", "world_bundle"}:
            bible = self._session.scalars(
                select(WorldBible).where(WorldBible.world_id == world_id)
            ).one_or_none()
            if bible is None:
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
        if template.template_kind in {"character", "world_bundle"}:
            applied_refs["agents"] = self._apply_character_templates(world_id, content)
        if template.template_kind in {"route", "world_bundle"}:
            applied_refs["routes"] = self._apply_route_templates(world_id, content)
        return applied_refs

    def _apply_character_templates(
        self,
        world_id: uuid.UUID,
        content: dict[str, Any],
    ) -> list[str]:
        applied: list[str] = []
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
            else:
                agent.display_name = display_name
                agent.character_profile = {**agent.character_profile, **profile}
            applied.append(str(agent.id))
        self._session.flush()
        return applied

    def _apply_route_templates(
        self,
        world_id: uuid.UUID,
        content: dict[str, Any],
    ) -> list[str]:
        worldline = self.worldline_or_404(world_id, None)
        applied: list[str] = []
        for route in _template_items(content, "routes"):
            agent = self._agent_from_route(world_id, route)
            if agent is None:
                continue
            route_key = _safe_key(route.get("route_key")) or f"{agent.agent_key}-route"
            affinity = self._session.scalars(
                select(RouteAffinity).where(
                    RouteAffinity.world_id == world_id,
                    RouteAffinity.worldline_id == worldline.id,
                    RouteAffinity.agent_id == agent.id,
                    RouteAffinity.route_key == route_key,
                )
            ).one_or_none()
            if affinity is None:
                affinity = RouteAffinity(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline.id,
                    agent_id=agent.id,
                    route_key=route_key,
                )
                self._session.add(affinity)
            affinity.status = str(route.get("status") or "available")
            affinity.affinity = _bounded(_optional_int(route.get("affinity")) or 0, -100, 100)
            affinity.stage = max(0, _optional_int(route.get("stage")) or 0)
            affinity.flags = _string_list(route.get("flags"))
            affinity.metadata_json = _dict(route.get("metadata"))
            applied.append(str(affinity.id))
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
        checks = [
            _check(
                "seven_day_simulation",
                "7-day simulation",
                metrics["events"] >= 7 or metrics["daily_candidates"] >= 7,
                metrics["events"] > 0,
                {"events": metrics["events"], "daily_candidates": metrics["daily_candidates"]},
                "Run a 7-day worldline simulation or generate daily candidates for seven days.",
            ),
            _check(
                "branch_saves",
                "Branch saves",
                worldline_count >= 2 and metrics["snapshots"] > 0,
                worldline_count >= 2 or metrics["snapshots"] > 0,
                {"worldlines": worldline_count, "snapshots": metrics["snapshots"]},
                "Create at least one forked worldline and snapshot evidence.",
            ),
            _check(
                "relationship_changes",
                "Relationship changes",
                metrics["relationships"] > 0,
                False,
                {"relationships": metrics["relationships"]},
                "Add relationship edges and record relationship-changing events.",
            ),
            _check(
                "faction_progress",
                "Faction progress",
                metrics["faction_tracks"] > 0,
                False,
                {"faction_tracks": metrics["faction_tracks"]},
                "Add organization faction tracks and progress evidence.",
            ),
            _check(
                "gm_event_loop",
                "GM/event loop",
                metrics["gm_agendas"] > 0 and metrics["gm_proposals"] > 0,
                metrics["gm_agendas"] > 0 or metrics["gm_proposals"] > 0,
                {"gm_agendas": metrics["gm_agendas"], "gm_proposals": metrics["gm_proposals"]},
                "Create at least one GM agenda and proposal.",
            ),
            _check(
                "player_interventions",
                "Player interventions",
                metrics["player_choices"] > 0 and metrics["player_interventions"] > 0,
                metrics["player_choices"] > 0 or metrics["player_interventions"] > 0,
                {
                    "player_choices": metrics["player_choices"],
                    "player_interventions": metrics["player_interventions"],
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
