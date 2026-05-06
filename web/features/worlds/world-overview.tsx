"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  advanceWorldClock,
  bindPlayerActor,
  compareWorldlines,
  createDailyEpisode,
  createFactionTrack,
  createGroupInteraction,
  createGMAgenda,
  createGMProposal,
  createOrganizationConflict,
  createPlotThread,
  createRumor,
  createRumorPropagation,
  createLocationEdge,
  createOffscreenEvent,
  createOrganization,
  createOrganizationMembership,
  createResolutionRule,
  createScene,
  createSceneBeat,
  createStoryHook,
  createEventTriggerCondition,
  createScheduleRule,
  createSnapshot,
  deactivateScene,
  deleteMembership,
  deliverRumorPropagation,
  dryRunEventTriggerCondition,
  dryRunResolutionRule,
  exportWorldComposition,
  forkWorldline,
  generateDailyLifeCandidates,
  generateRelationshipSuggestions,
  importWorldComposition,
  getCalendarConflicts,
  getDailyLifePreview,
  listMemberCandidates,
  listOffscreenEvents,
  listWorldEvents,
  pauseWorldClock,
  previewPlayerChoiceConsequences,
  previewScheduleRule,
  recordPlayerChoice,
  reviewGMProposal,
  resolveOrganizationConflict,
  resolveOffscreenEvents,
  resumeWorldClock,
  skipWorldClock,
  upsertAgentPresence,
  upsertRouteAffinity,
  updateWorld,
  upsertWorldBible,
  upsertMembership,
  validateWorldComposition,
} from "@/lib/worlds/client";
import { subscribeToEventStream } from "@/lib/realtime";
import type { WorldStreamEnvelope } from "@/lib/realtime";
import type { WorldWorkspaceData } from "@/lib/worlds/server";
import type {
  MemberCandidate,
  RuntimeDiagnostic,
  ScheduleRulePreview,
  CalendarConflictReport,
  DailyLifePreview,
  DailyLifeEventCandidate,
  ChoiceConsequencePreview,
  EventResolutionRule,
  GMAgenda,
  GMEventProposal,
  PlayerActor,
  PlayerChoice,
  ResolutionRuleDryRun,
  TriggerConditionDryRun,
  Worldline,
  WorldlineComparison,
  OffscreenEventQueueItem,
  WorldEventAuditEntry,
  WorldClock,
  WorldCompositionValidation,
  WorldRole,
  StoryHook,
  PlotThread,
  RouteAffinity,
  EventTriggerCondition,
  SceneBeatDraft,
  DailyEpisodeDraft,
  GroupInteractionContext,
  RelationshipEventSuggestion,
  OrganizationConflict,
  Rumor,
  RumorPropagation,
} from "@/lib/worlds/types";
import {
  formString,
  jsonObject,
  jsonObjectArray,
  messageForError,
  optionalFormString,
} from "@/features/workspace/form-utils";

type WorldOverviewProps = {
  data: WorldWorkspaceData;
};

export function WorldOverview({ data }: WorldOverviewProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [memberCandidates, setMemberCandidates] = useState<MemberCandidate[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [clock, setClock] = useState(data.clock);
  const [worldDiagnostics, setWorldDiagnostics] = useState(data.worldDiagnostics);
  const [worldEventAudit, setWorldEventAudit] = useState(data.worldEventAudit);
  const [calendarConflicts, setCalendarConflicts] = useState(data.calendarConflicts);
  const [dailyLifePreview, setDailyLifePreview] = useState(data.dailyLifePreview);
  const [dailyLifeCandidates, setDailyLifeCandidates] = useState(data.dailyLifeCandidates);
  const [offscreenEvents, setOffscreenEvents] = useState(data.offscreenEvents);
  const [schedulePreview, setSchedulePreview] = useState<ScheduleRulePreview | null>(null);
  const [ruleDryRun, setRuleDryRun] = useState<ResolutionRuleDryRun | null>(null);
  const [triggerDryRun, setTriggerDryRun] = useState<TriggerConditionDryRun | null>(null);
  const [choicePreview, setChoicePreview] = useState<ChoiceConsequencePreview | null>(null);
  const [worldlineComparison, setWorldlineComparison] = useState<WorldlineComparison | null>(null);
  const [exportedComposition, setExportedComposition] = useState("");
  const [compositionDraft, setCompositionDraft] = useState("");
  const [compositionValidation, setCompositionValidation] =
    useState<WorldCompositionValidation | null>(null);
  const world = data.selectedWorld;

  useEffect(() => {
    setClock(data.clock);
    setWorldDiagnostics(data.worldDiagnostics);
    setWorldEventAudit(data.worldEventAudit);
    setCalendarConflicts(data.calendarConflicts);
    setDailyLifePreview(data.dailyLifePreview);
    setDailyLifeCandidates(data.dailyLifeCandidates);
    setOffscreenEvents(data.offscreenEvents);
  }, [
    data.calendarConflicts,
    data.clock,
    data.dailyLifeCandidates,
    data.dailyLifePreview,
    data.offscreenEvents,
    data.worldDiagnostics,
    data.worldEventAudit,
  ]);

  useEffect(() => {
    if (world === null) {
      return;
    }
    return subscribeToEventStream<WorldStreamEnvelope["payload"]>(
      `/api/worlds/${world.id}/stream`,
      (envelope) => {
        if (envelope.payload.clock !== undefined) {
          setClock(envelope.payload.clock);
        }
        if (envelope.payload.diagnostics.length > 0) {
          setWorldDiagnostics((current) =>
            mergeWorldDiagnostics(current, envelope.payload.diagnostics),
          );
        }
      },
    );
  }, [world]);

  async function runAction(action: () => Promise<unknown>, success: string, refresh = true) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      if (refresh) {
        router.refresh();
      }
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  if (world === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{notice ?? "World not found."}</p>
      </section>
    );
  }
  const selectedWorld = world;

  async function handleUpdateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateWorld(selectedWorld.id, {
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          memory_backend_profile_id: optionalFormString(form, "memory_backend_profile_id"),
          memory_plugin_identifier: formString(form, "memory_plugin_identifier"),
          memory_plugin_config: jsonObject(formString(form, "memory_plugin_config")),
          world_rules_plugin_identifier: formString(form, "world_rules_plugin_identifier"),
          world_rules_plugin_config: jsonObject(formString(form, "world_rules_plugin_config")),
        }),
      "World saved.",
    );
  }

  async function handleCreateScene(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createScene(selectedWorld.id, {
          scene_key: formString(form, "scene_key"),
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          region_key: optionalFormString(form, "region_key"),
          location_tags: commaList(formString(form, "location_tags")),
          opening_rules: jsonObject(formString(form, "opening_rules")),
        });
        formElement.reset();
      },
      "Scene created.",
    );
  }

  async function handleCreateLocationEdge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createLocationEdge(selectedWorld.id, {
          source_scene_id: formString(form, "source_scene_id"),
          target_scene_id: formString(form, "target_scene_id"),
          travel_label: optionalFormString(form, "travel_label"),
          traversal_rules: jsonObject(formString(form, "traversal_rules")),
        });
        formElement.reset();
      },
      "Location edge created.",
    );
  }

  async function handleSetPresence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        upsertAgentPresence(selectedWorld.id, formString(form, "agent_id"), {
          current_scene_id: optionalFormString(form, "current_scene_id"),
          visibility_status: formString(form, "visibility_status") as
            | "visible"
            | "offscreen"
            | "hidden"
            | "unavailable",
          encounter_eligible: form.get("encounter_eligible") === "on",
          scheduled_movement: jsonObject(formString(form, "scheduled_movement")),
        }),
      "Presence saved.",
    );
  }

  async function handleCreateOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createOrganization(selectedWorld.id, {
          organization_key: formString(form, "organization_key"),
          name: formString(form, "name"),
          organization_type: formString(form, "organization_type") as "club",
          public_summary: optionalFormString(form, "public_summary"),
          hidden_summary: optionalFormString(form, "hidden_summary"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Organization created.",
    );
  }

  async function handleCreateOrganizationMembership(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createOrganizationMembership(
          selectedWorld.id,
          formString(form, "organization_id"),
          {
            agent_id: formString(form, "agent_id"),
            role_title: optionalFormString(form, "role_title"),
            visibility: formString(form, "visibility") as "public" | "hidden",
            loyalty: optionalPositiveInteger(form, "loyalty") ?? 50,
            influence: optionalPositiveInteger(form, "influence") ?? 50,
            responsibilities: commaList(formString(form, "responsibilities")),
            metadata: jsonObject(formString(form, "metadata")),
          },
        );
        formElement.reset();
      },
      "Organization membership created.",
    );
  }

  async function handleCreateFactionTrack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createFactionTrack(selectedWorld.id, formString(form, "organization_id"), {
          worldline_id: optionalFormString(form, "worldline_id"),
          track_key: formString(form, "track_key"),
          name: formString(form, "name"),
          track_type: formString(form, "track_type") as "goal",
          progress: optionalPositiveInteger(form, "progress") ?? 0,
          pressure: optionalPositiveInteger(form, "pressure") ?? 0,
          summary: optionalFormString(form, "summary"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Faction track created.",
    );
  }

  async function handleForkWorldline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await forkWorldline(selectedWorld.id, {
          source_worldline_id: optionalFormString(form, "source_worldline_id"),
          worldline_key: formString(form, "worldline_key"),
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          fork_event_sequence: optionalPositiveInteger(form, "fork_event_sequence"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Worldline forked.",
    );
  }

  async function handleCreateGMAgenda(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createGMAgenda(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          title: formString(form, "title"),
          summary: formString(form, "summary"),
          priority: optionalPositiveInteger(form, "priority") ?? 50,
          focus_agents: commaList(formString(form, "focus_agents")),
          focus_organizations: commaList(formString(form, "focus_organizations")),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "GM agenda created.",
    );
  }

  async function handleCreateGMProposal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createGMProposal(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          agenda_id: optionalFormString(form, "agenda_id"),
          title: formString(form, "title"),
          reason: formString(form, "reason"),
          event_name: formString(form, "event_name"),
          proposed_payload: jsonObject(formString(form, "proposed_payload")),
          importance: (optionalFormString(form, "importance") ?? "daily") as "route",
          risk_score: optionalPositiveInteger(form, "risk_score") ?? 0,
          affected_agents: commaList(formString(form, "affected_agents")),
          affected_organizations: commaList(formString(form, "affected_organizations")),
          source_context: jsonObject(formString(form, "source_context")),
        });
        formElement.reset();
      },
      "GM proposal created.",
    );
  }

  async function handleCreateResolutionRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createResolutionRule(selectedWorld.id, {
          rule_key: formString(form, "rule_key"),
          name: formString(form, "name"),
          priority: optionalPositiveInteger(form, "priority") ?? 50,
          conditions: jsonObject(formString(form, "conditions")),
          effects: jsonObject(formString(form, "effects")),
        });
        formElement.reset();
      },
      "Resolution rule created.",
    );
  }

  async function handleDryRunResolutionRule(ruleId: string) {
    await runAction(
      async () => {
        setRuleDryRun(await dryRunResolutionRule(selectedWorld.id, ruleId));
      },
      "Resolution rule dry-run completed.",
      false,
    );
  }

  async function handleBindPlayerActor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await bindPlayerActor(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          user_id: optionalFormString(form, "user_id"),
          display_name: formString(form, "display_name"),
          current_scene_id: optionalFormString(form, "current_scene_id"),
          profile: jsonObject(formString(form, "profile")),
        });
        formElement.reset();
      },
      "Player actor bound.",
    );
  }

  async function handlePlayerChoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    const applyChoice =
      submitter instanceof HTMLButtonElement && submitter.value === "apply";
    const form = new FormData(event.currentTarget);
    const input = {
      worldline_id: optionalFormString(form, "worldline_id"),
      user_id: optionalFormString(form, "user_id"),
      player_actor_id: formString(form, "player_actor_id"),
      choice_key: formString(form, "choice_key"),
      choice_kind: formString(form, "choice_kind") as "intervention",
      prompt: formString(form, "prompt"),
      selected_option: formString(form, "selected_option"),
      context: jsonObject(formString(form, "context")),
      effects: jsonObject(formString(form, "effects")),
      apply: applyChoice,
    };
    await runAction(
      async () => {
        if (applyChoice) {
          await recordPlayerChoice(selectedWorld.id, input);
        } else {
          setChoicePreview(await previewPlayerChoiceConsequences(selectedWorld.id, input));
        }
      },
      applyChoice ? "Player choice recorded." : "Choice consequence preview loaded.",
      applyChoice,
    );
  }

  async function handleResolveProposal(proposalId: string) {
    await runAction(
      () =>
        reviewGMProposal(selectedWorld.id, proposalId, {
          status: "resolved",
          review_note: "Resolved from workspace.",
        }),
      "GM proposal resolved.",
    );
  }

  async function handleCompareWorldlines(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setWorldlineComparison(
          await compareWorldlines(
            selectedWorld.id,
            formString(form, "base_worldline_id"),
            formString(form, "compare_worldline_id"),
          ),
        );
      },
      "Worldlines compared.",
      false,
    );
  }

  async function handleCreateStoryHook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createStoryHook(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          hook_key: formString(form, "hook_key"),
          title: formString(form, "title"),
          hook_type: formString(form, "hook_type") as "promise",
          summary: formString(form, "summary"),
          priority: optionalPositiveInteger(form, "priority") ?? 50,
          owner_agent_id: optionalFormString(form, "owner_agent_id"),
          target_agent_id: optionalFormString(form, "target_agent_id"),
          due_at: optionalFormString(form, "due_at"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Story hook created.",
    );
  }

  async function handleCreatePlotThread(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createPlotThread(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          thread_key: formString(form, "thread_key"),
          title: formString(form, "title"),
          thread_type: formString(form, "thread_type") as "personal",
          summary: formString(form, "summary"),
          stakes: optionalFormString(form, "stakes"),
          next_beats: commaList(formString(form, "next_beats")),
          participant_agent_ids: selectedValues(form, "participant_agent_ids"),
          organization_ids: selectedValues(form, "organization_ids"),
          priority: optionalPositiveInteger(form, "priority") ?? 50,
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Plot thread created.",
    );
  }

  async function handleUpsertRouteAffinity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await upsertRouteAffinity(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          agent_id: formString(form, "agent_id"),
          route_key: formString(form, "route_key"),
          status: formString(form, "status") as "available",
          affinity: signedInteger(form, "affinity") ?? 0,
          stage: optionalPositiveInteger(form, "stage") ?? 0,
          flags: commaList(formString(form, "flags")),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Route affinity saved.",
    );
  }

  async function handleCreateTriggerCondition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createEventTriggerCondition(selectedWorld.id, {
          condition_key: formString(form, "condition_key"),
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          priority: optionalPositiveInteger(form, "priority") ?? 50,
          conditions: jsonObject(formString(form, "conditions")),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Trigger condition created.",
    );
  }

  async function handleDryRunTriggerCondition(conditionId: string) {
    await runAction(
      async () => {
        setTriggerDryRun(await dryRunEventTriggerCondition(selectedWorld.id, conditionId));
      },
      "Trigger condition dry-run completed.",
      false,
    );
  }

  async function handleCreateSceneBeat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createSceneBeat(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          source_kind: formString(form, "source_kind") as "manual",
          source_ref: optionalFormString(form, "source_ref"),
          title: formString(form, "title"),
          participant_agent_ids: selectedValues(form, "participant_agent_ids"),
          scene_id: optionalFormString(form, "scene_id"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Scene beat draft created.",
    );
  }

  async function handleCreateDailyEpisode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createDailyEpisode(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          source_candidate_id: optionalFormString(form, "source_candidate_id"),
          title: optionalFormString(form, "title"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Daily episode draft created.",
    );
  }

  async function handleCreateGroupInteraction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createGroupInteraction(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          context_key: formString(form, "context_key"),
          title: formString(form, "title"),
          interaction_type: formString(form, "interaction_type") as "casual",
          scene_id: optionalFormString(form, "scene_id"),
          organization_id: optionalFormString(form, "organization_id"),
          participant_agent_ids: selectedValues(form, "participant_agent_ids"),
          participant_roles: jsonObject(formString(form, "participant_roles")),
          constraints: jsonObject(formString(form, "constraints")),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Group interaction created.",
    );
  }

  async function handleGenerateRelationshipSuggestions() {
    await runAction(
      () => generateRelationshipSuggestions(selectedWorld.id, { limit: 20 }),
      "Relationship suggestions generated.",
    );
  }

  async function handleCreateOrganizationConflict(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createOrganizationConflict(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          organization_id: formString(form, "organization_id"),
          faction_track_id: optionalFormString(form, "faction_track_id"),
          title: formString(form, "title"),
          summary: formString(form, "summary"),
          pressure_delta: signedInteger(form, "pressure_delta") ?? 0,
          progress_delta: signedInteger(form, "progress_delta") ?? 0,
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Organization conflict created.",
    );
  }

  async function handleResolveOrganizationConflict(conflictId: string) {
    await runAction(
      () => resolveOrganizationConflict(selectedWorld.id, conflictId),
      "Organization conflict resolved.",
    );
  }

  async function handleCreateRumor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createRumor(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          rumor_key: formString(form, "rumor_key"),
          title: formString(form, "title"),
          content: formString(form, "content"),
          source_agent_id: optionalFormString(form, "source_agent_id"),
          source_organization_id: optionalFormString(form, "source_organization_id"),
          visibility: formString(form, "visibility") as "private",
          known_agent_ids: selectedValues(form, "known_agent_ids"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Rumor created.",
    );
  }

  async function handleCreateRumorPropagation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createRumorPropagation(selectedWorld.id, {
          worldline_id: optionalFormString(form, "worldline_id"),
          rumor_id: formString(form, "rumor_id"),
          source_agent_id: optionalFormString(form, "source_agent_id"),
          target_agent_id: optionalFormString(form, "target_agent_id"),
          target_organization_id: optionalFormString(form, "target_organization_id"),
          propagation_reason: formString(form, "propagation_reason"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Rumor propagation created.",
    );
  }

  async function handleDeliverRumorPropagation(propagationId: string) {
    await runAction(
      () => deliverRumorPropagation(selectedWorld.id, propagationId),
      "Rumor delivered.",
    );
  }

  async function handleSaveWorldBible(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        upsertWorldBible(selectedWorld.id, {
          source_material: formString(form, "source_material"),
          canon_timeline: jsonObjectArray(formString(form, "canon_timeline")),
          setting_rules: jsonObject(formString(form, "setting_rules")),
          forbidden_changes: jsonObjectArray(formString(form, "forbidden_changes")),
          sequel_boundaries: jsonObject(formString(form, "sequel_boundaries")),
          continuity_config: jsonObject(formString(form, "continuity_config")),
          metadata: jsonObject(formString(form, "metadata")),
        }),
      "World bible saved.",
    );
  }

  async function handleSearchUsers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setMemberCandidates(await listMemberCandidates(selectedWorld.id, formString(form, "query")));
    }, "User search completed.");
  }

  async function setMembership(userId: string, role: WorldRole) {
    await runAction(
      () => upsertMembership(selectedWorld.id, userId, role),
      "Membership saved.",
    );
  }

  async function handleCreateRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createScheduleRule(selectedWorld.id, {
          rule_key: formString(form, "rule_key"),
          name: formString(form, "name"),
          kind: formString(form, "kind") as "weekday" | "weekend" | "timetable",
          config: jsonObject(formString(form, "config")),
        });
        formElement.reset();
      },
      "Schedule rule created.",
    );
  }

  async function handlePreviewRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setSchedulePreview(
          await previewScheduleRule(selectedWorld.id, {
            kind: formString(form, "kind") as "weekday" | "weekend" | "timetable",
            config: jsonObject(formString(form, "config")),
            start_world_time: optionalFormString(form, "start_world_time"),
            horizon_hours: optionalPositiveInteger(form, "horizon_hours") ?? 48,
            limit: optionalPositiveInteger(form, "limit") ?? 10,
          }),
        );
      },
      "Schedule preview loaded.",
      false,
    );
  }

  async function handleRefreshConflicts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setCalendarConflicts(
          await getCalendarConflicts(selectedWorld.id, {
            start_world_time: optionalFormString(form, "start_world_time"),
            horizon_hours: optionalPositiveInteger(form, "horizon_hours") ?? 168,
            limit: optionalPositiveInteger(form, "limit") ?? 50,
          }),
        );
      },
      "Calendar conflicts loaded.",
      false,
    );
  }

  async function handlePreviewDailyLife(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setDailyLifePreview(
          await getDailyLifePreview(selectedWorld.id, {
            start_world_time: optionalFormString(form, "start_world_time"),
            horizon_hours: optionalPositiveInteger(form, "horizon_hours") ?? 24,
            limit: optionalPositiveInteger(form, "limit") ?? 20,
          }),
        );
      },
      "Daily life preview loaded.",
      false,
    );
  }

  async function handleGenerateDailyLife(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setDailyLifeCandidates(
          await generateDailyLifeCandidates(selectedWorld.id, {
            horizon_hours: optionalPositiveInteger(form, "horizon_hours") ?? 24,
            limit: optionalPositiveInteger(form, "limit") ?? 20,
          }),
        );
      },
      "Daily life candidates generated.",
      false,
    );
  }

  async function handleQueueOffscreen(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createOffscreenEvent(selectedWorld.id, {
          candidate_id: optionalFormString(form, "candidate_id"),
          event_name: optionalFormString(form, "event_name") ?? "living_world.daily_life",
          title: formString(form, "title"),
          payload: jsonObject(formString(form, "payload")),
          due_at: formString(form, "due_at"),
          importance: (optionalFormString(form, "importance") ?? "daily") as "daily",
        });
        setOffscreenEvents(await listOffscreenEvents(selectedWorld.id, { limit: 10 }));
        formElement.reset();
      },
      "Offscreen event queued.",
      false,
    );
  }

  async function handleResolveOffscreen() {
    await runAction(
      async () => {
        await resolveOffscreenEvents(selectedWorld.id, 20);
        setOffscreenEvents(await listOffscreenEvents(selectedWorld.id, { limit: 10 }));
      },
      "Due offscreen events resolved.",
      false,
    );
  }

  async function handleExportComposition() {
    await runAction(async () => {
      const composition = await exportWorldComposition(selectedWorld.id);
      const text = JSON.stringify(composition, null, 2);
      setExportedComposition(text);
      setCompositionDraft(text);
    }, "Composition exported.");
  }

  async function handleImportComposition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        const importedWorld = await importWorldComposition({
          slug: formString(form, "slug"),
          name: formString(form, "name"),
          owner_user_id: formString(form, "owner_user_id"),
          description: optionalFormString(form, "description"),
          rules_config:
            optionalFormString(form, "rules_config") === null
              ? undefined
              : jsonObject(formString(form, "rules_config")),
          composition: JSON.parse(formString(form, "composition")),
        });
        window.location.assign(`/worlds/${importedWorld.id}`);
      },
      "Composition imported.",
      false,
    );
  }

  async function handleValidateComposition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setCompositionValidation(
          await validateWorldComposition({
            slug: formString(form, "slug"),
            name: formString(form, "name"),
            owner_user_id: formString(form, "owner_user_id"),
            description: optionalFormString(form, "description"),
            rules_config:
              optionalFormString(form, "rules_config") === null
                ? undefined
                : jsonObject(formString(form, "rules_config")),
            composition: JSON.parse(formString(form, "composition")),
          }),
        );
      },
      "Composition validation completed.",
      false,
    );
  }

  async function handleEventAuditFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        setWorldEventAudit(
          await listWorldEvents(selectedWorld.id, {
            event_name: optionalFormString(form, "event_name"),
            actor_ref: optionalFormString(form, "actor_ref"),
            importance: optionalFormString(form, "importance") as
              | "system"
              | "daily"
              | "relationship"
              | "organization"
              | "route"
              | "main_plot"
              | null,
            sequence_after: optionalPositiveInteger(form, "sequence_after"),
            sequence_before: optionalPositiveInteger(form, "sequence_before"),
            wall_time_from: optionalFormString(form, "wall_time_from"),
            wall_time_to: optionalFormString(form, "wall_time_to"),
            limit: optionalPositiveInteger(form, "limit") ?? 10,
          }),
        );
      },
      "Event audit loaded.",
      false,
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="dashboard-grid" aria-label="World metrics">
        <div className="metric">
          <p className="metric-label">Scenes</p>
          <p className="metric-value">{data.scenes.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Agents</p>
          <p className="metric-value">{data.agents.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Members</p>
          <p className="metric-value">{data.memberships.length}</p>
        </div>
      </section>

      <section className="management-panel" aria-labelledby="world-title">
        <h2 className="section-title" id="world-title">
          {world.name}
        </h2>
        <p>
          {world.slug} - {world.is_active ? "Active" : "Inactive"}
        </p>
        <p>{world.description ?? "No description."}</p>
        {data.canManageSelectedWorld ? (
          <form className="management-form" onSubmit={handleUpdateWorld}>
            <input className="text-input" name="name" defaultValue={world.name} />
            <input
              className="text-input"
              name="description"
              defaultValue={world.description ?? ""}
              placeholder="Description"
            />
            {data.isPlatformAdmin ? (
              <select
                aria-label="World memory backend profile"
                className="text-input"
                name="memory_backend_profile_id"
                defaultValue={world.memory_backend_profile_id ?? ""}
              >
                <option value="">No explicit memory backend profile</option>
                {data.memoryBackendProfiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name} ({profile.profile_key})
                  </option>
                ))}
              </select>
            ) : null}
            <select
              aria-label="World memory plugin"
              className="text-input"
              name="memory_plugin_identifier"
              defaultValue={world.memory_plugin_identifier}
            >
              {data.memoryPlugins.map((plugin) => (
                <option key={plugin.identifier} value={plugin.identifier}>
                  {plugin.identifier}
                </option>
              ))}
            </select>
            <textarea
              className="text-input"
              name="memory_plugin_config"
              rows={3}
              defaultValue={JSON.stringify(world.memory_plugin_config, null, 2)}
              placeholder="Memory plugin config"
            />
            <select
              aria-label="World rules plugin"
              className="text-input"
              name="world_rules_plugin_identifier"
              defaultValue={world.world_rules_plugin_identifier}
            >
              {data.worldRulesPlugins.map((plugin) => (
                <option key={plugin.identifier} value={plugin.identifier}>
                  {plugin.identifier}
                </option>
              ))}
            </select>
            <textarea
              className="text-input"
              name="world_rules_plugin_config"
              rows={3}
              defaultValue={JSON.stringify(world.world_rules_plugin_config, null, 2)}
              placeholder="World rules plugin config"
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Save world
            </button>
          </form>
        ) : (
          <>
            <p>Read-only world access.</p>
            <p>Memory backend profile: {world.memory_backend_profile_id ?? "none"}</p>
            <p>Memory plugin: {world.memory_plugin_identifier}</p>
            <p>World rules plugin: {world.world_rules_plugin_identifier}</p>
          </>
        )}
      </section>

      <section className="management-panel" aria-labelledby="world-bible-title">
        <h2 className="section-title" id="world-bible-title">
          World bible and continuity
        </h2>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Continuity</p>
            <p className="metric-value">{data.worldBible?.continuity_status ?? "unset"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Timeline notes</p>
            <p className="metric-value">{data.worldBible?.canon_timeline.length ?? 0}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Forbidden changes</p>
            <p className="metric-value">{data.worldBible?.forbidden_changes.length ?? 0}</p>
          </div>
        </div>
        {data.canManageSelectedWorld ? (
          <form className="management-form" onSubmit={handleSaveWorldBible}>
            <textarea
              className="text-input"
              name="source_material"
              rows={5}
              defaultValue={data.worldBible?.source_material ?? ""}
              placeholder="Source work context and post-ending setup"
            />
            <textarea
              className="text-input"
              name="canon_timeline"
              rows={4}
              defaultValue={JSON.stringify(data.worldBible?.canon_timeline ?? [], null, 2)}
              placeholder="[]"
            />
            <textarea
              className="text-input"
              name="setting_rules"
              rows={4}
              defaultValue={JSON.stringify(data.worldBible?.setting_rules ?? {}, null, 2)}
              placeholder="{}"
            />
            <textarea
              className="text-input"
              name="forbidden_changes"
              rows={4}
              defaultValue={JSON.stringify(data.worldBible?.forbidden_changes ?? [], null, 2)}
              placeholder="[]"
            />
            <textarea
              className="text-input"
              name="sequel_boundaries"
              rows={4}
              defaultValue={JSON.stringify(data.worldBible?.sequel_boundaries ?? {}, null, 2)}
              placeholder="{}"
            />
            <textarea
              className="text-input"
              name="continuity_config"
              rows={4}
              defaultValue={JSON.stringify(
                data.worldBible?.continuity_config ?? { status: "post_canon" },
                null,
                2,
              )}
              placeholder='{"status":"post_canon"}'
            />
            <textarea
              className="text-input"
              name="metadata"
              rows={3}
              defaultValue={JSON.stringify(data.worldBible?.metadata ?? {}, null, 2)}
              placeholder="{}"
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Save world bible
            </button>
          </form>
        ) : (
          <div className="resource-list">
            <article className="resource-row">
              <div>
                <h3>Source material</h3>
                <p>{data.worldBible?.source_material || "No world bible recorded."}</p>
              </div>
            </article>
          </div>
        )}
      </section>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="scenes-title">
          <h2 className="section-title" id="scenes-title">
            Scenes
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handleCreateScene}>
              <input className="text-input" name="scene_key" placeholder="scene-key" />
              <input className="text-input" name="name" placeholder="Scene name" />
              <input className="text-input" name="description" placeholder="Description" />
              <input className="text-input" name="region_key" placeholder="Region key" />
              <input className="text-input" name="location_tags" placeholder="school,indoors" />
              <input className="text-input" name="opening_rules" defaultValue="{}" />
              <button className="primary-button" type="submit" disabled={isBusy}>
                Create scene
              </button>
            </form>
          ) : null}
          <div className="resource-list">
            {data.scenes.length === 0 ? (
              <article className="resource-row">
                <div>
                  <h3>None yet</h3>
                  <p>No records are available.</p>
                </div>
              </article>
            ) : (
              data.scenes.map((scene) => {
                const locationTags = scene.location_tags ?? [];
                return (
                  <article className="resource-row" key={scene.id}>
                    <div>
                      <h3>{scene.name}</h3>
                      <p>
                        {scene.scene_key} - {scene.is_active ? "Active" : "Inactive"}
                      </p>
                      <p>
                        Region {scene.region_key ?? "unset"} - tags{" "}
                        {locationTags.length === 0 ? "none" : locationTags.join(", ")}
                      </p>
                    </div>
                    {data.canManageSelectedWorld ? (
                      <div className="button-row">
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() =>
                            runAction(
                              () => deactivateScene(selectedWorld.id, scene.id),
                              "Scene deactivated.",
                            )
                          }
                        >
                          Deactivate scene
                        </button>
                      </div>
                    ) : null}
                  </article>
                );
              })
            )}
          </div>
        </section>

        <section className="management-panel" aria-labelledby="members-title">
          <h2 className="section-title" id="members-title">
            Members
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handleSearchUsers}>
              <input
                className="text-input"
                name="query"
                placeholder="Search email or display name"
              />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Search users
              </button>
            </form>
          ) : null}
          <div className="resource-list">
            {memberCandidates.map((candidate) => (
              <article className="resource-row" key={candidate.id}>
                <div>
                  <h3>{candidate.display_name}</h3>
                  <p>
                    {candidate.email} - {candidate.role ?? "not a member"}
                  </p>
                </div>
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => setMembership(candidate.id, "human_user")}
                  >
                    Set human user
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => setMembership(candidate.id, "world_admin")}
                  >
                    Set world admin
                  </button>
                </div>
              </article>
            ))}
            {data.memberships.map((membership) => (
              <article className="resource-row" key={membership.id}>
                <div>
                  <h3>{membership.user.display_name}</h3>
                  <p>
                    {membership.user.email} - {membership.role}
                  </p>
                </div>
                {data.canManageSelectedWorld ? (
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={isBusy}
                      onClick={() =>
                        runAction(
                          () => deleteMembership(selectedWorld.id, membership.user_id),
                          "Membership removed.",
                        )
                      }
                    >
                      Remove member
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="management-panel" aria-labelledby="living-world-title">
        <h2 className="section-title" id="living-world-title">
          Living world autonomy
        </h2>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Location edges</p>
            <p className="metric-value">{data.locationEdges.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Organizations</p>
            <p className="metric-value">{data.organizations.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Presence states</p>
            <p className="metric-value">{data.agentPresenceStates.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Offscreen queue</p>
            <p className="metric-value">{offscreenEvents.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Worldlines</p>
            <p className="metric-value">{data.worldlines.length}</p>
          </div>
        </div>
        {data.canManageSelectedWorld ? (
          <div className="management-columns">
            <form className="management-form" onSubmit={handleCreateLocationEdge}>
              <h3>Location edge</h3>
              <select className="text-input" name="source_scene_id" defaultValue="">
                <option value="">Source scene</option>
                {data.scenes.map((scene) => (
                  <option key={scene.id} value={scene.id}>
                    {scene.name}
                  </option>
                ))}
              </select>
              <select className="text-input" name="target_scene_id" defaultValue="">
                <option value="">Target scene</option>
                {data.scenes.map((scene) => (
                  <option key={scene.id} value={scene.id}>
                    {scene.name}
                  </option>
                ))}
              </select>
              <input className="text-input" name="travel_label" placeholder="Travel label" />
              <input className="text-input" name="traversal_rules" defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Add edge
              </button>
            </form>
            <form className="management-form" onSubmit={handleSetPresence}>
              <h3>Character presence</h3>
              <select className="text-input" name="agent_id" defaultValue="">
                <option value="">Agent</option>
                {data.agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.display_name}
                  </option>
                ))}
              </select>
              <select className="text-input" name="current_scene_id" defaultValue="">
                <option value="">No current scene</option>
                {data.scenes.map((scene) => (
                  <option key={scene.id} value={scene.id}>
                    {scene.name}
                  </option>
                ))}
              </select>
              <select className="text-input" name="visibility_status" defaultValue="visible">
                <option value="visible">visible</option>
                <option value="offscreen">offscreen</option>
                <option value="hidden">hidden</option>
                <option value="unavailable">unavailable</option>
              </select>
              <label className="checkbox-label">
                <input name="encounter_eligible" type="checkbox" defaultChecked />
                Encounter eligible
              </label>
              <input className="text-input" name="scheduled_movement" defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Save presence
              </button>
            </form>
          </div>
        ) : null}
        <ResourceList
          rows={[
            ...data.locationEdges.map((edge) => ({
              id: edge.id,
              title: `${edge.source_scene_key} to ${edge.target_scene_key}`,
              detail: edge.travel_label ?? "No travel label",
            })),
            ...data.agentPresenceStates.map((presence) => ({
              id: presence.id,
              title: `${presence.agent_display_name} presence`,
              detail: `${presence.visibility_status} at ${
                presence.current_scene_name ?? "unknown"
              }`,
            })),
          ]}
        />
      </section>

      <section className="management-panel" aria-labelledby="organizations-title">
        <h2 className="section-title" id="organizations-title">
          Organizations and faction tracks
        </h2>
        {data.canManageSelectedWorld ? (
          <div className="management-columns">
            <form className="management-form" onSubmit={handleCreateOrganization}>
              <h3>Organization</h3>
              <input className="text-input" name="organization_key" placeholder="organization-key" />
              <input className="text-input" name="name" placeholder="Organization name" />
              <select className="text-input" name="organization_type" defaultValue="club">
                <option value="school">school</option>
                <option value="club">club</option>
                <option value="family">family</option>
                <option value="company">company</option>
                <option value="faction">faction</option>
                <option value="secret_group">secret_group</option>
                <option value="other">other</option>
              </select>
              <input className="text-input" name="public_summary" placeholder="Public summary" />
              <input className="text-input" name="hidden_summary" placeholder="Hidden summary" />
              <input className="text-input" name="metadata" defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Create organization
              </button>
            </form>
            <form className="management-form" onSubmit={handleCreateOrganizationMembership}>
              <h3>Organization assignment</h3>
              <select className="text-input" name="organization_id" defaultValue="">
                <option value="">Organization</option>
                {data.organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.name}
                  </option>
                ))}
              </select>
              <select className="text-input" name="agent_id" defaultValue="">
                <option value="">Agent</option>
                {data.agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.display_name}
                  </option>
                ))}
              </select>
              <input className="text-input" name="role_title" placeholder="Role title" />
              <select className="text-input" name="visibility" defaultValue="public">
                <option value="public">public</option>
                <option value="hidden">hidden</option>
              </select>
              <input className="text-input" name="loyalty" placeholder="Loyalty" />
              <input className="text-input" name="influence" placeholder="Influence" />
              <input className="text-input" name="responsibilities" placeholder="agenda,liaison" />
              <input className="text-input" name="metadata" defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Add membership
              </button>
            </form>
            <form className="management-form" onSubmit={handleCreateFactionTrack}>
              <h3>Faction track</h3>
              <select className="text-input" name="organization_id" defaultValue="">
                <option value="">Organization</option>
                {data.organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.name}
                  </option>
                ))}
              </select>
              <input className="text-input" name="track_key" placeholder="track-key" />
              <input className="text-input" name="name" placeholder="Track name" />
              <select className="text-input" name="track_type" defaultValue="goal">
                <option value="goal">goal</option>
                <option value="conflict">conflict</option>
                <option value="resource">resource</option>
                <option value="reputation">reputation</option>
                <option value="risk">risk</option>
              </select>
              <input className="text-input" name="progress" placeholder="Progress" />
              <input className="text-input" name="pressure" placeholder="Pressure" />
              <input className="text-input" name="summary" placeholder="Summary" />
              <input className="text-input" name="metadata" defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Add track
              </button>
            </form>
          </div>
        ) : null}
        <ResourceList
          rows={[
            ...data.organizations.map((organization) => ({
              id: organization.id,
              title: `${organization.name} (${organization.organization_type})`,
              detail: organization.public_summary ?? organization.organization_key,
            })),
            ...data.organizationMemberships.map((membership) => ({
              id: membership.id,
              title: `${membership.agent_display_name} in ${membership.organization_name}`,
              detail: `${membership.role_title ?? "member"} - loyalty ${
                membership.loyalty
              } / influence ${membership.influence}`,
            })),
            ...data.factionTracks.map((track) => ({
              id: track.id,
              title: `${track.organization_name}: ${track.name}`,
              detail: `${track.track_type} - progress ${track.progress} / pressure ${
                track.pressure
              }`,
            })),
          ]}
        />
      </section>

      <section className="management-panel" aria-labelledby="daily-life-title">
        <h2 className="section-title" id="daily-life-title">
          Daily life and offscreen queue
        </h2>
        {data.canManageSelectedWorld ? (
          <div className="management-columns">
            <form className="management-form" onSubmit={handlePreviewDailyLife}>
              <h3>Preview</h3>
              <input
                className="text-input"
                name="start_world_time"
                placeholder="2030-01-01T08:00:00Z"
              />
              <input className="text-input" name="horizon_hours" placeholder="Horizon hours" />
              <input className="text-input" name="limit" placeholder="Limit" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Preview daily life
              </button>
            </form>
            <form className="management-form" onSubmit={handleGenerateDailyLife}>
              <h3>Generate</h3>
              <input className="text-input" name="horizon_hours" placeholder="Horizon hours" />
              <input className="text-input" name="limit" placeholder="Limit" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Generate candidates
              </button>
            </form>
            <form className="management-form" onSubmit={handleQueueOffscreen}>
              <h3>Queue event</h3>
              <select className="text-input" name="candidate_id" defaultValue="">
                <option value="">Manual queue item</option>
                {dailyLifeCandidates
                  .filter((candidate) => candidate.id !== null)
                  .map((candidate) => (
                    <option key={candidate.id ?? candidate.title} value={candidate.id ?? ""}>
                      {candidate.title}
                    </option>
                  ))}
              </select>
              <input className="text-input" name="event_name" placeholder="living_world.daily_life" />
              <input className="text-input" name="title" placeholder="Queue title" />
              <input className="text-input" name="due_at" placeholder="2030-01-01T08:00:00Z" />
              <select className="text-input" name="importance" defaultValue="daily">
                <option value="daily">daily</option>
                <option value="relationship">relationship</option>
                <option value="organization">organization</option>
                <option value="route">route</option>
                <option value="main_plot">main_plot</option>
              </select>
              <textarea className="text-input" name="payload" rows={3} defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Queue offscreen event
              </button>
            </form>
          </div>
        ) : null}
        <div className="button-row">
          {data.canManageSelectedWorld ? (
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() => void handleResolveOffscreen()}
            >
              Resolve due offscreen events
            </button>
          ) : null}
        </div>
        <DailyLifeView
          preview={dailyLifePreview}
          candidates={dailyLifeCandidates}
          offscreenEvents={offscreenEvents}
        />
      </section>

      <section className="management-panel" aria-labelledby="gm-worldlines-title">
        <h2 className="section-title" id="gm-worldlines-title">
          GM choices and worldlines
        </h2>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Agendas</p>
            <p className="metric-value">{data.gmAgendas.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Proposals</p>
            <p className="metric-value">{data.gmProposals.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Rules</p>
            <p className="metric-value">{data.resolutionRules.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Choices</p>
            <p className="metric-value">{data.playerChoices.length}</p>
          </div>
        </div>
        {data.canManageSelectedWorld ? (
          <>
            <div className="management-columns">
              <form className="management-form" onSubmit={handleForkWorldline}>
                <h3>Worldline fork</h3>
                <select className="text-input" name="source_worldline_id" defaultValue="">
                  <option value="">Primary worldline</option>
                  {data.worldlines.map((worldline) => (
                    <option key={worldline.id} value={worldline.id}>
                      {worldline.name}
                    </option>
                  ))}
                </select>
                <input className="text-input" name="worldline_key" placeholder="branch-key" />
                <input className="text-input" name="name" placeholder="Branch name" />
                <input className="text-input" name="description" placeholder="Description" />
                <input className="text-input" name="fork_event_sequence" placeholder="Fork event sequence" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Fork worldline
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreateGMAgenda}>
                <h3>GM agenda</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <input className="text-input" name="title" placeholder="Agenda title" />
                <textarea className="text-input" name="summary" rows={3} placeholder="Summary" />
                <input className="text-input" name="priority" placeholder="Priority" />
                <input className="text-input" name="focus_agents" placeholder="agent-key,agent-key" />
                <input className="text-input" name="focus_organizations" placeholder="organization-key" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create agenda
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreateGMProposal}>
                <h3>GM proposal</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <select className="text-input" name="agenda_id" defaultValue="">
                  <option value="">No agenda</option>
                  {data.gmAgendas.map((agenda) => (
                    <option key={agenda.id} value={agenda.id}>
                      {agenda.title}
                    </option>
                  ))}
                </select>
                <input className="text-input" name="title" placeholder="Proposal title" />
                <textarea className="text-input" name="reason" rows={3} placeholder="Reason" />
                <input className="text-input" name="event_name" placeholder="gm.route_beat" />
                <select className="text-input" name="importance" defaultValue="route">
                  <option value="daily">daily</option>
                  <option value="relationship">relationship</option>
                  <option value="organization">organization</option>
                  <option value="route">route</option>
                  <option value="main_plot">main_plot</option>
                </select>
                <input className="text-input" name="risk_score" placeholder="Risk score" />
                <input className="text-input" name="affected_agents" placeholder="agent-key" />
                <input className="text-input" name="affected_organizations" placeholder="organization-key" />
                <textarea className="text-input" name="proposed_payload" rows={3} defaultValue="{}" />
                <textarea className="text-input" name="source_context" rows={3} defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create proposal
                </button>
              </form>
            </div>
            <div className="management-columns">
              <form className="management-form" onSubmit={handleCreateResolutionRule}>
                <h3>Resolution rule</h3>
                <input className="text-input" name="rule_key" placeholder="rule-key" />
                <input className="text-input" name="name" placeholder="Rule name" />
                <input className="text-input" name="priority" placeholder="Priority" />
                <textarea
                  className="text-input"
                  name="conditions"
                  rows={3}
                  defaultValue='{"min_relationship_trust":30}'
                />
                <textarea className="text-input" name="effects" rows={3} defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create rule
                </button>
              </form>
              <form className="management-form" onSubmit={handleBindPlayerActor}>
                <h3>Player actor</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <input className="text-input" name="user_id" placeholder="User id, defaults to you" />
                <input className="text-input" name="display_name" placeholder="Player display name" />
                <select className="text-input" name="current_scene_id" defaultValue="">
                  <option value="">No current scene</option>
                  {data.scenes.map((scene) => (
                    <option key={scene.id} value={scene.id}>
                      {scene.name}
                    </option>
                  ))}
                </select>
                <textarea className="text-input" name="profile" rows={3} defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Bind actor
                </button>
              </form>
              <form className="management-form" onSubmit={handlePlayerChoice}>
                <h3>Choice consequence</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <select className="text-input" name="player_actor_id" defaultValue="">
                  <option value="">Player actor</option>
                  {data.playerActors.map((actor) => (
                    <option key={actor.id} value={actor.id}>
                      {actor.display_name} ({actor.actor_ref})
                    </option>
                  ))}
                </select>
                <input className="text-input" name="user_id" placeholder="User id, defaults to you" />
                <input className="text-input" name="choice_key" placeholder="choice-key" />
                <select className="text-input" name="choice_kind" defaultValue="intervention">
                  <option value="dialogue">dialogue</option>
                  <option value="travel">travel</option>
                  <option value="contact">contact</option>
                  <option value="intervention">intervention</option>
                  <option value="route">route</option>
                </select>
                <input className="text-input" name="prompt" placeholder="Prompt" />
                <input className="text-input" name="selected_option" placeholder="Selected option" />
                <textarea className="text-input" name="context" rows={3} defaultValue="{}" />
                <textarea className="text-input" name="effects" rows={4} defaultValue='{"relationship_updates":[],"faction_updates":[],"offscreen_events":[]}' />
                <div className="button-row">
                  <button className="secondary-button" type="submit" value="preview" disabled={isBusy}>
                    Preview consequences
                  </button>
                  <button className="primary-button" type="submit" value="apply" disabled={isBusy}>
                    Record choice
                  </button>
                </div>
              </form>
            </div>
            <form className="inline-form" onSubmit={handleCompareWorldlines}>
              <select className="text-input" name="base_worldline_id" defaultValue="">
                <option value="">Base worldline</option>
                {data.worldlines.map((worldline) => (
                  <option key={worldline.id} value={worldline.id}>
                    {worldline.name}
                  </option>
                ))}
              </select>
              <select className="text-input" name="compare_worldline_id" defaultValue="">
                <option value="">Compare worldline</option>
                {data.worldlines.map((worldline) => (
                  <option key={worldline.id} value={worldline.id}>
                    {worldline.name}
                  </option>
                ))}
              </select>
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Compare worldlines
              </button>
            </form>
          </>
        ) : null}
        {ruleDryRun !== null ? (
          <p className="status-detail">
            Rule {ruleDryRun.rule_key}: {ruleDryRun.matched ? "matched" : "not matched"} -{" "}
            {ruleDryRun.reasons.join(" ")}
          </p>
        ) : null}
        {choicePreview !== null ? (
          <p className="status-detail">
            Choice preview: {choicePreview.diagnostics.join(", ")}
          </p>
        ) : null}
        {worldlineComparison !== null ? (
          <p className="status-detail">
            Comparison: {worldlineComparison.divergent_event_count} events,{" "}
            {worldlineComparison.relationship_delta_count} relationship deltas,{" "}
            {worldlineComparison.faction_delta_count} faction deltas,{" "}
            {worldlineComparison.choice_delta_count} choice deltas.
          </p>
        ) : null}
        <GMWorldlineView
          worldlines={data.worldlines}
          agendas={data.gmAgendas}
          proposals={data.gmProposals}
          rules={data.resolutionRules}
          actors={data.playerActors}
          choices={data.playerChoices}
          isBusy={isBusy}
          canManage={data.canManageSelectedWorld}
          onResolveProposal={handleResolveProposal}
          onDryRunRule={handleDryRunResolutionRule}
        />
      </section>

      <section className="management-panel" aria-labelledby="plot-route-rumor-title">
        <h2 className="section-title" id="plot-route-rumor-title">
          Plot, route, and rumor flow
        </h2>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Hooks</p>
            <p className="metric-value">{data.storyHooks.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Threads</p>
            <p className="metric-value">{data.plotThreads.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Routes</p>
            <p className="metric-value">{data.routeAffinities.length}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Rumors</p>
            <p className="metric-value">{data.rumors.length}</p>
          </div>
        </div>
        {data.canManageSelectedWorld ? (
          <>
            <div className="management-columns">
              <form className="management-form" onSubmit={handleCreateStoryHook}>
                <h3>Story hook</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <input className="text-input" name="hook_key" placeholder="hook-key" />
                <input className="text-input" name="title" placeholder="Hook title" />
                <select className="text-input" name="hook_type" defaultValue="promise">
                  <option value="promise">promise</option>
                  <option value="foreshadowing">foreshadowing</option>
                  <option value="mystery">mystery</option>
                  <option value="agreement">agreement</option>
                  <option value="flag">flag</option>
                </select>
                <textarea className="text-input" name="summary" rows={3} placeholder="Summary" />
                <AgentSelect agents={data.agents} name="owner_agent_id" label="Owner agent" />
                <AgentSelect agents={data.agents} name="target_agent_id" label="Target agent" />
                <input className="text-input" name="priority" placeholder="Priority" />
                <input className="text-input" name="due_at" placeholder="2030-01-01T08:00:00Z" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create hook
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreatePlotThread}>
                <h3>Plot thread</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <input className="text-input" name="thread_key" placeholder="thread-key" />
                <input className="text-input" name="title" placeholder="Thread title" />
                <select className="text-input" name="thread_type" defaultValue="personal">
                  <option value="personal">personal</option>
                  <option value="organization">organization</option>
                  <option value="daily">daily</option>
                  <option value="main">main</option>
                  <option value="hidden">hidden</option>
                </select>
                <textarea className="text-input" name="summary" rows={3} placeholder="Summary" />
                <input className="text-input" name="stakes" placeholder="Stakes" />
                <input className="text-input" name="next_beats" placeholder="beat,beat" />
                <MultiAgentSelect agents={data.agents} name="participant_agent_ids" />
                <MultiOrganizationSelect
                  organizations={data.organizations}
                  name="organization_ids"
                />
                <input className="text-input" name="priority" placeholder="Priority" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create thread
                </button>
              </form>
              <form className="management-form" onSubmit={handleUpsertRouteAffinity}>
                <h3>Route affinity</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <AgentSelect agents={data.agents} name="agent_id" label="Route agent" />
                <input className="text-input" name="route_key" placeholder="route-key" />
                <select className="text-input" name="status" defaultValue="available">
                  <option value="locked">locked</option>
                  <option value="available">available</option>
                  <option value="active">active</option>
                  <option value="completed">completed</option>
                  <option value="blocked">blocked</option>
                </select>
                <input className="text-input" name="affinity" placeholder="Affinity" />
                <input className="text-input" name="stage" placeholder="Stage" />
                <input className="text-input" name="flags" placeholder="flag,flag" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Save route
                </button>
              </form>
            </div>
            <div className="management-columns">
              <form className="management-form" onSubmit={handleCreateTriggerCondition}>
                <h3>Event trigger</h3>
                <input className="text-input" name="condition_key" placeholder="condition-key" />
                <input className="text-input" name="name" placeholder="Condition name" />
                <input className="text-input" name="description" placeholder="Description" />
                <input className="text-input" name="priority" placeholder="Priority" />
                <textarea
                  className="text-input"
                  name="conditions"
                  rows={4}
                  defaultValue='{"min_open_hooks":1}'
                />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create trigger
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreateSceneBeat}>
                <h3>Scene beat draft</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <select className="text-input" name="source_kind" defaultValue="manual">
                  <option value="manual">manual</option>
                  <option value="event">event</option>
                  <option value="proposal">proposal</option>
                  <option value="daily_episode">daily_episode</option>
                </select>
                <input className="text-input" name="source_ref" placeholder="Source ref" />
                <input className="text-input" name="title" placeholder="Beat title" />
                <MultiAgentSelect agents={data.agents} name="participant_agent_ids" />
                <SceneSelect scenes={data.scenes} name="scene_id" label="Scene" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Compose beat
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreateDailyEpisode}>
                <h3>Daily episode draft</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <select className="text-input" name="source_candidate_id" defaultValue="">
                  <option value="">No source candidate</option>
                  {data.dailyLifeCandidates
                    .filter((candidate) => candidate.id !== null)
                    .map((candidate) => (
                      <option key={candidate.id ?? candidate.title} value={candidate.id ?? ""}>
                        {candidate.title}
                      </option>
                    ))}
                </select>
                <input className="text-input" name="title" placeholder="Episode title" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create episode
                </button>
              </form>
            </div>
            <div className="management-columns">
              <form className="management-form" onSubmit={handleCreateGroupInteraction}>
                <h3>Group interaction</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <input className="text-input" name="context_key" placeholder="context-key" />
                <input className="text-input" name="title" placeholder="Interaction title" />
                <select className="text-input" name="interaction_type" defaultValue="casual">
                  <option value="club">club</option>
                  <option value="class">class</option>
                  <option value="organization_meeting">organization_meeting</option>
                  <option value="conflict">conflict</option>
                  <option value="casual">casual</option>
                </select>
                <SceneSelect scenes={data.scenes} name="scene_id" label="Location" />
                <OrganizationSelect
                  organizations={data.organizations}
                  name="organization_id"
                  label="Organization"
                />
                <MultiAgentSelect agents={data.agents} name="participant_agent_ids" />
                <textarea className="text-input" name="participant_roles" rows={3} defaultValue="{}" />
                <textarea className="text-input" name="constraints" rows={3} defaultValue="{}" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create group context
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreateOrganizationConflict}>
                <h3>Organization conflict</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <OrganizationSelect
                  organizations={data.organizations}
                  name="organization_id"
                  label="Organization"
                />
                <select className="text-input" name="faction_track_id" defaultValue="">
                  <option value="">No faction track</option>
                  {data.factionTracks.map((track) => (
                    <option key={track.id} value={track.id}>
                      {track.organization_name}: {track.name}
                    </option>
                  ))}
                </select>
                <input className="text-input" name="title" placeholder="Conflict title" />
                <textarea className="text-input" name="summary" rows={3} placeholder="Summary" />
                <input className="text-input" name="pressure_delta" placeholder="Pressure delta" />
                <input className="text-input" name="progress_delta" placeholder="Progress delta" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create conflict
                </button>
              </form>
              <form className="management-form" onSubmit={handleCreateRumor}>
                <h3>Rumor</h3>
                <WorldlineSelect worldlines={data.worldlines} />
                <input className="text-input" name="rumor_key" placeholder="rumor-key" />
                <input className="text-input" name="title" placeholder="Rumor title" />
                <textarea className="text-input" name="content" rows={3} placeholder="Content" />
                <AgentSelect agents={data.agents} name="source_agent_id" label="Source agent" />
                <OrganizationSelect
                  organizations={data.organizations}
                  name="source_organization_id"
                  label="Source organization"
                />
                <select className="text-input" name="visibility" defaultValue="private">
                  <option value="private">private</option>
                  <option value="group">group</option>
                  <option value="public">public</option>
                </select>
                <MultiAgentSelect agents={data.agents} name="known_agent_ids" />
                <input className="text-input" name="metadata" defaultValue="{}" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Create rumor
                </button>
              </form>
            </div>
            <form className="inline-form" onSubmit={handleCreateRumorPropagation}>
              <select className="text-input" name="rumor_id" defaultValue="">
                <option value="">Rumor</option>
                {data.rumors.map((rumor) => (
                  <option key={rumor.id} value={rumor.id}>
                    {rumor.title}
                  </option>
                ))}
              </select>
              <AgentSelect agents={data.agents} name="source_agent_id" label="Source agent" />
              <AgentSelect agents={data.agents} name="target_agent_id" label="Target agent" />
              <OrganizationSelect
                organizations={data.organizations}
                name="target_organization_id"
                label="Target organization"
              />
              <input className="text-input" name="propagation_reason" placeholder="Propagation reason" />
              <input className="text-input" name="metadata" defaultValue="{}" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Queue rumor delivery
              </button>
            </form>
            <div className="button-row">
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => void handleGenerateRelationshipSuggestions()}
              >
                Generate relationship suggestions
              </button>
            </div>
          </>
        ) : null}
        {triggerDryRun !== null ? (
          <p className="status-detail">
            Trigger {triggerDryRun.condition_key}:{" "}
            {triggerDryRun.matched ? "matched" : "not matched"} -{" "}
            {[...triggerDryRun.satisfied, ...triggerDryRun.unsatisfied].join(" ")}
          </p>
        ) : null}
        <PlotRouteRumorView
          hooks={data.storyHooks}
          threads={data.plotThreads}
          routes={data.routeAffinities}
          triggers={data.triggerConditions}
          sceneBeats={data.sceneBeats}
          dailyEpisodes={data.dailyEpisodes}
          groupInteractions={data.groupInteractions}
          suggestions={data.relationshipSuggestions}
          conflicts={data.organizationConflicts}
          rumors={data.rumors}
          propagations={data.rumorPropagations}
          isBusy={isBusy}
          canManage={data.canManageSelectedWorld}
          onDryRunTrigger={handleDryRunTriggerCondition}
          onResolveConflict={handleResolveOrganizationConflict}
          onDeliverRumor={handleDeliverRumorPropagation}
        />
      </section>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="clock-title">
          <h2 className="section-title" id="clock-title">
            World clock
          </h2>
          {clock !== null ? (
            <>
              <div className="clock-grid">
                <div>
                  <p className="metric-label">Status</p>
                  <p className="metric-value">{clock.status}</p>
                </div>
                <div>
                  <p className="metric-label">Effective time</p>
                  <p>{clock.effective_world_time}</p>
                </div>
                <div>
                  <p className="metric-label">Revision</p>
                  <p className="metric-value">{clock.revision}</p>
                </div>
              </div>
              {data.canManageSelectedWorld ? (
                <div className="clock-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => pauseWorldClock(selectedWorld.id), "Clock paused.")
                    }
                  >
                    Pause clock
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => resumeWorldClock(selectedWorld.id), "Clock resumed.")
                    }
                  >
                    Resume clock
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => advanceWorldClock(selectedWorld.id), "Clock advanced.")
                    }
                  >
                    Advance clock
                  </button>
                  <form
                    className="inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void runAction(
                        () =>
                          skipWorldClock(
                            selectedWorld.id,
                            formString(form, "target_world_time"),
                          ),
                        "Clock skipped.",
                      );
                    }}
                  >
                    <input
                      className="text-input"
                      name="target_world_time"
                      placeholder="2030-01-01T00:00:00Z"
                    />
                    <button className="secondary-button" type="submit">
                      Skip clock
                    </button>
                  </form>
                  <form
                    className="inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void runAction(
                        () =>
                          resumeWorldClock(
                            selectedWorld.id,
                            optionalFormString(form, "speed_multiplier") ?? undefined,
                          ),
                        "Clock resumed.",
                      );
                    }}
                  >
                    <input
                      className="text-input"
                      name="speed_multiplier"
                      placeholder="Speed multiplier"
                    />
                    <button className="secondary-button" type="submit">
                      Resume with multiplier
                    </button>
                  </form>
                </div>
              ) : null}
              {data.canManageSelectedWorld ? (
                <div className="resource-list">
                  {data.clockTransitions.length === 0 ? (
                    <article className="resource-row">
                      <div>
                        <h3>No clock transitions</h3>
                        <p>No records are available.</p>
                      </div>
                    </article>
                  ) : (
                    data.clockTransitions.map((transition) => (
                      <article className="resource-row" key={transition.id}>
                        <div>
                          <h3>
                            {transition.transition_type} to revision{" "}
                            {transition.new_revision}
                          </h3>
                          <p>
                            {transition.previous_status ?? "none"} to{" "}
                            {transition.new_status} - {transition.wall_time}
                          </p>
                          <p>{transition.reason ?? transition.actor_ref ?? "No reason"}</p>
                        </div>
                      </article>
                    ))
                  )}
                </div>
              ) : null}
            </>
          ) : (
            <p>Clock state unavailable.</p>
          )}
        </section>

        <section className="management-panel" aria-labelledby="replay-title">
          <h2 className="section-title" id="replay-title">
            Replay and snapshots
          </h2>
          <div className="dashboard-grid">
            <div className="metric">
              <p className="metric-label">Live clock</p>
              <p className="metric-value">{clock?.status ?? "unknown"}</p>
              <p>Revision {clock?.revision ?? "n/a"}</p>
              <p>{clock?.effective_world_time ?? "No live clock state"}</p>
            </div>
            <div className="metric">
              <p className="metric-label">Reconstructed clock</p>
              <p className="metric-value">{data.replayState?.clock?.status ?? "none"}</p>
              <p>Revision {data.replayState?.clock?.revision ?? "n/a"}</p>
              <p>Source sequence {data.replayState?.source_sequence ?? 0}</p>
            </div>
            <div className="metric">
              <p className="metric-label">Replay events</p>
              <p className="metric-value">{data.replayState?.applied_event_count ?? 0}</p>
              <p>Unhandled {data.replayState?.unhandled_event_count ?? 0}</p>
            </div>
            <div className="metric">
              <p className="metric-label">Snapshot integrity</p>
              <p className="metric-value">{data.snapshotIntegrity?.status ?? "unknown"}</p>
              <p>Gap {data.snapshotIntegrity?.event_gap ?? "n/a"}</p>
              <p>Payload {data.snapshotIntegrity?.payload_location ?? "n/a"}</p>
              <p>Latest event {data.snapshotIntegrity?.latest_event_sequence ?? "n/a"}</p>
            </div>
          </div>
          <div className="resource-list">
            <article className="resource-row">
              <div>
                <h3>Latest snapshot</h3>
                {data.latestSnapshot === null ? (
                  <p>none</p>
                ) : (
                  <>
                    <p>
                      {data.latestSnapshot.status} - covers sequence{" "}
                      {data.latestSnapshot.covers_event_sequence}
                    </p>
                    <p>
                      {data.latestSnapshot.schema_version} - {data.latestSnapshot.created_at}
                    </p>
                    <p>Payload {data.latestSnapshot.payload_location ?? "unknown"}</p>
                  </>
                )}
              </div>
            </article>
            {data.snapshotIntegrity?.issues.map((issue) => (
              <article className="resource-row" key={issue}>
                <div>
                  <h3>Integrity issue</h3>
                  <p>{issue}</p>
                </div>
              </article>
            ))}
          </div>
          {data.canManageSelectedWorld ? (
            <button
              className="primary-button"
              type="button"
              onClick={() => runAction(() => createSnapshot(selectedWorld.id), "Snapshot created.")}
            >
              Create snapshot
            </button>
          ) : null}
        </section>
      </div>

      <section className="management-panel" aria-labelledby="rules-title">
        <h2 className="section-title" id="rules-title">
          Schedule rules
        </h2>
        {data.canManageSelectedWorld ? (
          <>
            <form className="management-form" onSubmit={handleCreateRule}>
              <input className="text-input" name="rule_key" placeholder="rule-key" />
              <input className="text-input" name="name" placeholder="Rule name" />
              <select className="text-input" name="kind" defaultValue="weekday">
                <option value="weekday">weekday</option>
                <option value="weekend">weekend</option>
                <option value="timetable">timetable</option>
              </select>
              <input className="text-input" name="config" placeholder="{}" />
              <button className="primary-button" type="submit" disabled={isBusy}>
                Create schedule rule
              </button>
            </form>
            <form className="management-form" onSubmit={handlePreviewRule}>
              <select className="text-input" name="kind" defaultValue="weekday">
                <option value="weekday">weekday</option>
                <option value="weekend">weekend</option>
                <option value="timetable">timetable</option>
              </select>
              <input
                className="text-input"
                name="config"
                defaultValue="{}"
                placeholder='{"hours":[8]}'
              />
              <input
                className="text-input"
                name="start_world_time"
                placeholder="2030-01-01T07:00:00Z"
              />
              <input className="text-input" name="horizon_hours" placeholder="Horizon hours" />
              <input className="text-input" name="limit" placeholder="Limit" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Preview schedule
              </button>
            </form>
          </>
        ) : null}
        {schedulePreview !== null ? (
          <section>
            <p>
              Preview matches {schedulePreview.match_count} windows for{" "}
              {schedulePreview.affected_agent_count} agents.
            </p>
            <ResourceList
              rows={schedulePreview.matches.map((match) => ({
                id: match.world_time,
                title: match.world_time,
                detail: `${match.reason} - ${match.affected_agent_count} agents`,
              }))}
            />
          </section>
        ) : null}
        <section aria-labelledby="calendar-conflicts-title">
          <h3 id="calendar-conflicts-title">Calendar conflicts</h3>
          {data.canManageSelectedWorld ? (
            <form className="management-form" onSubmit={handleRefreshConflicts}>
              <input
                className="text-input"
                name="start_world_time"
                placeholder="2030-01-01T07:00:00Z"
              />
              <input className="text-input" name="horizon_hours" placeholder="Horizon hours" />
              <input className="text-input" name="limit" placeholder="Limit" />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Check conflicts
              </button>
            </form>
          ) : null}
          <CalendarConflictsView report={calendarConflicts} />
        </section>
        <ResourceList
          rows={data.scheduleRules.map((rule) => ({
            id: rule.id,
            title: rule.name,
            detail: `${rule.rule_key} - ${rule.kind} - ${
              rule.is_enabled ? "Enabled" : "Disabled"
            }`,
          }))}
        />
      </section>

      <section className="management-panel" aria-labelledby="next-title">
        <h2 className="section-title" id="next-title">
          Workspace pages
        </h2>
        <div className="button-row">
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/agents`}>
            Build agents
          </Link>
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/conversations`}>
            Open conversations
          </Link>
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/narrative`}>
            Narrative artifacts
          </Link>
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/reader`}>
            Reader
          </Link>
        </div>
      </section>

      {data.canManageSelectedWorld ? (
        <section className="management-panel" aria-labelledby="event-audit-title">
          <h2 className="section-title" id="event-audit-title">
            Event audit
          </h2>
          <form className="inline-form" onSubmit={handleEventAuditFilter}>
            <input className="text-input" name="event_name" placeholder="event.name" />
            <input className="text-input" name="actor_ref" placeholder="actor:ref" />
            <select className="text-input" name="importance" defaultValue="">
              <option value="">Any importance</option>
              <option value="system">system</option>
              <option value="daily">daily</option>
              <option value="relationship">relationship</option>
              <option value="organization">organization</option>
              <option value="route">route</option>
              <option value="main_plot">main_plot</option>
            </select>
            <input className="text-input" name="sequence_after" placeholder="After sequence" />
            <input className="text-input" name="sequence_before" placeholder="Before sequence" />
            <input className="text-input" name="wall_time_from" placeholder="Wall time from" />
            <input className="text-input" name="wall_time_to" placeholder="Wall time to" />
            <input className="text-input" name="limit" placeholder="Limit" defaultValue="10" />
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Filter events
            </button>
          </form>
          <div className="resource-list">
            {worldEventAudit.length === 0 ? (
              <article className="resource-row">
                <div>
                  <h3>No audit events</h3>
                  <p>No records are available.</p>
                </div>
              </article>
            ) : (
              worldEventAudit.map((event) => (
                <article className="resource-row" key={event.id}>
                  <div>
                    <h3>
                      #{event.sequence} {event.event_name}
                    </h3>
                    <p>
                      {event.actor_ref} - {event.importance} - {event.wall_time}
                    </p>
                    <p>{formatPayload(event)}</p>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      ) : null}

      <section className="management-panel" aria-labelledby="composition-title">
        <h2 className="section-title" id="composition-title">
          World composition
        </h2>
        {data.canManageSelectedWorld ? (
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() => void handleExportComposition()}
            >
              Export composition
            </button>
          </div>
        ) : (
          <p>Read-only world composition access.</p>
        )}
        <textarea
          className="text-input"
          rows={10}
          readOnly
          value={exportedComposition}
          placeholder="Exported composition JSON appears here."
        />
        {data.isPlatformAdmin ? (
          <form className="management-form" onSubmit={handleValidateComposition}>
            <input className="text-input" name="slug" placeholder="validate-world-slug" />
            <input className="text-input" name="name" placeholder="Validate world name" />
            <input
              className="text-input"
              name="owner_user_id"
              defaultValue={selectedWorld.owner_user_id}
              placeholder="Owner user id"
            />
            <input className="text-input" name="description" placeholder="Override description" />
            <textarea
              className="text-input"
              name="rules_config"
              rows={3}
              defaultValue={JSON.stringify(selectedWorld.rules_config, null, 2)}
            />
            <textarea
              className="text-input"
              name="composition"
              rows={10}
              value={compositionDraft}
              onChange={(event) => setCompositionDraft(event.target.value)}
              placeholder="Paste composition JSON to validate"
            />
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Validate composition
            </button>
          </form>
        ) : null}
        {compositionValidation !== null ? (
          <section aria-labelledby="composition-validation-title">
            <h3 id="composition-validation-title">Composition validation</h3>
            <p>
              {compositionValidation.valid ? "Ready to import" : "Import blocked"} -{" "}
              {compositionValidation.blocking_issue_count} blocking,{" "}
              {compositionValidation.warning_issue_count} warning
            </p>
            <ResourceList
              rows={compositionValidation.issues.map((issue) => ({
                id: `${issue.code}:${issue.field}:${issue.message}`,
                title: `${issue.severity} - ${issue.code}`,
                detail: `${issue.field}: ${issue.message}`,
              }))}
            />
          </section>
        ) : null}
        {data.isPlatformAdmin ? (
          <form className="management-form" onSubmit={handleImportComposition}>
            <input className="text-input" name="slug" placeholder="imported-world-slug" />
            <input className="text-input" name="name" placeholder="Imported world name" />
            <input
              className="text-input"
              name="owner_user_id"
              defaultValue={selectedWorld.owner_user_id}
              placeholder="Owner user id"
            />
            <input className="text-input" name="description" placeholder="Override description" />
            <textarea
              className="text-input"
              name="rules_config"
              rows={3}
              defaultValue={JSON.stringify(selectedWorld.rules_config, null, 2)}
            />
            <textarea
              className="text-input"
              name="composition"
              rows={10}
              value={compositionDraft}
              onChange={(event) => setCompositionDraft(event.target.value)}
              placeholder="Paste exported composition JSON"
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Import as new world
            </button>
          </form>
        ) : null}
        <p>
          Export includes world metadata, scenes, agents, schedule rules, and preset references.
          It excludes memberships, auth/session, clock state, events, diagnostics, memory,
          observations, conversations, and narrative artifacts.
        </p>
      </section>

      <section className="management-panel" aria-labelledby="world-diagnostics-title">
        <h2 className="section-title" id="world-diagnostics-title">
          World diagnostics
        </h2>
        <ResourceList
          rows={worldDiagnostics.map((diagnostic) => ({
            id: diagnostic.id,
            title: `${diagnostic.severity} - ${diagnostic.component}`,
            detail: diagnostic.message,
          }))}
        />
      </section>
    </section>
  );
}

function mergeWorldDiagnostics(
  current: RuntimeDiagnostic[],
  incoming: RuntimeDiagnostic[],
): RuntimeDiagnostic[] {
  const byId = new Map(current.map((diagnostic) => [diagnostic.id, diagnostic]));
  for (const diagnostic of incoming) {
    byId.set(diagnostic.id, diagnostic);
  }
  return Array.from(byId.values()).sort((left, right) =>
    right.occurred_at.localeCompare(left.occurred_at),
  );
}

function optionalPositiveInteger(form: FormData, key: string): number | null {
  const value = optionalFormString(form, key);
  if (value === null) {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function signedInteger(form: FormData, key: string): number | null {
  const value = optionalFormString(form, key);
  if (value === null) {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function selectedValues(form: FormData, key: string): string[] {
  return form
    .getAll(key)
    .map((item) => (typeof item === "string" ? item : ""))
    .filter((item) => item !== "");
}

function commaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

function formatPayload(event: WorldEventAuditEntry): string {
  const payload = JSON.stringify(event.payload);
  if (payload.length <= 160) {
    return payload;
  }
  return `${payload.slice(0, 157)}...`;
}

function AgentSelect({
  agents,
  name,
  label,
}: {
  agents: { id: string; display_name: string }[];
  name: string;
  label: string;
}) {
  return (
    <select className="text-input" name={name} defaultValue="" aria-label={label}>
      <option value="">{label}</option>
      {agents.map((agent) => (
        <option key={agent.id} value={agent.id}>
          {agent.display_name}
        </option>
      ))}
    </select>
  );
}

function MultiAgentSelect({
  agents,
  name,
}: {
  agents: { id: string; display_name: string }[];
  name: string;
}) {
  return (
    <select className="text-input" name={name} multiple size={Math.min(4, Math.max(2, agents.length))}>
      {agents.map((agent) => (
        <option key={agent.id} value={agent.id}>
          {agent.display_name}
        </option>
      ))}
    </select>
  );
}

function SceneSelect({
  scenes,
  name,
  label,
}: {
  scenes: { id: string; name: string }[];
  name: string;
  label: string;
}) {
  return (
    <select className="text-input" name={name} defaultValue="" aria-label={label}>
      <option value="">{label}</option>
      {scenes.map((scene) => (
        <option key={scene.id} value={scene.id}>
          {scene.name}
        </option>
      ))}
    </select>
  );
}

function OrganizationSelect({
  organizations,
  name,
  label,
}: {
  organizations: { id: string; name: string }[];
  name: string;
  label: string;
}) {
  return (
    <select className="text-input" name={name} defaultValue="" aria-label={label}>
      <option value="">{label}</option>
      {organizations.map((organization) => (
        <option key={organization.id} value={organization.id}>
          {organization.name}
        </option>
      ))}
    </select>
  );
}

function MultiOrganizationSelect({
  organizations,
  name,
}: {
  organizations: { id: string; name: string }[];
  name: string;
}) {
  return (
    <select
      className="text-input"
      name={name}
      multiple
      size={Math.min(4, Math.max(2, organizations.length))}
    >
      {organizations.map((organization) => (
        <option key={organization.id} value={organization.id}>
          {organization.name}
        </option>
      ))}
    </select>
  );
}

function DailyLifeView({
  preview,
  candidates,
  offscreenEvents,
}: {
  preview: DailyLifePreview | null;
  candidates: DailyLifeEventCandidate[];
  offscreenEvents: OffscreenEventQueueItem[];
}) {
  return (
    <div className="management-columns">
      <section aria-labelledby="daily-preview-title">
        <h3 id="daily-preview-title">Daily preview</h3>
        {preview === null ? (
          <p className="status-detail">No preview loaded.</p>
        ) : (
          <ResourceList
            rows={preview.candidates.map((candidate, index) => ({
              id: candidate.id ?? `${candidate.title}-${index}`,
              title: candidate.title,
              detail: `${candidate.agent_display_name ?? "world"} at ${
                candidate.scene_name ?? "offscreen"
              } - ${candidate.importance}`,
            }))}
          />
        )}
      </section>
      <section aria-labelledby="daily-candidates-title">
        <h3 id="daily-candidates-title">Daily candidates</h3>
        <ResourceList
          rows={candidates.map((candidate, index) => ({
            id: candidate.id ?? `${candidate.title}-${index}`,
            title: candidate.title,
            detail: `${candidate.status} - ${candidate.starts_at}`,
          }))}
        />
      </section>
      <section aria-labelledby="offscreen-queue-title">
        <h3 id="offscreen-queue-title">Offscreen queue</h3>
        <ResourceList
          rows={offscreenEvents.map((item) => ({
            id: item.id,
            title: item.title,
            detail: `${item.status} - ${item.importance} - ${item.due_at}${
              item.last_error === null ? "" : ` - ${item.last_error}`
            }`,
          }))}
        />
      </section>
    </div>
  );
}

function PlotRouteRumorView({
  hooks,
  threads,
  routes,
  triggers,
  sceneBeats,
  dailyEpisodes,
  groupInteractions,
  suggestions,
  conflicts,
  rumors,
  propagations,
  isBusy,
  canManage,
  onDryRunTrigger,
  onResolveConflict,
  onDeliverRumor,
}: {
  hooks: StoryHook[];
  threads: PlotThread[];
  routes: RouteAffinity[];
  triggers: EventTriggerCondition[];
  sceneBeats: SceneBeatDraft[];
  dailyEpisodes: DailyEpisodeDraft[];
  groupInteractions: GroupInteractionContext[];
  suggestions: RelationshipEventSuggestion[];
  conflicts: OrganizationConflict[];
  rumors: Rumor[];
  propagations: RumorPropagation[];
  isBusy: boolean;
  canManage: boolean;
  onDryRunTrigger: (conditionId: string) => Promise<void>;
  onResolveConflict: (conflictId: string) => Promise<void>;
  onDeliverRumor: (propagationId: string) => Promise<void>;
}) {
  return (
    <div className="management-columns">
      <section aria-labelledby="plot-hooks-title">
        <h3 id="plot-hooks-title">Hooks, threads, and routes</h3>
        <div className="resource-list">
          {hooks.length === 0 && threads.length === 0 && routes.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>None yet</h3>
                <p>No records are available.</p>
              </div>
            </article>
          ) : null}
          {hooks.map((hook) => (
            <article className="resource-row" key={hook.id}>
              <div>
                <h3>{hook.title}</h3>
                <p>
                  {hook.hook_key} - {hook.hook_type} - {hook.status}
                </p>
                <p>{hook.summary}</p>
              </div>
            </article>
          ))}
          {threads.map((thread) => (
            <article className="resource-row" key={thread.id}>
              <div>
                <h3>{thread.title}</h3>
                <p>
                  {thread.thread_key} - {thread.thread_type} - {thread.status}
                </p>
                <p>{thread.summary}</p>
              </div>
            </article>
          ))}
          {routes.map((route) => (
            <article className="resource-row" key={route.id}>
              <div>
                <h3>{route.route_key}</h3>
                <p>
                  {route.agent_display_name} - {route.status} - affinity {route.affinity} /
                  stage {route.stage}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="beats-triggers-title">
        <h3 id="beats-triggers-title">Triggers and drafts</h3>
        <div className="resource-list">
          {triggers.length === 0 && sceneBeats.length === 0 && dailyEpisodes.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>None yet</h3>
                <p>No records are available.</p>
              </div>
            </article>
          ) : null}
          {triggers.map((trigger) => (
            <article className="resource-row" key={trigger.id}>
              <div>
                <h3>{trigger.name}</h3>
                <p>
                  {trigger.condition_key} - {trigger.status} - priority {trigger.priority}
                </p>
              </div>
              {canManage ? (
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => void onDryRunTrigger(trigger.id)}
                  >
                    Dry-run trigger
                  </button>
                </div>
              ) : null}
            </article>
          ))}
          {sceneBeats.map((beat) => (
            <article className="resource-row" key={beat.id}>
              <div>
                <h3>{beat.title}</h3>
                <p>
                  {beat.source_kind} - {beat.status} - {beat.scene_name ?? "no scene"}
                </p>
                <p>{beat.setup}</p>
              </div>
            </article>
          ))}
          {dailyEpisodes.map((episode) => (
            <article className="resource-row" key={episode.id}>
              <div>
                <h3>{episode.title}</h3>
                <p>{episode.status}</p>
                <p>{episode.summary}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="rumor-flow-title">
        <h3 id="rumor-flow-title">Groups, conflicts, and rumors</h3>
        <div className="resource-list">
          {groupInteractions.length === 0 &&
          suggestions.length === 0 &&
          conflicts.length === 0 &&
          rumors.length === 0 &&
          propagations.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>None yet</h3>
                <p>No records are available.</p>
              </div>
            </article>
          ) : null}
          {groupInteractions.map((context) => (
            <article className="resource-row" key={context.id}>
              <div>
                <h3>{context.title}</h3>
                <p>
                  {context.interaction_type} - {context.status} -{" "}
                  {context.scene_name ?? context.organization_name ?? "unscoped"}
                </p>
              </div>
            </article>
          ))}
          {suggestions.map((suggestion) => (
            <article className="resource-row" key={suggestion.id}>
              <div>
                <h3>{suggestion.title}</h3>
                <p>
                  {suggestion.status} - score {suggestion.score}
                </p>
                <p>{suggestion.reason}</p>
              </div>
            </article>
          ))}
          {conflicts.map((conflict) => (
            <article className="resource-row" key={conflict.id}>
              <div>
                <h3>{conflict.title}</h3>
                <p>
                  {conflict.organization_name} - {conflict.status} - pressure{" "}
                  {conflict.pressure_delta} / progress {conflict.progress_delta}
                </p>
              </div>
              {canManage && conflict.status !== "resolved" ? (
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => void onResolveConflict(conflict.id)}
                  >
                    Resolve conflict
                  </button>
                </div>
              ) : null}
            </article>
          ))}
          {rumors.map((rumor) => (
            <article className="resource-row" key={rumor.id}>
              <div>
                <h3>{rumor.title}</h3>
                <p>
                  {rumor.visibility} - {rumor.status} - known by{" "}
                  {rumor.known_agent_ids.length}
                </p>
                <p>{rumor.content}</p>
              </div>
            </article>
          ))}
          {propagations.map((propagation) => (
            <article className="resource-row" key={propagation.id}>
              <div>
                <h3>{propagation.rumor_title}</h3>
                <p>
                  {propagation.status} to{" "}
                  {propagation.target_agent_display_name ??
                    propagation.target_organization_name ??
                    "unassigned"}
                </p>
                <p>{propagation.propagation_reason}</p>
              </div>
              {canManage && propagation.status === "pending" ? (
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => void onDeliverRumor(propagation.id)}
                  >
                    Deliver rumor
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function WorldlineSelect({ worldlines }: { worldlines: Worldline[] }) {
  return (
    <select className="text-input" name="worldline_id" defaultValue="">
      <option value="">Primary worldline</option>
      {worldlines.map((worldline) => (
        <option key={worldline.id} value={worldline.id}>
          {worldline.name}
        </option>
      ))}
    </select>
  );
}

function GMWorldlineView({
  worldlines,
  agendas,
  proposals,
  rules,
  actors,
  choices,
  isBusy,
  canManage,
  onResolveProposal,
  onDryRunRule,
}: {
  worldlines: Worldline[];
  agendas: GMAgenda[];
  proposals: GMEventProposal[];
  rules: EventResolutionRule[];
  actors: PlayerActor[];
  choices: PlayerChoice[];
  isBusy: boolean;
  canManage: boolean;
  onResolveProposal: (proposalId: string) => Promise<void>;
  onDryRunRule: (ruleId: string) => Promise<void>;
}) {
  return (
    <div className="management-columns">
      <section aria-labelledby="worldlines-list-title">
        <h3 id="worldlines-list-title">Worldlines</h3>
        <ResourceList
          rows={worldlines.map((worldline) => ({
            id: worldline.id,
            title: `${worldline.name} (${worldline.worldline_key})`,
            detail:
              worldline.parent_worldline_id === null
                ? `${worldline.status} primary`
                : `${worldline.status} fork from sequence ${
                    worldline.fork_event_sequence ?? "latest"
                  }`,
          }))}
        />
      </section>
      <section aria-labelledby="gm-agenda-list-title">
        <h3 id="gm-agenda-list-title">GM agenda and proposals</h3>
        <div className="resource-list">
          {agendas.length === 0 && proposals.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>None yet</h3>
                <p>No records are available.</p>
              </div>
            </article>
          ) : null}
          {agendas.map((agenda) => (
            <article className="resource-row" key={agenda.id}>
              <div>
                <h3>{agenda.title}</h3>
                <p>
                  {agenda.status} - priority {agenda.priority}
                </p>
                <p>{agenda.summary}</p>
              </div>
            </article>
          ))}
          {proposals.map((proposal) => (
            <article className="resource-row" key={proposal.id}>
              <div>
                <h3>{proposal.title}</h3>
                <p>
                  {proposal.status} - {proposal.importance} - risk {proposal.risk_score}
                </p>
                <p>{proposal.reason}</p>
              </div>
              {canManage && proposal.status !== "resolved" ? (
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => void onResolveProposal(proposal.id)}
                  >
                    Resolve proposal
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="resolution-rule-list-title">
        <h3 id="resolution-rule-list-title">Rules and choices</h3>
        <div className="resource-list">
          {rules.length === 0 && actors.length === 0 && choices.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>None yet</h3>
                <p>No records are available.</p>
              </div>
            </article>
          ) : null}
          {rules.map((rule) => (
            <article className="resource-row" key={rule.id}>
              <div>
                <h3>{rule.name}</h3>
                <p>
                  {rule.rule_key} - {rule.status} - priority {rule.priority}
                </p>
              </div>
              {canManage ? (
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => void onDryRunRule(rule.id)}
                  >
                    Dry-run rule
                  </button>
                </div>
              ) : null}
            </article>
          ))}
          {actors.map((actor) => (
            <article className="resource-row" key={actor.id}>
              <div>
                <h3>{actor.display_name}</h3>
                <p>
                  {actor.actor_ref} - {actor.is_active ? "active" : "inactive"}
                </p>
              </div>
            </article>
          ))}
          {choices.map((choice) => (
            <article className="resource-row" key={choice.id}>
              <div>
                <h3>{choice.choice_key}</h3>
                <p>
                  {choice.choice_kind} - {choice.applied_event_id === null ? "preview" : "applied"}
                </p>
                <p>{choice.selected_option}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function CalendarConflictsView({ report }: { report: CalendarConflictReport | null }) {
  if (report === null) {
    return <p className="status-detail">Conflict report unavailable.</p>;
  }
  if (report.conflicts.length === 0) {
    return <p className="status-detail">No conflicts in the selected window.</p>;
  }
  return (
    <ResourceList
      rows={report.conflicts.map((conflict, index) => ({
        id: `${conflict.conflict_type}-${conflict.starts_at}-${index}`,
        title: `${conflict.conflict_type} at ${conflict.starts_at}`,
        detail: `${conflict.reason} - ${conflict.sources
          .map((source) => source.label)
          .join(" / ")}`,
      }))}
    />
  );
}

function ResourceList({ rows }: { rows: { id: string; title: string; detail: string }[] }) {
  if (rows.length === 0) {
    return (
      <div className="resource-list">
        <article className="resource-row">
          <div>
            <h3>None yet</h3>
            <p>No records are available.</p>
          </div>
        </article>
      </div>
    );
  }
  return (
    <div className="resource-list">
      {rows.map((row) => (
        <article className="resource-row" key={row.id}>
          <div>
            <h3>{row.title}</h3>
            <p>{row.detail}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
