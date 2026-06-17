"use client";

import { FormEvent, type ReactNode, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import type { AuthSubject } from "@/lib/auth/types";
import {
  cancelAgentCalendarEntry,
  createAgentCalendarEntry,
  createAgentObservation,
  createAgent,
  createNarrativeArtifact,
  createProviderProfile,
  createScene,
  createScheduleRule,
  createSnapshot,
  createWorld,
  advanceWorldClock,
  deactivateAgent,
  deactivateScene,
  deactivateWorld,
  deleteMembership,
  disableProviderProfile,
  disableScheduleRule,
  getLatestSnapshot,
  getAgentPersona,
  getReplayState,
  getRuntimeControl,
  getRuntimeStatus,
  getWorldClock,
  listAgentCalendar,
  listAgentMemory,
  listAgentObservations,
  listAgentRuns,
  listAgents,
  listRuntimeDiagnostics,
  listMemberCandidates,
  listMemberships,
  listNarrativeArtifacts,
  listProviderProfiles,
  listScheduleRules,
  listScenes,
  listWorldDiagnostics,
  pauseWorldClock,
  resumeWorldClock,
  runAgent,
  refreshAgentObservations,
  searchAgentMemory,
  skipWorldClock,
  testProviderProfile,
  updateAgent,
  updateAgentCalendarEntry,
  updateAgentPersona,
  updateProviderProfile,
  updateRuntimeControl,
  updateScheduleRule,
  updateScene,
  updateWorld,
  upsertMembership,
  WorldClientError,
} from "@/lib/worlds/client";
import type {
  Agent,
  AgentKind,
  AgentObservation,
  AgentPersona,
  AgentRun,
  CalendarEntry,
  MemberCandidate,
  MemoryItem,
  Membership,
  NarrativeArtifact,
  NarrativeArtifactKind,
  ProviderProfile,
  ProviderType,
  RuntimeDiagnostic,
  RuntimeControl,
  RuntimeStatus,
  Scene,
  ScheduleRule,
  ScheduleRuleKind,
  World,
  WorldClock,
  WorldDashboardData,
  WorldReplayState,
  WorldRole,
  WorldSnapshot,
} from "@/lib/worlds/types";

type WorldManagementDashboardProps = {
  subject: AuthSubject;
  initialData: WorldDashboardData;
};

export function WorldManagementDashboard({
  subject,
  initialData,
}: WorldManagementDashboardProps) {
  const router = useRouter();
  const [worlds, setWorlds] = useState(initialData.worlds);
  const [selectedWorldId, setSelectedWorldId] = useState(initialData.selectedWorldId);
  const [scenes, setScenes] = useState(initialData.scenes);
  const [agents, setAgents] = useState(initialData.agents);
  const [memberships, setMemberships] = useState(initialData.memberships);
  const [clock, setClock] = useState(initialData.clock);
  const [replayState, setReplayState] = useState(initialData.replayState);
  const [latestSnapshot, setLatestSnapshot] = useState(initialData.latestSnapshot);
  const [selectedAgentId, setSelectedAgentId] = useState(initialData.selectedAgentId);
  const [calendarEntries, setCalendarEntries] = useState(initialData.calendarEntries);
  const [scheduleRules, setScheduleRules] = useState(initialData.scheduleRules);
  const [memoryItems, setMemoryItems] = useState(initialData.memoryItems);
  const [agentRuns, setAgentRuns] = useState(initialData.agentRuns);
  const [agentPersona, setAgentPersona] = useState(initialData.agentPersona);
  const [agentObservations, setAgentObservations] = useState(initialData.agentObservations);
  const [narrativeArtifacts, setNarrativeArtifacts] = useState(initialData.narrativeArtifacts);
  const [providerProfiles, setProviderProfiles] = useState(initialData.providerProfiles);
  const [runtimeControl, setRuntimeControl] = useState(initialData.runtimeControl);
  const [runtimeStatus, setRuntimeStatus] = useState(initialData.runtimeStatus);
  const [runtimeDiagnostics, setRuntimeDiagnostics] = useState(initialData.runtimeDiagnostics);
  const [worldDiagnostics, setWorldDiagnostics] = useState(initialData.worldDiagnostics);
  const [canManageSelectedWorld, setCanManageSelectedWorld] = useState(
    initialData.canManageSelectedWorld,
  );
  const [memberCandidates, setMemberCandidates] = useState<MemberCandidate[]>([]);
  const [notice, setNotice] = useState(initialData.loadError);
  const [isBusy, setIsBusy] = useState(false);

  const selectedWorld = useMemo(
    () => worlds.find((world) => world.id === selectedWorldId) ?? null,
    [selectedWorldId, worlds],
  );
  const isPlatformAdmin = subject.roles.includes("platform_admin");
  const canManage = selectedWorld !== null && canManageSelectedWorld;
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null,
    [agents, selectedAgentId],
  );

  async function handleSelectWorld(nextWorldId: string) {
    if (nextWorldId === "") {
      return;
    }
    router.replace(worldQueryPath(nextWorldId));
    await loadWorld(nextWorldId);
  }

  async function loadWorld(worldId: string) {
    await runAction(async () => {
      const [
        nextScenes,
        nextAgents,
        nextMemberships,
        nextClock,
        nextReplayState,
        nextLatestSnapshot,
        nextScheduleRules,
        nextNarrativeArtifacts,
        nextWorldDiagnostics,
      ] = await Promise.all([
        listScenes(worldId),
        listAgents(worldId),
        listMembershipsIfAllowed(worldId),
        getWorldClock(worldId),
        getReplayState(worldId),
        getLatestSnapshot(worldId),
        listScheduleRules(worldId),
        listNarrativeArtifacts(worldId),
        listWorldDiagnosticsIfAllowed(worldId),
      ]);
      const nextSelectedAgent = nextAgents[0] ?? null;
      const nextCanManage = nextMemberships !== null;
      const [
        nextCalendarEntries,
        nextMemoryItems,
        nextAgentRuns,
        nextAgentPersona,
        nextAgentObservations,
      ] =
        nextSelectedAgent === null
          ? [[], [], [], null, []]
          : await Promise.all([
              listAgentCalendar(worldId, nextSelectedAgent.id),
              nextCanManage ? listAgentMemory(worldId, nextSelectedAgent.id) : Promise.resolve([]),
              listAgentRuns(worldId, nextSelectedAgent.id),
              nextCanManage
                ? getAgentPersona(worldId, nextSelectedAgent.id)
                : Promise.resolve(null),
              nextCanManage
                ? listAgentObservations(worldId, nextSelectedAgent.id)
                : Promise.resolve([]),
            ]);
      setSelectedWorldId(worldId);
      setScenes(nextScenes);
      setAgents(nextAgents);
      setMemberships(nextMemberships ?? []);
      setClock(nextClock);
      setReplayState(nextReplayState);
      setLatestSnapshot(nextLatestSnapshot);
      setSelectedAgentId(nextSelectedAgent?.id ?? null);
      setCalendarEntries(nextCalendarEntries);
      setScheduleRules(nextScheduleRules);
      setMemoryItems(nextMemoryItems);
      setAgentRuns(nextAgentRuns);
      setAgentPersona(nextAgentPersona);
      setAgentObservations(nextAgentObservations);
      setNarrativeArtifacts(nextNarrativeArtifacts);
      setWorldDiagnostics(nextWorldDiagnostics ?? []);
      setCanManageSelectedWorld(nextCanManage);
      setMemberCandidates([]);
    });
  }

  async function handleCreateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const slug = formString(form, "slug");
    const name = formString(form, "name");
    if (slug === "" || name === "") {
      setNotice("World slug and name are required.");
      return;
    }

    await runAction(async () => {
      const world = await createWorld({
        slug,
        name,
        description: optionalFormString(form, "description"),
      });
      const nextClock = await getWorldClock(world.id);
      setWorlds((currentWorlds) => [...currentWorlds, world].sort(compareWorlds));
      setSelectedWorldId(world.id);
      setScenes([]);
      setAgents([]);
      setClock(nextClock);
      setReplayState({
        world_id: world.id,
        schema_version: "world_state.v1",
        source_sequence: 0,
        clock: null,
        applied_event_count: 0,
        unhandled_event_count: 0,
      });
      setLatestSnapshot(null);
      setSelectedAgentId(null);
      setCalendarEntries([]);
      setScheduleRules([]);
      setMemoryItems([]);
      setAgentRuns([]);
      setAgentPersona(null);
      setAgentObservations([]);
      setNarrativeArtifacts([]);
      setWorldDiagnostics([]);
      setMemberships([
        {
          id: "local-owner",
          world_id: world.id,
          user_id: subject.user_id,
          role: "world_admin",
          user: {
            id: subject.user_id,
            email: subject.email,
            display_name: subject.display_name,
            is_active: true,
          },
        },
      ]);
      setCanManageSelectedWorld(true);
      setMemberCandidates([]);
      router.replace(worldQueryPath(world.id));
      formElement.reset();
    }, "World created.");
  }

  async function handleUpdateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const world = await updateWorld(selectedWorld.id, {
        name: formString(form, "name"),
        description: optionalFormString(form, "description"),
        is_active: form.get("is_active") === "on",
      });
      setWorlds((currentWorlds) => replaceById(currentWorlds, world));
    }, "World updated.");
  }

  async function handleDeactivateWorld() {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deactivateWorld(selectedWorld.id);
      setWorlds((currentWorlds) =>
        currentWorlds.map((world) =>
          world.id === selectedWorld.id ? { ...world, is_active: false } : world,
        ),
      );
    }, "World deactivated.");
  }

  async function handlePauseClock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setClock(await pauseWorldClock(selectedWorld.id, optionalFormString(form, "reason") ?? undefined));
    }, "Clock paused.");
  }

  async function handleResumeClock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setClock(
        await resumeWorldClock(
          selectedWorld.id,
          optionalFormString(form, "speed_multiplier") ?? undefined,
          optionalFormString(form, "reason") ?? undefined,
        ),
      );
    }, "Clock resumed.");
  }

  async function handleAdvanceClock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setClock(await advanceWorldClock(selectedWorld.id, optionalFormString(form, "reason") ?? undefined));
    }, "Clock advanced.");
  }

  async function handleSkipClock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const targetWorldTime = formString(form, "target_world_time");
    if (targetWorldTime === "") {
      setNotice("Target world time is required.");
      return;
    }
    await runAction(async () => {
      setClock(
        await skipWorldClock(
          selectedWorld.id,
          targetWorldTime,
          optionalFormString(form, "reason") ?? undefined,
        ),
      );
    }, "Clock skipped.");
  }

  async function handleRefreshReplay() {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      const [nextReplayState, nextLatestSnapshot] = await Promise.all([
        getReplayState(selectedWorld.id),
        getLatestSnapshot(selectedWorld.id),
      ]);
      setReplayState(nextReplayState);
      setLatestSnapshot(nextLatestSnapshot);
    }, "Replay state refreshed.");
  }

  async function handleCreateSnapshot() {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      const snapshot = await createSnapshot(selectedWorld.id);
      const nextReplayState = await getReplayState(selectedWorld.id);
      setLatestSnapshot(snapshot);
      setReplayState(nextReplayState);
    }, "Snapshot created.");
  }

  async function handleCreateScene(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const scene_key = formString(form, "scene_key");
    const name = formString(form, "name");
    if (scene_key === "" || name === "") {
      setNotice("Scene key and name are required.");
      return;
    }
    await runAction(async () => {
      const scene = await createScene(selectedWorld.id, {
        scene_key,
        name,
        description: optionalFormString(form, "description"),
      });
      setScenes((currentScenes) => [...currentScenes, scene].sort(compareScenes));
      formElement.reset();
    }, "Scene created.");
  }

  async function handleUpdateScene(event: FormEvent<HTMLFormElement>, scene: Scene) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedScene = await updateScene(selectedWorld.id, scene.id, {
        name: formString(form, "name"),
        description: optionalFormString(form, "description"),
        is_active: form.get("is_active") === "on",
      });
      setScenes((currentScenes) => replaceById(currentScenes, updatedScene));
    }, "Scene updated.");
  }

  async function handleDeactivateScene(scene: Scene) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deactivateScene(selectedWorld.id, scene.id);
      setScenes((currentScenes) =>
        currentScenes.map((currentScene) =>
          currentScene.id === scene.id ? { ...currentScene, is_active: false } : currentScene,
        ),
      );
    }, "Scene deactivated.");
  }

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const agent_key = formString(form, "agent_key");
    const display_name = formString(form, "display_name");
    if (agent_key === "" || display_name === "") {
      setNotice("Agent key and display name are required.");
      return;
    }
    await runAction(async () => {
      const agent = await createAgent(selectedWorld.id, {
        agent_key,
        display_name,
        kind: formString(form, "kind") as AgentKind,
        home_scene_id: optionalFormString(form, "home_scene_id"),
        config: dashboardJsonObject(formString(form, "config")),
      });
      setAgents((currentAgents) => [...currentAgents, agent].sort(compareAgents));
      setSelectedAgentId(agent.id);
      setCalendarEntries([]);
      setMemoryItems([]);
      setAgentRuns([]);
      setAgentPersona(null);
      setAgentObservations([]);
      formElement.reset();
    }, "Agent created.");
  }

  async function handleSelectAgent(agentId: string) {
    if (selectedWorld === null || agentId === "") {
      return;
    }
    await runAction(async () => {
      setSelectedAgentId(agentId);
      const [
        nextCalendarEntries,
        nextMemoryItems,
        nextAgentRuns,
        nextAgentPersona,
        nextAgentObservations,
      ] = await Promise.all([
        listAgentCalendar(selectedWorld.id, agentId),
        canManage ? listAgentMemory(selectedWorld.id, agentId) : Promise.resolve([]),
        listAgentRuns(selectedWorld.id, agentId),
        canManage ? getAgentPersona(selectedWorld.id, agentId) : Promise.resolve(null),
        canManage ? listAgentObservations(selectedWorld.id, agentId) : Promise.resolve([]),
      ]);
      setCalendarEntries(nextCalendarEntries);
      setMemoryItems(nextMemoryItems);
      setAgentRuns(nextAgentRuns);
      setAgentPersona(nextAgentPersona);
      setAgentObservations(nextAgentObservations);
    });
  }

  async function handleCreateCalendarEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = formString(form, "title");
    const starts_at = formString(form, "starts_at");
    if (title === "" || starts_at === "") {
      setNotice("Calendar title and start time are required.");
      return;
    }
    await runAction(async () => {
      const entry = await createAgentCalendarEntry(selectedWorld.id, selectedAgent.id, {
        title,
        starts_at,
        ends_at: optionalFormString(form, "ends_at"),
        description: optionalFormString(form, "description"),
        metadata: {},
      });
      setCalendarEntries((currentEntries) => [...currentEntries, entry].sort(compareCalendarEntries));
      formElement.reset();
    }, "Calendar entry created.");
  }

  async function handleUpdateCalendarEntry(
    event: FormEvent<HTMLFormElement>,
    entry: CalendarEntry,
  ) {
    event.preventDefault();
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedEntry = await updateAgentCalendarEntry(selectedWorld.id, selectedAgent.id, entry.id, {
        title: formString(form, "title"),
        starts_at: formString(form, "starts_at"),
        ends_at: optionalFormString(form, "ends_at"),
        description: optionalFormString(form, "description"),
        status: form.get("status") === "cancelled" ? "cancelled" : "active",
      });
      setCalendarEntries((currentEntries) => replaceById(currentEntries, updatedEntry));
    }, "Calendar entry updated.");
  }

  async function handleCancelCalendarEntry(entry: CalendarEntry) {
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    await runAction(async () => {
      await cancelAgentCalendarEntry(selectedWorld.id, selectedAgent.id, entry.id);
      setCalendarEntries((currentEntries) =>
        currentEntries.map((currentEntry) =>
          currentEntry.id === entry.id ? { ...currentEntry, status: "cancelled" } : currentEntry,
        ),
      );
    }, "Calendar entry cancelled.");
  }

  async function handleCreateScheduleRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const rule_key = formString(form, "rule_key");
    const name = formString(form, "name");
    if (rule_key === "" || name === "") {
      setNotice("Schedule rule key and name are required.");
      return;
    }
    await runAction(async () => {
      const rule = await createScheduleRule(selectedWorld.id, {
        rule_key,
        name,
        kind: formString(form, "kind") as ScheduleRuleKind,
        config: dashboardJsonObject(formString(form, "config")),
      });
      setScheduleRules((currentRules) => [...currentRules, rule].sort(compareScheduleRules));
      formElement.reset();
    }, "Schedule rule created.");
  }

  async function handleUpdateScheduleRule(event: FormEvent<HTMLFormElement>, rule: ScheduleRule) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedRule = await updateScheduleRule(selectedWorld.id, rule.id, {
        name: formString(form, "name"),
        kind: formString(form, "kind") as ScheduleRuleKind,
        config: dashboardJsonObject(formString(form, "config")),
        is_enabled: form.get("is_enabled") === "on",
      });
      setScheduleRules((currentRules) => replaceById(currentRules, updatedRule));
    }, "Schedule rule updated.");
  }

  async function handleDisableScheduleRule(rule: ScheduleRule) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await disableScheduleRule(selectedWorld.id, rule.id);
      setScheduleRules((currentRules) =>
        currentRules.map((currentRule) =>
          currentRule.id === rule.id ? { ...currentRule, is_enabled: false } : currentRule,
        ),
      );
    }, "Schedule rule disabled.");
  }

  async function handleSearchMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setMemoryItems(
        await searchAgentMemory(selectedWorld.id, selectedAgent.id, {
          query_text: formString(form, "query_text"),
          limit: optionalNumber(formString(form, "limit")),
        }),
      );
    }, "Memory search completed.");
  }

  async function handleRefreshMemory() {
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    await runAction(async () => {
      setMemoryItems(await listAgentMemory(selectedWorld.id, selectedAgent.id));
    }, "Memory refreshed.");
  }

  async function handleUpdatePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setAgentPersona(
        await updateAgentPersona(selectedWorld.id, selectedAgent.id, {
          persona_text: formString(form, "persona_text"),
          behavior_policy: dashboardJsonObject(formString(form, "behavior_policy")),
          is_enabled: form.get("is_enabled") === "on",
        }),
      );
    }, "Agent persona updated.");
  }

  async function handleCreateObservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const content = formString(form, "content");
    if (content === "") {
      setNotice("Observation content is required.");
      return;
    }
    await runAction(async () => {
      const observation = await createAgentObservation(selectedWorld.id, selectedAgent.id, {
        observation_type: formString(form, "observation_type") || "manual",
        content,
        metadata: dashboardJsonObject(formString(form, "metadata")),
        observed_at: optionalFormString(form, "observed_at"),
      });
      setAgentObservations((currentObservations) => [observation, ...currentObservations]);
      formElement.reset();
    }, "Agent observation created.");
  }

  async function handleRefreshObservations() {
    if (selectedWorld === null || selectedAgent === null || !canManage) {
      return;
    }
    await runAction(async () => {
      setAgentObservations(await refreshAgentObservations(selectedWorld.id, selectedAgent.id));
    }, "Agent observations refreshed.");
  }

  async function handleRunAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null || selectedAgent === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      const run = await runAgent(selectedWorld.id, selectedAgent.id, {
        prompt: optionalFormString(form, "prompt") ?? undefined,
        provider_profile_id: optionalFormString(form, "provider_profile_id"),
        create_memory: form.get("create_memory") === "on",
        create_narrative_artifact: form.get("create_narrative_artifact") === "on",
      });
      setAgentRuns((currentRuns) => [run, ...currentRuns]);
      setNarrativeArtifacts(await listNarrativeArtifacts(selectedWorld.id));
      setWorldDiagnostics(await listWorldDiagnosticsIfAllowed(selectedWorld.id) ?? []);
      if (canManage) {
        const [nextMemoryItems, nextObservations] = await Promise.all([
          listAgentMemory(selectedWorld.id, selectedAgent.id),
          listAgentObservations(selectedWorld.id, selectedAgent.id),
        ]);
        setMemoryItems(nextMemoryItems);
        setAgentObservations(nextObservations);
      }
      formElement.reset();
    }, "Agent run completed.");
  }

  async function handleCreateNarrativeArtifact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = formString(form, "title");
    const content = formString(form, "content");
    if (title === "" || content === "") {
      setNotice("Narrative title and content are required.");
      return;
    }
    await runAction(async () => {
      const artifact = await createNarrativeArtifact(selectedWorld.id, {
        title,
        content,
        artifact_kind: formString(form, "artifact_kind") as NarrativeArtifactKind,
        agent_id: optionalFormString(form, "agent_id"),
      });
      setNarrativeArtifacts((currentArtifacts) => [artifact, ...currentArtifacts]);
      formElement.reset();
    }, "Narrative artifact created.");
  }

  async function handleStartRuntime() {
    await runAction(async () => {
      setRuntimeControl(await updateRuntimeControl({ desired_state: "running" }));
      setRuntimeStatus(await getRuntimeStatus());
    }, "Runtime start requested.");
  }

  async function handleStopRuntime() {
    await runAction(async () => {
      setRuntimeControl(await updateRuntimeControl({ desired_state: "stopped" }));
      setRuntimeStatus(await getRuntimeStatus());
    }, "Runtime stop requested.");
  }

  async function handleRefreshRuntimeStatus() {
    await runAction(async () => {
      const [nextRuntimeControl, nextRuntimeStatus, nextRuntimeDiagnostics] = await Promise.all([
        getRuntimeControl(),
        getRuntimeStatus(),
        listRuntimeDiagnostics(),
      ]);
      setRuntimeControl(nextRuntimeControl);
      setRuntimeStatus(nextRuntimeStatus);
      setRuntimeDiagnostics(nextRuntimeDiagnostics);
    }, "Runtime status refreshed.");
  }

  async function handleCreateProviderProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const profile_key = formString(form, "profile_key");
    const name = formString(form, "name");
    if (profile_key === "" || name === "") {
      setNotice("Provider profile key and name are required.");
      return;
    }
    await runAction(async () => {
      const profile = await createProviderProfile({
        profile_key,
        name,
        provider_type: formString(form, "provider_type") as ProviderType,
        base_url: formString(form, "base_url"),
        model_name: formString(form, "model_name"),
        capabilities: dashboardJsonObject(formString(form, "capabilities")),
        api_key_ref: formString(form, "api_key_ref"),
        timeout_seconds: numberFormValue(form, "timeout_seconds", 20),
        retry_attempts: numberFormValue(form, "retry_attempts", 1),
        rate_limit_per_minute: optionalNumberFormValue(form, "rate_limit_per_minute"),
      });
      setProviderProfiles((currentProfiles) => [...currentProfiles, profile].sort(compareProviderProfiles));
      formElement.reset();
    }, "Provider profile created.");
  }

  async function handleUpdateProviderProfile(
    event: FormEvent<HTMLFormElement>,
    profile: ProviderProfile,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedProfile = await updateProviderProfile(profile.id, {
        name: formString(form, "name"),
        base_url: formString(form, "base_url"),
        model_name: formString(form, "model_name"),
        capabilities: dashboardJsonObject(formString(form, "capabilities")),
        api_key_ref: formString(form, "api_key_ref"),
        timeout_seconds: numberFormValue(form, "timeout_seconds", profile.timeout_seconds),
        retry_attempts: numberFormValue(form, "retry_attempts", profile.retry_attempts),
        rate_limit_per_minute: optionalNumberFormValue(form, "rate_limit_per_minute"),
        is_enabled: form.get("is_enabled") === "on",
      });
      setProviderProfiles((currentProfiles) => replaceById(currentProfiles, updatedProfile));
    }, "Provider profile updated.");
  }

  async function handleDisableProviderProfile(profile: ProviderProfile) {
    await runAction(async () => {
      await disableProviderProfile(profile.id);
      setProviderProfiles((currentProfiles) =>
        currentProfiles.map((currentProfile) =>
          currentProfile.id === profile.id
            ? { ...currentProfile, is_enabled: false }
            : currentProfile,
        ),
      );
    }, "Provider profile disabled.");
  }

  async function handleTestProviderProfile(
    event: FormEvent<HTMLFormElement>,
    profile: ProviderProfile,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const result = await testProviderProfile(
        profile.id,
        optionalFormString(form, "prompt") ?? undefined,
      );
      setProviderProfiles(await listProviderProfiles());
      setRuntimeDiagnostics(await listRuntimeDiagnostics());
      setNotice(
        result.status === "success"
          ? `Provider test succeeded in ${result.latency_ms}ms.`
          : `Provider test failed: ${result.error_code ?? "provider_error"}`,
      );
    });
  }

  async function handleUpdateAgent(event: FormEvent<HTMLFormElement>, agent: Agent) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedAgent = await updateAgent(selectedWorld.id, agent.id, {
        display_name: formString(form, "display_name"),
        home_scene_id: optionalFormString(form, "home_scene_id"),
        config: dashboardJsonObject(formString(form, "config")),
        is_enabled: form.get("is_enabled") === "on",
      });
      setAgents((currentAgents) => replaceById(currentAgents, updatedAgent));
    }, "Agent updated.");
  }

  async function handleDeactivateAgent(agent: Agent) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deactivateAgent(selectedWorld.id, agent.id);
      setAgents((currentAgents) =>
        currentAgents.map((currentAgent) =>
          currentAgent.id === agent.id ? { ...currentAgent, is_enabled: false } : currentAgent,
        ),
      );
    }, "Agent deactivated.");
  }

  async function handleSearchMembers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setMemberCandidates(await listMemberCandidates(selectedWorld.id, formString(form, "query")));
    });
  }

  async function handleUpsertMembership(candidate: MemberCandidate, role: WorldRole) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      const membership = await upsertMembership(selectedWorld.id, candidate.id, role);
      setMemberships((currentMemberships) => upsertByUserId(currentMemberships, membership));
      setMemberCandidates((currentCandidates) =>
        currentCandidates.map((currentCandidate) =>
          currentCandidate.id === candidate.id ? { ...currentCandidate, role } : currentCandidate,
        ),
      );
    }, "Membership saved.");
  }

  async function handleDeleteMembership(membership: Membership) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deleteMembership(selectedWorld.id, membership.user_id);
      setMemberships((currentMemberships) =>
        currentMemberships.filter((currentMembership) => currentMembership.id !== membership.id),
      );
      setMemberCandidates((currentCandidates) =>
        currentCandidates.map((candidate) =>
          candidate.id === membership.user_id ? { ...candidate, role: null } : candidate,
        ),
      );
    }, "Membership removed.");
  }

  async function runAction(action: () => Promise<void>, successMessage?: string) {
    setNotice(null);
    setIsBusy(true);
    try {
      await action();
      if (successMessage !== undefined) {
        setNotice(successMessage);
      }
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section" aria-label="World management">
      {notice !== null ? (
        <p className="management-notice" role="status">
          {notice}
        </p>
      ) : null}

      <div className="dashboard-grid" aria-label="World overview">
        <Metric label="Worlds" value={`${worlds.length} visible`} />
        <Metric label="Scenes" value={selectedWorld === null ? "No world" : `${scenes.length} listed`} />
        <Metric label="Agents" value={selectedWorld === null ? "No world" : `${agents.length} listed`} />
        <Metric
          label="Replay"
          value={replayState === null ? "No state" : `seq ${replayState.source_sequence}`}
        />
      </div>

      <div className="world-toolbar">
        <label className="field-label" htmlFor="world-select">
          Active world
        </label>
        <select
          className="text-input"
          id="world-select"
          value={selectedWorldId ?? ""}
          onChange={(event) => void handleSelectWorld(event.target.value)}
        >
          {worlds.length === 0 ? <option value="">No worlds yet</option> : null}
          {worlds.map((world) => (
            <option key={world.id} value={world.id}>
              {world.name} ({world.slug})
            </option>
          ))}
        </select>
      </div>

      {isPlatformAdmin ? (
        <section className="management-panel" aria-label="Create world">
          <h2 className="section-title">Create world</h2>
          <form className="management-form" onSubmit={(event) => void handleCreateWorld(event)}>
            <input className="text-input" name="slug" placeholder="world-slug" />
            <input className="text-input" name="name" placeholder="World name" />
            <input className="text-input" name="description" placeholder="Description" />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create world
            </button>
          </form>
        </section>
      ) : null}

      {isPlatformAdmin ? (
        <>
          <RuntimeControlPanel
            runtimeControl={runtimeControl}
            runtimeStatus={runtimeStatus}
            diagnostics={runtimeDiagnostics}
            isBusy={isBusy}
            onStart={handleStartRuntime}
            onStop={handleStopRuntime}
            onRefresh={handleRefreshRuntimeStatus}
          />
          <ProviderProfilesPanel
            profiles={providerProfiles}
            isBusy={isBusy}
            onCreate={handleCreateProviderProfile}
            onUpdate={handleUpdateProviderProfile}
            onDisable={handleDisableProviderProfile}
            onTest={handleTestProviderProfile}
          />
        </>
      ) : null}

      {selectedWorld === null ? (
        <section className="management-panel">
          <h2 className="section-title">No world selected</h2>
          <p className="status-detail">Create or join a world to manage scenes and agents.</p>
        </section>
      ) : (
        <>
          <section className="management-panel" aria-label="Selected world" key={selectedWorld.id}>
            <h2 className="section-title">{selectedWorld.name}</h2>
            <p className="status-detail">
              {selectedWorld.slug} - {selectedWorld.is_active ? "Active" : "Inactive"}
            </p>
            {canManage ? (
              <form className="management-form" onSubmit={(event) => void handleUpdateWorld(event)}>
                <input className="text-input" name="name" defaultValue={selectedWorld.name} />
                <input
                  className="text-input"
                  name="description"
                  defaultValue={selectedWorld.description ?? ""}
                  placeholder="Description"
                />
                <label className="checkbox-label">
                  <input name="is_active" type="checkbox" defaultChecked={selectedWorld.is_active} />
                  Active
                </label>
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Save world
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() => void handleDeactivateWorld()}
                >
                  Deactivate world
                </button>
              </form>
            ) : (
              <p className="status-detail">Read-only world access.</p>
            )}
          </section>

          <ClockPanel
            clock={clock}
            canManage={canManage}
            isBusy={isBusy}
            onPause={handlePauseClock}
            onResume={handleResumeClock}
            onAdvance={handleAdvanceClock}
            onSkip={handleSkipClock}
          />

          <ReplayPanel
            replayState={replayState}
            latestSnapshot={latestSnapshot}
            canManage={canManage}
            isBusy={isBusy}
            onRefresh={handleRefreshReplay}
            onCreateSnapshot={handleCreateSnapshot}
          />

          <ScheduleRulesPanel
            rules={scheduleRules}
            canManage={canManage}
            isBusy={isBusy}
            onCreate={handleCreateScheduleRule}
            onUpdate={handleUpdateScheduleRule}
            onDisable={handleDisableScheduleRule}
          />

          <CalendarPanel
            agents={agents}
            selectedAgent={selectedAgent}
            entries={calendarEntries}
            canManage={canManage}
            isBusy={isBusy}
            onSelectAgent={handleSelectAgent}
            onCreate={handleCreateCalendarEntry}
            onUpdate={handleUpdateCalendarEntry}
            onCancel={handleCancelCalendarEntry}
          />

          <MemoryPanel
            agents={agents}
            selectedAgent={selectedAgent}
            items={memoryItems}
            isBusy={isBusy}
            onSelectAgent={handleSelectAgent}
            onSearch={handleSearchMemory}
            onRefresh={handleRefreshMemory}
          />

          <AgentPersonaObservationsPanel
            agents={agents}
            selectedAgent={selectedAgent}
            persona={agentPersona}
            observations={agentObservations}
            canManage={canManage}
            isBusy={isBusy}
            onSelectAgent={handleSelectAgent}
            onUpdatePersona={handleUpdatePersona}
            onCreateObservation={handleCreateObservation}
            onRefreshObservations={handleRefreshObservations}
          />

          <AgentRunsPanel
            agents={agents}
            selectedAgent={selectedAgent}
            runs={agentRuns}
            providerProfiles={providerProfiles}
            canManage={canManage}
            isBusy={isBusy}
            onSelectAgent={handleSelectAgent}
            onRun={handleRunAgent}
          />

          <NarrativeArtifactsPanel
            agents={agents}
            artifacts={narrativeArtifacts}
            canManage={canManage}
            isBusy={isBusy}
            onCreate={handleCreateNarrativeArtifact}
          />

          {canManage ? <DiagnosticsPanel title="World diagnostics" diagnostics={worldDiagnostics} /> : null}

          <section className="management-columns">
            <ResourcePanel title="Scenes">
              {canManage ? (
                <form className="management-form" onSubmit={(event) => void handleCreateScene(event)}>
                  <input className="text-input" name="scene_key" placeholder="scene-key" />
                  <input className="text-input" name="name" placeholder="Scene name" />
                  <input className="text-input" name="description" placeholder="Description" />
                  <button className="primary-button" type="submit" disabled={isBusy}>
                    Create scene
                  </button>
                </form>
              ) : null}
              <div className="resource-list">
                {scenes.map((scene) => (
                  <article className="resource-row" key={scene.id}>
                    <div>
                      <h3>{scene.name}</h3>
                      <p>{scene.scene_key} - {scene.is_active ? "Active" : "Inactive"}</p>
                    </div>
                    {canManage ? (
                      <form
                        className="inline-form"
                        onSubmit={(event) => void handleUpdateScene(event, scene)}
                      >
                        <input className="text-input" name="name" defaultValue={scene.name} />
                        <input
                          className="text-input"
                          name="description"
                          defaultValue={scene.description ?? ""}
                          placeholder="Description"
                        />
                        <label className="checkbox-label">
                          <input name="is_active" type="checkbox" defaultChecked={scene.is_active} />
                          Active
                        </label>
                        <button className="secondary-button" type="submit" disabled={isBusy}>
                          Save scene
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleDeactivateScene(scene)}
                        >
                          Deactivate scene
                        </button>
                      </form>
                    ) : null}
                  </article>
                ))}
              </div>
            </ResourcePanel>

            <ResourcePanel title="Agents">
              {canManage ? (
                <form className="management-form" onSubmit={(event) => void handleCreateAgent(event)}>
                  <input className="text-input" name="agent_key" placeholder="agent-key" />
                  <input className="text-input" name="display_name" placeholder="Display name" />
                  <select className="text-input" name="kind" defaultValue="role_agent">
                    <option value="role_agent">role_agent</option>
                    <option value="narrative_agent">narrative_agent</option>
                  </select>
                  <select className="text-input" name="home_scene_id" defaultValue="">
                    <option value="">No home scene</option>
                    {scenes.map((scene) => (
                      <option key={scene.id} value={scene.id}>
                        {scene.name}
                      </option>
                    ))}
                  </select>
                  <textarea className="text-input" name="config" placeholder="{}" rows={3} />
                  <button className="primary-button" type="submit" disabled={isBusy}>
                    Create agent
                  </button>
                </form>
              ) : null}
              <div className="resource-list">
                {agents.map((agent) => (
                  <article className="resource-row" key={agent.id}>
                    <div>
                      <h3>{agent.display_name}</h3>
                      <p>{agent.agent_key} - {agent.kind} - {agent.is_enabled ? "Enabled" : "Disabled"}</p>
                    </div>
                    {canManage ? (
                      <form
                        className="inline-form"
                        onSubmit={(event) => void handleUpdateAgent(event, agent)}
                      >
                        <input
                          className="text-input"
                          name="display_name"
                          defaultValue={agent.display_name}
                        />
                        <select className="text-input" name="home_scene_id" defaultValue={agent.home_scene_id ?? ""}>
                          <option value="">No home scene</option>
                          {scenes.map((scene) => (
                            <option key={scene.id} value={scene.id}>
                              {scene.name}
                            </option>
                          ))}
                        </select>
                        <textarea
                          className="text-input"
                          name="config"
                          defaultValue={dashboardJsonString(agent.config)}
                          rows={3}
                        />
                        <label className="checkbox-label">
                          <input name="is_enabled" type="checkbox" defaultChecked={agent.is_enabled} />
                          Enabled
                        </label>
                        <button className="secondary-button" type="submit" disabled={isBusy}>
                          Save agent
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleDeactivateAgent(agent)}
                        >
                          Deactivate agent
                        </button>
                      </form>
                    ) : null}
                  </article>
                ))}
              </div>
            </ResourcePanel>
          </section>

          {canManage ? (
            <section className="management-panel" aria-label="World memberships">
              <h2 className="section-title">Members</h2>
              <form className="management-form" onSubmit={(event) => void handleSearchMembers(event)}>
                <input className="text-input" name="query" placeholder="Search email or display name" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Search users
                </button>
              </form>
              <div className="resource-list">
                {memberships.map((membership) => (
                  <article className="resource-row" key={membership.id}>
                    <div>
                      <h3>{membership.user.display_name}</h3>
                      <p>{membership.user.email} - {membership.role}</p>
                    </div>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={isBusy}
                      onClick={() => void handleDeleteMembership(membership)}
                    >
                      Remove member
                    </button>
                  </article>
                ))}
              </div>
              {memberCandidates.length > 0 ? (
                <div className="resource-list" aria-label="Member candidates">
                  {memberCandidates.map((candidate) => (
                    <article className="resource-row" key={candidate.id}>
                      <div>
                        <h3>{candidate.display_name}</h3>
                        <p>{candidate.email} - {candidate.role ?? "not a member"}</p>
                      </div>
                      <div className="button-row">
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleUpsertMembership(candidate, "human_user")}
                        >
                          Set human user
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleUpsertMembership(candidate, "world_admin")}
                        >
                          Set world admin
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null}
        </>
      )}
    </section>
  );
}

async function listWorldDiagnosticsIfAllowed(worldId: string): Promise<RuntimeDiagnostic[] | null> {
  try {
    return await listWorldDiagnostics(worldId);
  } catch (error) {
    if (
      error instanceof WorldClientError
      && (error.status === 403 || error.status === 404)
    ) {
      return null;
    }
    throw error;
  }
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

function ResourcePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="management-panel">
      <h2 className="section-title">{title}</h2>
      {children}
    </section>
  );
}

function ClockPanel({
  clock,
  canManage,
  isBusy,
  onPause,
  onResume,
  onAdvance,
  onSkip,
}: {
  clock: WorldClock | null;
  canManage: boolean;
  isBusy: boolean;
  onPause: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onResume: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onAdvance: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onSkip: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="World clock">
      <h2 className="section-title">World clock</h2>
      {clock === null ? (
        <p className="status-detail">Clock state is not available.</p>
      ) : (
        <>
          <div className="clock-grid">
            <Metric label="Clock" value={clock.status} />
            <Metric label="Speed" value={`${clock.speed_multiplier}x`} />
            <Metric label="Revision" value={String(clock.revision)} />
          </div>
          <p className="status-detail">
            World time {formatDateTime(clock.effective_world_time)}
          </p>
          <p className="status-detail">
            Anchor {clock.wall_time_anchor === null ? "Paused" : formatDateTime(clock.wall_time_anchor)}
          </p>
        </>
      )}
      {canManage ? (
        <div className="clock-actions">
          <form className="inline-form" onSubmit={(event) => void onPause(event)}>
            <input className="text-input" name="reason" placeholder="Pause reason" />
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Pause clock
            </button>
          </form>
          <form className="inline-form" onSubmit={(event) => void onResume(event)}>
            <input className="text-input" name="speed_multiplier" placeholder="Speed multiplier" />
            <input className="text-input" name="reason" placeholder="Resume reason" />
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Resume clock
            </button>
          </form>
          <form className="inline-form" onSubmit={(event) => void onAdvance(event)}>
            <input className="text-input" name="reason" placeholder="Advance reason" />
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Advance clock
            </button>
          </form>
          <form className="inline-form" onSubmit={(event) => void onSkip(event)}>
            <input
              className="text-input"
              name="target_world_time"
              placeholder="2030-01-01T00:00:00Z"
            />
            <input className="text-input" name="reason" placeholder="Skip reason" />
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Skip clock
            </button>
          </form>
        </div>
      ) : null}
    </section>
  );
}

function ReplayPanel({
  replayState,
  latestSnapshot,
  canManage,
  isBusy,
  onRefresh,
  onCreateSnapshot,
}: {
  replayState: WorldReplayState | null;
  latestSnapshot: WorldSnapshot | null;
  canManage: boolean;
  isBusy: boolean;
  onRefresh: () => void | Promise<void>;
  onCreateSnapshot: () => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Replay and snapshots">
      <h2 className="section-title">Replay and snapshots</h2>
      {replayState === null ? (
        <p className="status-detail">Replay state is not available.</p>
      ) : (
        <>
          <div className="clock-grid">
            <Metric label="Source sequence" value={String(replayState.source_sequence)} />
            <Metric label="Applied events" value={String(replayState.applied_event_count)} />
            <Metric label="Unhandled events" value={String(replayState.unhandled_event_count)} />
          </div>
          <p className="status-detail">
            Schema {replayState.schema_version}
          </p>
          <p className="status-detail">
            Clock{" "}
            {replayState.clock === null
              ? "No clock events"
              : `${replayState.clock.status} revision ${replayState.clock.revision ?? "unknown"}`}
          </p>
        </>
      )}
      {latestSnapshot === null ? (
        <p className="status-detail">No valid snapshot yet.</p>
      ) : (
        <p className="status-detail">
          Latest snapshot covers sequence {latestSnapshot.covers_event_sequence} as{" "}
          {latestSnapshot.schema_version} ({latestSnapshot.status}); payload{" "}
          {latestSnapshot.payload_location ?? "unknown"}
        </p>
      )}
      <div className="button-row">
        <button
          className="secondary-button"
          type="button"
          disabled={isBusy}
          onClick={() => void onRefresh()}
        >
          Refresh replay
        </button>
        {canManage ? (
          <button
            className="primary-button"
            type="button"
            disabled={isBusy}
            onClick={() => void onCreateSnapshot()}
          >
            Create snapshot
          </button>
        ) : null}
      </div>
    </section>
  );
}

function ScheduleRulesPanel({
  rules,
  canManage,
  isBusy,
  onCreate,
  onUpdate,
  onDisable,
}: {
  rules: ScheduleRule[];
  canManage: boolean;
  isBusy: boolean;
  onCreate: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onUpdate: (event: FormEvent<HTMLFormElement>, rule: ScheduleRule) => void | Promise<void>;
  onDisable: (rule: ScheduleRule) => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Schedule rules">
      <h2 className="section-title">Schedule rules</h2>
      {canManage ? (
        <form className="management-form" onSubmit={(event) => void onCreate(event)}>
          <input className="text-input" name="rule_key" placeholder="rule-key" />
          <input className="text-input" name="name" placeholder="Rule name" />
          <select className="text-input" name="kind" defaultValue="weekday">
            <option value="weekday">weekday</option>
            <option value="weekend">weekend</option>
            <option value="timetable">timetable</option>
          </select>
          <textarea className="text-input" name="config" placeholder='{"hours":[8]}' rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create schedule rule
          </button>
        </form>
      ) : null}
      <div className="resource-list">
        {rules.map((rule) => (
          <article className="resource-row" key={rule.id}>
            <div>
              <h3>{rule.name}</h3>
              <p>{rule.rule_key} - {rule.kind} - {rule.is_enabled ? "Enabled" : "Disabled"}</p>
            </div>
            {canManage ? (
              <form className="inline-form" onSubmit={(event) => void onUpdate(event, rule)}>
                <input className="text-input" name="name" defaultValue={rule.name} />
                <select className="text-input" name="kind" defaultValue={rule.kind}>
                  <option value="weekday">weekday</option>
                  <option value="weekend">weekend</option>
                  <option value="timetable">timetable</option>
                </select>
                <textarea
                  className="text-input"
                  name="config"
                  defaultValue={dashboardJsonString(rule.config)}
                  rows={3}
                />
                <label className="checkbox-label">
                  <input name="is_enabled" type="checkbox" defaultChecked={rule.is_enabled} />
                  Enabled
                </label>
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Save rule
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() => void onDisable(rule)}
                >
                  Disable rule
                </button>
              </form>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function CalendarPanel({
  agents,
  selectedAgent,
  entries,
  canManage,
  isBusy,
  onSelectAgent,
  onCreate,
  onUpdate,
  onCancel,
}: {
  agents: Agent[];
  selectedAgent: Agent | null;
  entries: CalendarEntry[];
  canManage: boolean;
  isBusy: boolean;
  onSelectAgent: (agentId: string) => void | Promise<void>;
  onCreate: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onUpdate: (event: FormEvent<HTMLFormElement>, entry: CalendarEntry) => void | Promise<void>;
  onCancel: (entry: CalendarEntry) => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Agent calendar">
      <h2 className="section-title">Agent calendar</h2>
      <select
        className="text-input"
        value={selectedAgent?.id ?? ""}
        onChange={(event) => void onSelectAgent(event.target.value)}
      >
        {agents.length === 0 ? <option value="">No agents</option> : null}
        {agents.map((agent) => (
          <option key={agent.id} value={agent.id}>
            {agent.display_name}
          </option>
        ))}
      </select>
      {canManage && selectedAgent !== null ? (
        <form className="management-form" onSubmit={(event) => void onCreate(event)}>
          <input className="text-input" name="title" placeholder="Calendar title" />
          <input className="text-input" name="starts_at" placeholder="Calendar start" />
          <input className="text-input" name="ends_at" placeholder="Calendar end" />
          <input className="text-input" name="description" placeholder="Description" />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create calendar entry
          </button>
        </form>
      ) : null}
      <div className="resource-list">
        {entries.map((entry) => (
          <article className="resource-row" key={entry.id}>
            <div>
              <h3>{entry.title}</h3>
              <p>{formatDateTime(entry.starts_at)} - {entry.status}</p>
            </div>
            {canManage ? (
              <form className="inline-form" onSubmit={(event) => void onUpdate(event, entry)}>
                <input className="text-input" name="title" defaultValue={entry.title} />
                <input className="text-input" name="starts_at" defaultValue={entry.starts_at} />
                <input className="text-input" name="ends_at" defaultValue={entry.ends_at ?? ""} />
                <input
                  className="text-input"
                  name="description"
                  defaultValue={entry.description ?? ""}
                />
                <select className="text-input" name="status" defaultValue={entry.status}>
                  <option value="active">active</option>
                  <option value="cancelled">cancelled</option>
                </select>
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Save calendar entry
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() => void onCancel(entry)}
                >
                  Cancel calendar entry
                </button>
              </form>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function MemoryPanel({
  agents,
  selectedAgent,
  items,
  isBusy,
  onSelectAgent,
  onSearch,
  onRefresh,
}: {
  agents: Agent[];
  selectedAgent: Agent | null;
  items: MemoryItem[];
  isBusy: boolean;
  onSelectAgent: (agentId: string) => void | Promise<void>;
  onSearch: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Agent memory">
      <h2 className="section-title">Agent memory</h2>
      <select
        className="text-input"
        value={selectedAgent?.id ?? ""}
        onChange={(event) => void onSelectAgent(event.target.value)}
      >
        {agents.length === 0 ? <option value="">No agents</option> : null}
        {agents.map((agent) => (
          <option key={agent.id} value={agent.id}>
            {agent.display_name}
          </option>
        ))}
      </select>
      {selectedAgent !== null ? (
        <>
          <p className="status-detail">
            Long-term memory is runtime-managed. Manual add and disable are not available.
          </p>
          <form className="management-form" onSubmit={(event) => void onSearch(event)}>
            <textarea className="text-input" name="query_text" placeholder="Search memory text" rows={3} />
            <input className="text-input" name="limit" placeholder="10" />
            <div className="button-row">
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Search memory
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => void onRefresh()}
              >
                Refresh memory
              </button>
            </div>
          </form>
        </>
      ) : (
        <p className="status-detail">Select an agent to inspect long-term memory.</p>
      )}
      <div className="resource-list">
        {items.map((item) => (
          <article className="resource-row" key={item.id}>
            <div>
              <h3>{item.content}</h3>
              <p>{memoryItemDetail(item)}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RuntimeControlPanel({
  runtimeControl,
  runtimeStatus,
  diagnostics,
  isBusy,
  onStart,
  onStop,
  onRefresh,
}: {
  runtimeControl: RuntimeControl | null;
  runtimeStatus: RuntimeStatus | null;
  diagnostics: RuntimeDiagnostic[];
  isBusy: boolean;
  onStart: () => void | Promise<void>;
  onStop: () => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Runtime control">
      <h2 className="section-title">Runtime control</h2>
      {runtimeControl === null || runtimeStatus === null ? (
        <p className="status-detail">Runtime control is not available.</p>
      ) : (
        <>
          <div className="clock-grid">
            <Metric label="Desired state" value={runtimeControl.desired_state} />
            <Metric label="Loop interval" value={`${runtimeStatus.runtime_loop_interval_seconds}s`} />
            <Metric label="Batch limit" value={String(runtimeStatus.runtime_batch_limit)} />
          </div>
          <p className="status-detail">
            Last heartbeat{" "}
            {runtimeControl.last_heartbeat_at === null
              ? "never"
              : formatDateTime(runtimeControl.last_heartbeat_at)}
          </p>
          <p className="status-detail">
            Last error {dashboardOptionalText(runtimeControl.last_error) ?? "none"}
          </p>
        </>
      )}
      <div className="button-row">
        <button className="secondary-button" type="button" disabled={isBusy} onClick={() => void onRefresh()}>
          Refresh runtime
        </button>
        <button className="primary-button" type="button" disabled={isBusy} onClick={() => void onStart()}>
          Start runtime
        </button>
        <button className="secondary-button" type="button" disabled={isBusy} onClick={() => void onStop()}>
          Stop runtime
        </button>
      </div>
      <div aria-label="Runtime diagnostics">
        <h3>Runtime diagnostics</h3>
        <DiagnosticList diagnostics={diagnostics} />
      </div>
    </section>
  );
}

function DiagnosticsPanel({
  title,
  diagnostics,
}: {
  title: string;
  diagnostics: RuntimeDiagnostic[];
}) {
  return (
    <section className="management-panel" aria-label={title}>
      <h2 className="section-title">{title}</h2>
      <DiagnosticList diagnostics={diagnostics} />
    </section>
  );
}

function DiagnosticList({ diagnostics }: { diagnostics: RuntimeDiagnostic[] }) {
  if (diagnostics.length === 0) {
    return <p className="status-detail">No diagnostics recorded.</p>;
  }
  return (
    <div className="resource-list">
      {diagnostics.slice(0, 8).map((diagnostic) => (
        <article className="resource-row" key={diagnostic.id}>
          <div>
            <h3>{dashboardText(diagnostic.message)}</h3>
            <p>
              {dashboardText(diagnostic.severity)} - {dashboardText(diagnostic.component)} -{" "}
              {dashboardText(diagnostic.event_type)}
            </p>
            <p className="status-detail">{formatDateTime(diagnostic.occurred_at)}</p>
          </div>
          <p className="status-detail">{diagnostic.agent_id ?? diagnostic.run_id ?? "runtime"}</p>
        </article>
      ))}
    </div>
  );
}

function ProviderProfilesPanel({
  profiles,
  isBusy,
  onCreate,
  onUpdate,
  onDisable,
  onTest,
}: {
  profiles: ProviderProfile[];
  isBusy: boolean;
  onCreate: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onUpdate: (event: FormEvent<HTMLFormElement>, profile: ProviderProfile) => void | Promise<void>;
  onDisable: (profile: ProviderProfile) => void | Promise<void>;
  onTest: (event: FormEvent<HTMLFormElement>, profile: ProviderProfile) => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Provider profiles">
      <h2 className="section-title">Provider profiles</h2>
      <form className="management-form" onSubmit={(event) => void onCreate(event)}>
        <input className="text-input" name="profile_key" placeholder="profile-key" />
        <input className="text-input" name="name" placeholder="Profile name" />
        <select className="text-input" name="provider_type" defaultValue="openai_compatible">
          <option value="openai_compatible">openai_compatible</option>
          <option value="anthropic_compatible">anthropic_compatible</option>
        </select>
        <input className="text-input" name="base_url" placeholder="https://api.example.test/v1" />
        <input className="text-input" name="model_name" placeholder="Model name" />
        <input className="text-input" name="api_key_ref" placeholder="api-key-ref" />
        <input className="text-input" name="timeout_seconds" placeholder="Timeout seconds" />
        <input className="text-input" name="retry_attempts" placeholder="Retry attempts" />
        <input className="text-input" name="rate_limit_per_minute" placeholder="Rate limit per minute" />
        <textarea className="text-input" name="capabilities" placeholder="{}" rows={3} />
        <button className="primary-button" type="submit" disabled={isBusy}>
          Create provider profile
        </button>
      </form>
      <div className="resource-list">
        {profiles.map((profile) => {
          const lastTestError = dashboardOptionalText(profile.last_test_error);

          return (
            <article className="resource-row" key={profile.id}>
              <div>
                <h3>{profile.name}</h3>
                <p>
                  {profile.profile_key} - {profile.provider_type} - {profile.model_name} -{" "}
                  {profile.is_enabled ? "Enabled" : "Disabled"}
                </p>
                <p className="status-detail">
                  Timeout {profile.timeout_seconds}s - retries {profile.retry_attempts} - rate{" "}
                  {profile.rate_limit_per_minute ?? "unlimited"}/min
                </p>
                <p className="status-detail">
                  Last test{" "}
                  {profile.last_test_status === null
                    ? "never"
                    : `${profile.last_test_status} at ${optionalDateTime(profile.last_tested_at)}`}
                  {lastTestError === null ? "" : ` - ${lastTestError}`}
                </p>
              </div>
              <form className="inline-form" onSubmit={(event) => void onUpdate(event, profile)}>
                <input className="text-input" name="name" defaultValue={profile.name} />
                <input className="text-input" name="base_url" defaultValue={profile.base_url} />
                <input className="text-input" name="model_name" defaultValue={profile.model_name} />
                <input className="text-input" name="api_key_ref" defaultValue={profile.api_key_ref} />
                <input
                  className="text-input"
                  name="timeout_seconds"
                  defaultValue={String(profile.timeout_seconds)}
                />
                <input
                  className="text-input"
                  name="retry_attempts"
                  defaultValue={String(profile.retry_attempts)}
                />
                <input
                  className="text-input"
                  name="rate_limit_per_minute"
                  defaultValue={profile.rate_limit_per_minute ?? ""}
                  placeholder="Rate limit per minute"
                />
                <textarea
                  className="text-input"
                  name="capabilities"
                  defaultValue={dashboardJsonString(profile.capabilities)}
                  rows={3}
                />
                <label className="checkbox-label">
                  <input name="is_enabled" type="checkbox" defaultChecked={profile.is_enabled} />
                  Enabled
                </label>
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Save profile
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() => void onDisable(profile)}
                >
                  Disable profile
                </button>
              </form>
              <form className="inline-form" onSubmit={(event) => void onTest(event, profile)}>
                <input className="text-input" name="prompt" placeholder="Reply with OK." />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Test provider
                </button>
              </form>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function AgentPersonaObservationsPanel({
  agents,
  selectedAgent,
  persona,
  observations,
  canManage,
  isBusy,
  onSelectAgent,
  onUpdatePersona,
  onCreateObservation,
  onRefreshObservations,
}: {
  agents: Agent[];
  selectedAgent: Agent | null;
  persona: AgentPersona | null;
  observations: AgentObservation[];
  canManage: boolean;
  isBusy: boolean;
  onSelectAgent: (agentId: string) => void | Promise<void>;
  onUpdatePersona: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onCreateObservation: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onRefreshObservations: () => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Agent persona and observations">
      <h2 className="section-title">Agent persona and observations</h2>
      <select
        className="text-input"
        value={selectedAgent?.id ?? ""}
        onChange={(event) => void onSelectAgent(event.target.value)}
      >
        {agents.length === 0 ? <option value="">No agents</option> : null}
        {agents.map((agent) => (
          <option key={agent.id} value={agent.id}>
            {agent.display_name}
          </option>
        ))}
      </select>
      {canManage && selectedAgent !== null ? (
        <>
          <form className="management-form" onSubmit={(event) => void onUpdatePersona(event)}>
            <textarea
              className="text-input"
              name="persona_text"
              placeholder="Persona text"
              defaultValue={persona?.persona_text ?? ""}
              rows={4}
            />
            <textarea
              className="text-input"
              name="behavior_policy"
              placeholder="{}"
              defaultValue={dashboardJsonString(persona?.behavior_policy ?? {})}
              rows={3}
            />
            <label className="checkbox-label">
              <input name="is_enabled" type="checkbox" defaultChecked={persona?.is_enabled ?? true} />
              Persona enabled
            </label>
            <button className="primary-button" type="submit" disabled={isBusy}>
              Save persona
            </button>
          </form>
          <form className="management-form" onSubmit={(event) => void onCreateObservation(event)}>
            <input className="text-input" name="observation_type" placeholder="manual" />
            <textarea className="text-input" name="content" placeholder="Observation" rows={3} />
            <textarea className="text-input" name="metadata" placeholder="{}" rows={3} />
            <input className="text-input" name="observed_at" placeholder="Observed at" />
            <div className="button-row">
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Add observation
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => void onRefreshObservations()}
              >
                Refresh observations
              </button>
            </div>
          </form>
        </>
      ) : (
        <p className="status-detail">Persona and observation management requires world admin access.</p>
      )}
      <div className="resource-list">
        {observations.map((observation) => (
          <article className="resource-row" key={observation.id}>
            <div>
              <h3>{observation.observation_type}</h3>
              <p>{observation.content}</p>
              <p className="status-detail">{formatDateTime(observation.observed_at)}</p>
              <p className="status-detail">
                {observation.review_status} - used {observation.runtime_use_count}
              </p>
            </div>
            <p className="status-detail">
              {observation.last_used_run_id ?? observation.source_event_id ?? "manual"}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function AgentRunsPanel({
  agents,
  selectedAgent,
  runs,
  providerProfiles,
  canManage,
  isBusy,
  onSelectAgent,
  onRun,
}: {
  agents: Agent[];
  selectedAgent: Agent | null;
  runs: AgentRun[];
  providerProfiles: ProviderProfile[];
  canManage: boolean;
  isBusy: boolean;
  onSelectAgent: (agentId: string) => void | Promise<void>;
  onRun: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Agent runs">
      <h2 className="section-title">Agent runs</h2>
      <select
        className="text-input"
        value={selectedAgent?.id ?? ""}
        onChange={(event) => void onSelectAgent(event.target.value)}
      >
        {agents.length === 0 ? <option value="">No agents</option> : null}
        {agents.map((agent) => (
          <option key={agent.id} value={agent.id}>
            {agent.display_name}
          </option>
        ))}
      </select>
      {canManage && selectedAgent !== null ? (
        <form className="management-form" onSubmit={(event) => void onRun(event)}>
          <textarea className="text-input" name="prompt" placeholder="Manual run prompt" rows={3} />
          <select className="text-input" name="provider_profile_id" defaultValue="">
            <option value="">Use default enabled profile</option>
            {providerProfiles
              .filter((profile) => profile.is_enabled)
              .map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                </option>
              ))}
          </select>
          <label className="checkbox-label">
            <input name="create_memory" type="checkbox" defaultChecked />
            Create memory
          </label>
          <label className="checkbox-label">
            <input name="create_narrative_artifact" type="checkbox" defaultChecked />
            Create narrative artifact
          </label>
          <button className="primary-button" type="submit" disabled={isBusy}>
            Run agent
          </button>
        </form>
      ) : null}
      <div className="resource-list">
        {runs.map((run) => (
          <article className="resource-row" key={run.run_id}>
            <div>
              <h3>{run.status}</h3>
              <p>{formatDateTime(run.started_at)}</p>
              <p className="status-detail">
                Persona {String(run.diagnostics.persona_enabled ?? false)} - observations{" "}
                {String(run.diagnostics.observation_count ?? 0)}
              </p>
              <p>{run.response_text ?? run.prompt_text}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function NarrativeArtifactsPanel({
  agents,
  artifacts,
  canManage,
  isBusy,
  onCreate,
}: {
  agents: Agent[];
  artifacts: NarrativeArtifact[];
  canManage: boolean;
  isBusy: boolean;
  onCreate: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
}) {
  return (
    <section className="management-panel" aria-label="Narrative artifacts">
      <h2 className="section-title">Narrative artifacts</h2>
      {canManage ? (
        <form className="management-form" onSubmit={(event) => void onCreate(event)}>
          <input className="text-input" name="title" placeholder="Artifact title" />
          <textarea className="text-input" name="content" placeholder="Artifact content" rows={4} />
          <select className="text-input" name="artifact_kind" defaultValue="world_summary">
            <option value="world_summary">world_summary</option>
            <option value="agent_note">agent_note</option>
          </select>
          <select className="text-input" name="agent_id" defaultValue="">
            <option value="">No agent</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.display_name}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create narrative artifact
          </button>
        </form>
      ) : null}
      <div className="resource-list">
        {artifacts.map((artifact) => (
          <article className="resource-row" key={artifact.id}>
            <div>
              <h3>{artifact.title}</h3>
              <p>{artifact.artifact_kind} - {formatDateTime(artifact.created_at)}</p>
              <p>{artifact.content}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

async function listMembershipsIfAllowed(worldId: string): Promise<Membership[] | null> {
  try {
    return await listMemberships(worldId);
  } catch (error) {
    if (error instanceof WorldClientError && (error.status === 403 || error.status === 404)) {
      return null;
    }
    throw error;
  }
}

function formString(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function optionalFormString(form: FormData, key: string): string | null {
  const value = formString(form, key);
  return value === "" ? null : value;
}

function numberFormValue(form: FormData, key: string, fallback: number): number {
  const value = formString(form, key);
  if (value === "") {
    return fallback;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${key} must be a number.`);
  }
  return parsed;
}

function optionalNumberFormValue(form: FormData, key: string): number | null {
  const value = formString(form, key);
  if (value === "") {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${key} must be a number.`);
  }
  return parsed;
}

function dashboardJsonString(value: Record<string, unknown>): string {
  return JSON.stringify(sanitizeDashboardJsonForDisplay(value));
}

function dashboardJsonObject(rawValue: string): Record<string, unknown> {
  return sanitizeDashboardJsonForDisplay(jsonObject(rawValue));
}

function sanitizeDashboardJsonForDisplay(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !sensitiveDashboardJsonKey(key))
      .map(([key, entry]) => [key, sanitizeDashboardJsonValue(entry)]),
  );
}

function dashboardText(value: string): string {
  return looksSensitiveDashboardString(value) ? "[redacted]" : value;
}

function dashboardOptionalText(value: string | null): string | null {
  return value === null ? null : dashboardText(value);
}

function sanitizeDashboardJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeDashboardJsonValue(entry));
  }
  if (value !== null && typeof value === "object") {
    return sanitizeDashboardJsonForDisplay(value as Record<string, unknown>);
  }
  if (typeof value === "string" && looksSensitiveDashboardString(value)) {
    return "[redacted]";
  }
  return value;
}

const EXACT_SENSITIVE_DASHBOARD_JSON_KEYS = new Set([
  "apikey",
  "authorization",
  "base64",
  "bearertoken",
  "bytes",
  "password",
  "secret",
  "token",
]);

const SENSITIVE_DASHBOARD_JSON_KEY_MARKERS = [
  "accesstoken",
  "bearertoken",
  "clientsecret",
  "filesystempath",
  "filepath",
  "localmodelpath",
  "objectpath",
  "objectstoragepath",
  "privatekey",
  "promptsnapshot",
  "promptsnapshotid",
  "rawbytes",
  "rawoutput",
  "rawprompt",
  "refreshtoken",
  "secretkey",
  "storagepath",
  "storageuri",
  "storageurl",
];

function sensitiveDashboardJsonKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/[^a-z0-9]+/g, "");
  return (
    EXACT_SENSITIVE_DASHBOARD_JSON_KEYS.has(normalized) ||
    SENSITIVE_DASHBOARD_JSON_KEY_MARKERS.some((marker) => normalized.includes(marker))
  );
}

function looksSensitiveDashboardString(value: string): boolean {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "");
  return (
    SENSITIVE_DASHBOARD_JSON_KEY_MARKERS.some((marker) => normalized.includes(marker)) ||
    /media:\/\/|\/var\/|\/tmp\/|\/models\/|[A-Za-z]:\\|sk-[A-Za-z0-9_-]+|Bearer\s+\S+/i.test(value) ||
    containsBase64LikeDashboardToken(value)
  );
}

function containsBase64LikeDashboardToken(value: string): boolean {
  return value
    .split(/\s+/)
    .some((part) => {
      const normalized = part.replace(/[^A-Za-z0-9+/=]/g, "");
      return (
        normalized.length >= 16 &&
        normalized.length % 4 === 0 &&
        /^[A-Za-z0-9+/]+={0,2}$/.test(normalized) &&
        !/^[a-f0-9]{32,}$/i.test(normalized)
      );
    });
}

function jsonObject(rawValue: string): Record<string, unknown> {
  if (rawValue.trim() === "") {
    return {};
  }
  const parsed = JSON.parse(rawValue) as unknown;
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Config must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

function messageForError(error: unknown): string {
  if (error instanceof WorldClientError) {
    if (error.status === 409) {
      return error.message;
    }
    if (error.status === 403) {
      return "Forbidden";
    }
    if (error.status === 422) {
      return "Check the fields and try again.";
    }
    return error.message;
  }
  if (error instanceof SyntaxError || error instanceof Error) {
    return error.message;
  }
  return "World request failed.";
}

function formatDateTime(value: string): string {
  return new Date(value).toISOString();
}

function optionalDateTime(value: string | null): string {
  return value === null ? "unknown time" : formatDateTime(value);
}

function replaceById<T extends { id: string }>(items: T[], nextItem: T): T[] {
  return items.map((item) => (item.id === nextItem.id ? nextItem : item));
}

function upsertByUserId(items: Membership[], nextItem: Membership): Membership[] {
  const exists = items.some((item) => item.user_id === nextItem.user_id);
  if (!exists) {
    return [...items, nextItem].sort(compareMemberships);
  }
  return items
    .map((item) => (item.user_id === nextItem.user_id ? nextItem : item))
    .sort(compareMemberships);
}

function compareWorlds(left: World, right: World): number {
  return left.slug.localeCompare(right.slug);
}

function compareScenes(left: Scene, right: Scene): number {
  return left.scene_key.localeCompare(right.scene_key);
}

function compareAgents(left: Agent, right: Agent): number {
  return left.agent_key.localeCompare(right.agent_key);
}

function compareCalendarEntries(left: CalendarEntry, right: CalendarEntry): number {
  return left.starts_at.localeCompare(right.starts_at);
}

function compareScheduleRules(left: ScheduleRule, right: ScheduleRule): number {
  return left.rule_key.localeCompare(right.rule_key);
}

function compareProviderProfiles(left: ProviderProfile, right: ProviderProfile): number {
  return left.profile_key.localeCompare(right.profile_key);
}

function compareMemberships(left: Membership, right: Membership): number {
  return left.user.email.localeCompare(right.user.email);
}

function optionalNumber(value: string): number | undefined {
  if (value.trim() === "") {
    return undefined;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error("Limit must be a number.");
  }
  return parsed;
}

function memoryItemDetail(item: MemoryItem): string {
  const parts = [
    `backend ${item.backend}`,
    item.created_at === null ? "unknown time" : formatDateTime(item.created_at),
    item.score === null ? null : `score ${item.score.toFixed(2)}`,
    typeof item.metadata.turn_id === "string"
      ? `turn ${item.metadata.turn_id}`
      : typeof item.metadata.run_id === "string"
        ? `run ${item.metadata.run_id}`
        : typeof item.metadata.source_event_id === "string"
          ? `event ${item.metadata.source_event_id}`
          : typeof item.metadata.conversation_id === "string"
            ? `conversation ${item.metadata.conversation_id}`
            : null,
  ].filter((part): part is string => part !== null);
  return parts.join(" - ");
}

function worldQueryPath(worldId: string): string {
  return `/?world=${encodeURIComponent(worldId)}`;
}
