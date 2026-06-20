import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/realtime", async () => {
  const actual = await vi.importActual<typeof import("@/lib/realtime")>("@/lib/realtime");
  return {
    ...actual,
    subscribeToEventStream: vi.fn(() => undefined),
  };
});

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>(
    "@/lib/worlds/client",
  );
  return {
    ...actual,
    getCalendarConflicts: vi.fn(),
    getDailyLifePreview: vi.fn(),
    generateDailyLifeCandidates: vi.fn(),
    importWorldComposition: vi.fn(),
    updateWorld: vi.fn(),
    upsertWorldBible: vi.fn(),
    compareWorldlines: vi.fn(),
    createBetaChecklist: vi.fn(),
    createEndingCandidate: vi.fn(),
    createLongRunEval: vi.fn(),
    createRouteMilestone: vi.fn(),
    forkWorldline: vi.fn(),
    listOffscreenEvents: vi.fn(),
    listWorldEvents: vi.fn(),
    previewScheduleRule: vi.fn(),
    resolveOffscreenEvents: vi.fn(),
    upsertReleaseProfile: vi.fn(),
    validateWorldComposition: vi.fn(),
  };
});

import { WorldOverview } from "@/features/worlds/world-overview";
import { subscribeToEventStream } from "@/lib/realtime";
import {
  compareWorldlines,
  createBetaChecklist,
  createEndingCandidate,
  createLongRunEval,
  createRouteMilestone,
  forkWorldline,
  getCalendarConflicts,
  getDailyLifePreview,
  generateDailyLifeCandidates,
  importWorldComposition,
  updateWorld,
  upsertWorldBible,
  listOffscreenEvents,
  listWorldEvents,
  previewScheduleRule,
  resolveOffscreenEvents,
  upsertReleaseProfile,
  validateWorldComposition,
} from "@/lib/worlds/client";
import type { WorldWorkspaceData } from "@/lib/worlds/server";
import type { WorldEventAuditEntry } from "@/lib/worlds/types";

describe("WorldOverview", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("redacts sensitive world overview JSON and submit payloads", async () => {
    const dirtyData: WorldWorkspaceData = {
      ...workspaceData,
      selectedWorld: {
        ...workspaceData.selectedWorld!,
        rules_config: { safeRule: true, rawOutput: "rules output" },
        memory_plugin_config: {
          safeMemory: true,
          clientSecret: "sk-world-secret",
          nested: { storageUri: "media://world-secret" },
        },
        world_rules_plugin_config: {
          safeRules: true,
          bearerToken: "Bearer world-token",
          promptSnapshotId: "snapshot-world-rules",
        },
      },
      worldBible: {
        id: "world-bible-1",
        world_id: "world-1",
        source_material: "Safe source",
        canon_timeline: [{ year: 2030, event: "festival", rawPrompt: "system prompt" }],
        setting_rules: { genre: "school", filePath: "/tmp/world-bible.json" },
        forbidden_changes: [{ rule: "no retcon", storageUri: "media://forbidden-secret" }],
        sequel_boundaries: { route: "after ending", promptSnapshotId: "snapshot-bible" },
        continuity_config: { status: "post_canon", rawOutput: "model output" },
        continuity_status: "post_canon",
        metadata: { safeMeta: true, bytes: "YWJjZGVmZ2hpamtsbW5vcA==" },
        created_at: "2026-05-05T00:00:00.000Z",
        updated_at: "2026-05-05T00:00:00.000Z",
      },
      releaseProfile: {
        ...workspaceData.releaseProfile!,
        branch_policy: { branch_review: true, storageUri: "media://release-secret" },
        backup_policy: { snapshot_before_beta: true, rawPrompt: "backup prompt" },
        content_review_policy: { continuity_review_required: true, filePath: "/tmp/release.json" },
        player_permission_policy: { invite_only: true, bearerToken: "Bearer release-token" },
        worldline_policy: { forks_allowed: true, promptSnapshotId: "snapshot-release" },
        checklist: { sample_world_required: true, rawOutput: "checklist output" },
        metadata: { safeRelease: true, clientSecret: "sk-release-secret" },
      },
      worldEventAudit: [
        {
          ...eventRow("event-dirty", 9, "agent.run_failed"),
          payload: { safe: "visible", rawPrompt: "event prompt", storageUri: "media://event-secret" },
        },
      ],
    };
    vi.mocked(updateWorld).mockResolvedValue(dirtyData.selectedWorld!);
    vi.mocked(upsertWorldBible).mockResolvedValue(dirtyData.worldBible!);
    vi.mocked(upsertReleaseProfile).mockResolvedValue(dirtyData.releaseProfile!);
    vi.mocked(validateWorldComposition).mockResolvedValue({
      valid: true,
      blocking_issue_count: 0,
      warning_issue_count: 0,
      issues: [],
    });
    vi.mocked(importWorldComposition).mockResolvedValue(dirtyData.selectedWorld!);

    render(<WorldOverview data={dirtyData} />);

    expect(screen.getByDisplayValue(/safeMemory/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/safeRules/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/festival/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/safeRelease/)).toBeInTheDocument();
    expect(document.body.textContent).toContain("safe");
    expect(document.body.textContent).not.toMatch(/rawPrompt|media:\/\/event-secret/i);
    expect(
      screen.queryAllByDisplayValue(
        /clientSecret|sk-world-secret|storageUri|media:\/\/world-secret|bearerToken|Bearer world-token|promptSnapshotId|snapshot-world-rules|rawPrompt|filePath|\/tmp\/world-bible|media:\/\/forbidden-secret|snapshot-bible|rawOutput|bytes|YWJjZGVmZ2hpamtsbW5vcA|media:\/\/release-secret|Bearer release-token|snapshot-release|sk-release-secret/i,
      ),
    ).toHaveLength(0);

    fireEvent.submit(formForButton("Save world"));
    await waitFor(() => {
      expect(updateWorld).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          memory_plugin_config: { safeMemory: true, nested: {} },
          world_rules_plugin_config: { safeRules: true },
        }),
      );
    });
    expect(JSON.stringify(vi.mocked(updateWorld).mock.calls[0][1])).not.toMatch(
      /clientSecret|sk-world-secret|storageUri|media:\/\/world-secret|bearerToken|Bearer world-token|promptSnapshotId/i,
    );

    fireEvent.submit(formForButton("Save world bible"));
    await waitFor(() => {
      expect(upsertWorldBible).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          canon_timeline: [expect.objectContaining({ year: 2030, event: "festival" })],
          setting_rules: { genre: "school" },
          metadata: { safeMeta: true },
        }),
      );
    });
    expect(JSON.stringify(vi.mocked(upsertWorldBible).mock.calls[0][1])).not.toMatch(
      /rawPrompt|filePath|\/tmp\/world-bible|storageUri|media:\/\/forbidden-secret|promptSnapshotId|snapshot-bible|rawOutput|bytes|YWJjZGVmZ2hpamtsbW5vcA/i,
    );

    fireEvent.submit(formForHeading("Release profile"));
    await waitFor(() => {
      expect(upsertReleaseProfile).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          branch_policy: { branch_review: true },
          backup_policy: { snapshot_before_beta: true },
          metadata: { safeRelease: true },
        }),
      );
    });
    expect(JSON.stringify(vi.mocked(upsertReleaseProfile).mock.calls[0][1])).not.toMatch(
      /storageUri|media:\/\/release-secret|rawPrompt|filePath|\/tmp\/release|bearerToken|Bearer release-token|promptSnapshotId|snapshot-release|rawOutput|clientSecret|sk-release-secret/i,
    );

    const validateForm = formForButton("Validate composition");
    setFormValue(validateForm, "slug", "validated-world");
    setFormValue(validateForm, "name", "Validated World");
    setFormValue(validateForm, "rules_config", JSON.stringify({ safeRule: true, storageUri: "media://validate-secret" }));
    setFormValue(validateForm, "composition", JSON.stringify(compositionExport));
    fireEvent.submit(validateForm);
    await waitFor(() => {
      expect(validateWorldComposition).toHaveBeenCalledWith(
        expect.objectContaining({ rules_config: { safeRule: true } }),
      );
    });
    expect(JSON.stringify(vi.mocked(validateWorldComposition).mock.calls[0][0])).not.toMatch(
      /storageUri|media:\/\/validate-secret/i,
    );

    const importForm = formForButton("Import as new world");
    setFormValue(importForm, "slug", "imported-world");
    setFormValue(importForm, "name", "Imported World");
    setFormValue(importForm, "rules_config", JSON.stringify({ safeImport: true, rawPrompt: "import prompt" }));
    setFormValue(importForm, "composition", JSON.stringify(compositionExport));
    fireEvent.submit(importForm);
    await waitFor(() => {
      expect(importWorldComposition).toHaveBeenCalledWith(
        expect.objectContaining({ rules_config: { safeImport: true } }),
      );
    });
    expect(JSON.stringify(vi.mocked(importWorldComposition).mock.calls[0][0])).not.toMatch(/rawPrompt|import prompt/i);
  }, 180000);

  it("renders and filters world event audit rows for world admins", async () => {
    vi.mocked(listWorldEvents).mockResolvedValue([eventRow("event-2", 2, "agent.run_failed")]);
    vi.mocked(getCalendarConflicts).mockResolvedValue({
      world_id: "world-1",
      start_world_time: "2030-01-01T00:00:00.000Z",
      horizon_hours: 168,
      conflict_count: 1,
      conflicts: [
        {
          conflict_type: "calendar_entry_overlap",
          world_id: "world-1",
          agent_id: "agent-1",
          starts_at: "2030-01-01T08:00:00.000Z",
          ends_at: "2030-01-01T09:00:00.000Z",
          reason: "calendar entries overlap for the same agent",
          sources: [
            {
              source_kind: "calendar_entry",
              source_id: "entry-1",
              agent_id: "agent-1",
              label: "Briefing",
            },
            {
              source_kind: "calendar_entry",
              source_id: "entry-2",
              agent_id: "agent-1",
              label: "Debrief",
            },
          ],
        },
      ],
    });
    vi.mocked(previewScheduleRule).mockResolvedValue({
      world_id: "world-1",
      kind: "timetable",
      config: { hours: [8] },
      start_world_time: "2030-01-01T07:00:00.000Z",
      horizon_hours: 4,
      match_count: 1,
      affected_agent_count: 1,
      affected_agent_ids: ["agent-1"],
      matches: [
        {
          world_time: "2030-01-01T08:00:00.000Z",
          reason: "hour 8",
          affected_agent_count: 1,
          affected_agent_ids: ["agent-1"],
        },
      ],
    });
    vi.mocked(getDailyLifePreview).mockResolvedValue({
      world_id: "world-1",
      start_world_time: "2030-01-01T08:00:00.000Z",
      horizon_hours: 12,
      candidate_count: 1,
      candidates: [
        {
          id: null,
          world_id: "world-1",
          agent_id: "agent-1",
          agent_display_name: "Guide",
          scene_id: "scene-1",
          scene_name: "Club room",
          title: "Guide daily life beat",
          summary: "Guide spends time at Club room.",
          importance: "daily",
          starts_at: "2030-01-01T08:00:00.000Z",
          source_kind: "daily_life_scheduler",
          source_ref: "agent-1",
          status: "candidate",
          metadata: {},
          created_at: null,
          updated_at: null,
        },
      ],
    });
    vi.mocked(generateDailyLifeCandidates).mockResolvedValue([
      {
        id: "candidate-1",
        world_id: "world-1",
        agent_id: "agent-1",
        agent_display_name: "Guide",
        scene_id: "scene-1",
        scene_name: "Club room",
        title: "Guide daily life beat",
        summary: "Guide spends time at Club room.",
        importance: "daily",
        starts_at: "2030-01-01T08:00:00.000Z",
        source_kind: "daily_life_scheduler",
        source_ref: "agent-1",
        status: "candidate",
        metadata: {},
        created_at: "2026-05-05T12:00:00.000Z",
        updated_at: "2026-05-05T12:00:00.000Z",
      },
    ]);
    vi.mocked(resolveOffscreenEvents).mockResolvedValue({
      processed_count: 1,
      resolved_count: 1,
      failed_count: 0,
      event_ids: ["event-3"],
    });
    vi.mocked(listOffscreenEvents).mockResolvedValue([
      {
        id: "queue-1",
        world_id: "world-1",
        source_candidate_id: "candidate-1",
        event_name: "living_world.daily_life",
        title: "Guide daily life beat",
        payload: {},
        due_at: "2030-01-01T08:00:00.000Z",
        importance: "daily",
        status: "resolved",
        resolved_event_id: "event-3",
        last_error: null,
        created_at: "2026-05-05T12:00:00.000Z",
        updated_at: "2026-05-05T12:00:00.000Z",
      },
    ]);
    vi.mocked(validateWorldComposition).mockResolvedValue({
      valid: false,
      blocking_issue_count: 1,
      warning_issue_count: 0,
      issues: [
        {
          severity: "blocking",
          code: "missing_preset",
          field: "composition.agents[0].source_preset_key",
          message: "Unknown agent preset: absent.",
        },
      ],
    });

    render(<WorldOverview data={workspaceData} />);

    expect(screen.getByRole("heading", { name: "Event audit" })).toBeInTheDocument();
    expect(screen.getByText("resume to revision 1")).toBeInTheDocument();
    expect(screen.getByText("Reconstructed clock")).toBeInTheDocument();
    expect(screen.getByText("Snapshot integrity")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Calendar conflicts" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Living world autonomy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Organizations and faction tracks" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Daily life and offscreen queue" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Plot, route, and rumor flow" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Knowledge, player, and guardrails" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Beta release readiness" })).toBeInTheDocument();
    expect(screen.getByText("classroom to courtyard")).toBeInTheDocument();
    expect(screen.getByText("Student Council (club)")).toBeInTheDocument();
    expect(screen.getByText("Guide presence")).toBeInTheDocument();
    expect(screen.getByText("Festival promise")).toBeInTheDocument();
    expect(screen.getAllByText("Festival route").length).toBeGreaterThan(0);
    expect(screen.getAllByText("guide-route").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Late rehearsal rumor").length).toBeGreaterThan(0);
    expect(screen.getByText("rival-route-note")).toBeInTheDocument();
    expect(screen.getByText("Hidden letter")).toBeInTheDocument();
    expect(screen.getByText(/restless - stress 40/)).toBeInTheDocument();
    expect(screen.getByText("Late rehearsal journal")).toBeInTheDocument();
    expect(screen.getByText("Club room notice")).toBeInTheDocument();
    expect(screen.getByText("GM style: warning")).toBeInTheDocument();
    expect(screen.getByText("Continuity: warning")).toBeInTheDocument();
    expect(screen.getByText("Festival confession lock")).toBeInTheDocument();
    expect(screen.getByText("Guide normal ending")).toBeInTheDocument();
    expect(screen.getByText("seven-day-beta-eval")).toBeInTheDocument();
    expect(screen.getByText("Sequel world bundle")).toBeInTheDocument();
    expect(screen.getByText(/Gate ready - allowed - blockers 0 - warnings 0 - evidence refs 1/)).toBeInTheDocument();
    expect(screen.getByText(/Preview diff characters 1, events 1, routes 1/)).toBeInTheDocument();
    expect(screen.getByText(/day coverage 7 - trace refs 2 - snapshot refs 1/)).toBeInTheDocument();
    expect(screen.getByText("sample-world-beta")).toBeInTheDocument();
    expect(screen.getByText("7-day simulation")).toBeInTheDocument();
    expect(screen.getAllByText("Evidence refs 1").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Gap 0")).toBeInTheDocument();
    expect(screen.getByText(/agent.run_succeeded/)).toBeInTheDocument();
    expect(screen.getByText('{"output":"ok"}')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("event.name"), {
      target: { value: "agent.run_failed" },
    });
    fireEvent.change(screen.getByPlaceholderText("actor:ref"), {
      target: { value: "agent:guide" },
    });
    clickButton("Filter events");

    await waitFor(() => {
      expect(screen.getByText(/agent.run_failed/)).toBeInTheDocument();
    });
    expect(listWorldEvents).toHaveBeenCalledWith(
      "world-1",
      expect.objectContaining({
        event_name: "agent.run_failed",
        actor_ref: "agent:guide",
        limit: 10,
      }),
    );

    clickButton("Preview schedule");

    await waitFor(() => {
      expect(screen.getByText("Preview matches 1 windows for 1 agents.")).toBeInTheDocument();
    });
    expect(screen.getByText("hour 8 - 1 agents")).toBeInTheDocument();

    clickButton("Check conflicts");

    await waitFor(() => {
      expect(screen.getByText(/calendar_entry_overlap/)).toBeInTheDocument();
    });
    expect(getCalendarConflicts).toHaveBeenCalledWith("world-1", {
      start_world_time: null,
      horizon_hours: 168,
      limit: 50,
    });

    clickButton("Preview daily life");

    await waitFor(() => {
      expect(screen.getByText("Guide daily life beat")).toBeInTheDocument();
    });
    expect(getDailyLifePreview).toHaveBeenCalledWith("world-1", {
      start_world_time: null,
      horizon_hours: 24,
      limit: 20,
    });

    clickButton("Generate candidates");

    await waitFor(() => {
      expect(generateDailyLifeCandidates).toHaveBeenCalledWith("world-1", {
        horizon_hours: 24,
        limit: 20,
      });
    });

    clickButton("Resolve due offscreen events");

    await waitFor(() => {
      expect(resolveOffscreenEvents).toHaveBeenCalledWith("world-1", 20);
    });

    fireEvent.change(screen.getByPlaceholderText("validate-world-slug"), {
      target: { value: "composition-import" },
    });
    fireEvent.change(screen.getByPlaceholderText("Validate world name"), {
      target: { value: "Composition Import" },
    });
    fireEvent.change(screen.getByPlaceholderText("Paste composition JSON to validate"), {
      target: { value: JSON.stringify(compositionExport) },
    });
    clickButton("Validate composition");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Composition validation" })).toBeInTheDocument();
    });
    expect(screen.getByText("blocking - missing_preset")).toBeInTheDocument();
    expect(validateWorldComposition).toHaveBeenCalledWith(
      expect.objectContaining({
        slug: "composition-import",
        name: "Composition Import",
        composition: compositionExport,
      }),
    );
  }, 180000);

  it("encodes workspace shortcut links for reserved world identifiers", () => {
    render(
      <WorldOverview
        data={{
          ...workspaceData,
          selectedWorld: { ...workspaceData.selectedWorld!, id: RESERVED_WORLD_ID },
        }}
      />,
    );

    const worldPath = `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}`;

    expect(screen.getByRole("link", { name: "Build agents" })).toHaveAttribute(
      "href",
      `${worldPath}/agents`,
    );
    expect(screen.getByRole("link", { name: "Open conversations" })).toHaveAttribute(
      "href",
      `${worldPath}/conversations`,
    );
    expect(screen.getByRole("link", { name: "Narrative artifacts" })).toHaveAttribute(
      "href",
      `${worldPath}/narrative`,
    );
    expect(screen.getByRole("link", { name: "Reader" })).toHaveAttribute(
      "href",
      `${worldPath}/reader`,
    );
  });


  it("encodes world EventSource paths for reserved world identifiers", () => {
    render(
      <WorldOverview
        data={{
          ...workspaceData,
          selectedWorld: { ...workspaceData.selectedWorld!, id: RESERVED_WORLD_ID },
        }}
      />,
    );

    expect(vi.mocked(subscribeToEventStream).mock.calls[0]?.[0]).toBe(
      `/api/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/stream`,
    );
  });

  it("submits V2 beta, release, route, ending, and worldline form contracts", async () => {
    vi.mocked(forkWorldline).mockResolvedValue(undefined as never);
    vi.mocked(compareWorldlines).mockResolvedValue({
      base_worldline_id: "worldline-1",
      compare_worldline_id: "worldline-1",
      fork_event_sequence: null,
      divergent_event_count: 0,
      relationship_delta_count: 0,
      faction_delta_count: 0,
      choice_delta_count: 0,
    });
    vi.mocked(createRouteMilestone).mockResolvedValue(undefined as never);
    vi.mocked(createEndingCandidate).mockResolvedValue(undefined as never);
    vi.mocked(createLongRunEval).mockResolvedValue(undefined as never);
    vi.mocked(upsertReleaseProfile).mockResolvedValue(undefined as never);
    vi.mocked(createBetaChecklist).mockResolvedValue(undefined as never);

    render(<WorldOverview data={workspaceData} />);

    const forkForm = formForHeading("Worldline fork");
    setFormValue(forkForm, "source_worldline_id", "worldline-1");
    setFormValue(forkForm, "worldline_key", "beta-branch");
    setFormValue(forkForm, "name", "Beta Branch");
    setFormValue(forkForm, "description", "Branch for beta readiness.");
    setFormValue(forkForm, "fork_event_sequence", "42");
    setFormValue(forkForm, "metadata", JSON.stringify({ reason: "beta_compare", gate: "ready" }));
    fireEvent.submit(forkForm);

    await waitFor(() => {
      expect(forkWorldline).toHaveBeenCalledWith("world-1", {
        source_worldline_id: "worldline-1",
        worldline_key: "beta-branch",
        name: "Beta Branch",
        description: "Branch for beta readiness.",
        fork_event_sequence: 42,
        metadata: { reason: "beta_compare", gate: "ready" },
      });
    });

    const compareForm = formForButton("Compare worldlines");
    setFormValue(compareForm, "base_worldline_id", "worldline-1");
    setFormValue(compareForm, "compare_worldline_id", "worldline-1");
    fireEvent.submit(compareForm);

    await waitFor(() => {
      expect(compareWorldlines).toHaveBeenCalledWith("world-1", "worldline-1", "worldline-1");
    });

    const milestoneForm = formForHeading("Route milestone");
    setFormValue(milestoneForm, "worldline_id", "worldline-1");
    setFormValue(milestoneForm, "milestone_key", "festival-ready");
    setFormValue(milestoneForm, "title", "Festival Ready");
    setFormValue(milestoneForm, "description", "All beta evidence is present.");
    setFormValue(milestoneForm, "stage", "4");
    setFormValue(milestoneForm, "status", "active");
    setFormValue(milestoneForm, "route_affinity_id", "route-1");
    setFormValue(milestoneForm, "plot_thread_id", "thread-1");
    setFormValue(
      milestoneForm,
      "conditions",
      JSON.stringify({ gate_decision: { status: "ready", allowed: true, blocker_count: 0 } }),
    );
    setFormValue(
      milestoneForm,
      "evidence_metadata",
      JSON.stringify({
        evidence_refs: [{ kind: "beta_checklist", id: "checklist-1", label: "sample-world-beta" }],
        gate_decision: { status: "ready", allowed: true },
      }),
    );
    setFormValue(milestoneForm, "metadata", JSON.stringify({ source: "v2-beta-contract" }));
    fireEvent.submit(milestoneForm);

    await waitFor(() => {
      expect(createRouteMilestone).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
        milestone_key: "festival-ready",
        title: "Festival Ready",
        description: "All beta evidence is present.",
        stage: 4,
        status: "active",
        route_affinity_id: "route-1",
        plot_thread_id: "thread-1",
        agent_id: null,
        conditions: { gate_decision: { status: "ready", allowed: true, blocker_count: 0 } },
        evidence_metadata: {
          evidence_refs: [{ kind: "beta_checklist", id: "checklist-1", label: "sample-world-beta" }],
          gate_decision: { status: "ready", allowed: true },
        },
        metadata: { source: "v2-beta-contract" },
      });
    });

    const endingForm = formForHeading("Ending candidate");
    setFormValue(endingForm, "worldline_id", "worldline-1");
    setFormValue(endingForm, "ending_key", "festival-release");
    setFormValue(endingForm, "title", "Festival Release Ending");
    setFormValue(endingForm, "ending_type", "epilogue");
    setFormValue(endingForm, "status", "available");
    setFormValue(endingForm, "route_affinity_id", "route-1");
    setFormValue(endingForm, "plot_thread_id", "thread-1");
    setFormValue(
      endingForm,
      "requirements",
      JSON.stringify({ gate_decision: { status: "ready", allowed: true }, min_route_stage: 4 }),
    );
    setFormValue(endingForm, "outcome_summary", "Beta can release after the festival route.");
    setFormValue(
      endingForm,
      "evidence_metadata",
      JSON.stringify({ evidence_refs: [{ kind: "route_milestone", id: "milestone-1" }] }),
    );
    setFormValue(endingForm, "metadata", JSON.stringify({ decision: "ready" }));
    fireEvent.submit(endingForm);

    await waitFor(() => {
      expect(createEndingCandidate).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
        ending_key: "festival-release",
        title: "Festival Release Ending",
        ending_type: "epilogue",
        status: "available",
        route_affinity_id: "route-1",
        plot_thread_id: "thread-1",
        agent_id: null,
        requirements: { gate_decision: { status: "ready", allowed: true }, min_route_stage: 4 },
        outcome_summary: "Beta can release after the festival route.",
        evidence_metadata: { evidence_refs: [{ kind: "route_milestone", id: "milestone-1" }] },
        metadata: { decision: "ready" },
      });
    });

    const evalForm = formForHeading("Long-run eval");
    setFormValue(evalForm, "worldline_id", "worldline-1");
    setFormValue(evalForm, "eval_key", "seven-day-release-gate");
    setFormValue(evalForm, "horizon_days", "14");
    setFormValue(
      evalForm,
      "metadata",
      JSON.stringify({
        gate_decision: {
          status: "blocked",
          allowed: false,
          blockers: [{ code: "route_gap", severity: "blocking" }],
          evidence_refs: [{ kind: "snapshot", id: "snapshot-1" }],
        },
      }),
    );
    fireEvent.submit(evalForm);

    await waitFor(() => {
      expect(createLongRunEval).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
        eval_key: "seven-day-release-gate",
        horizon_days: 14,
        metadata: {
          gate_decision: {
            status: "blocked",
            allowed: false,
            blockers: [{ code: "route_gap", severity: "blocking" }],
            evidence_refs: [{ kind: "snapshot", id: "snapshot-1" }],
          },
        },
      });
    });

    const releaseForm = formForHeading("Release profile");
    setFormValue(releaseForm, "profile_key", "living-world-v2-release");
    setFormValue(releaseForm, "status", "ready");
    setFormValue(releaseForm, "branch_policy", JSON.stringify({ branch_review: true, required_worldline_id: "worldline-1" }));
    setFormValue(releaseForm, "backup_policy", JSON.stringify({ snapshot_before_release: true }));
    setFormValue(releaseForm, "content_review_policy", JSON.stringify({ continuity_review_required: true }));
    setFormValue(releaseForm, "player_permission_policy", JSON.stringify({ beta_players: "invited" }));
    setFormValue(releaseForm, "worldline_policy", JSON.stringify({ forks_allowed: true, compare_before_release: true }));
    setFormValue(
      releaseForm,
      "checklist",
      JSON.stringify({
        gate_decision: {
          status: "ready",
          allowed: true,
          blockers: [],
          warnings: [{ code: "density_low", severity: "warning" }],
          evidence_refs: [{ kind: "long_run_eval", id: "eval-1", label: "seven-day-beta-eval" }],
        },
      }),
    );
    setFormValue(
      releaseForm,
      "metadata",
      JSON.stringify({
        gate_decision: {
          status: "ready",
          allowed: true,
          blockers: [],
          warnings: [],
          evidence_refs: [{ kind: "beta_checklist", id: "checklist-1", label: "sample-world-beta" }],
        },
      }),
    );
    fireEvent.submit(releaseForm);

    await waitFor(() => {
      expect(upsertReleaseProfile).toHaveBeenCalledWith("world-1", {
        profile_key: "living-world-v2-release",
        status: "ready",
        branch_policy: { branch_review: true, required_worldline_id: "worldline-1" },
        backup_policy: { snapshot_before_release: true },
        content_review_policy: { continuity_review_required: true },
        player_permission_policy: { beta_players: "invited" },
        worldline_policy: { forks_allowed: true, compare_before_release: true },
        checklist: {
          gate_decision: {
            status: "ready",
            allowed: true,
            blockers: [],
            warnings: [{ code: "density_low", severity: "warning" }],
            evidence_refs: [{ kind: "long_run_eval", id: "eval-1", label: "seven-day-beta-eval" }],
          },
        },
        metadata: {
          gate_decision: {
            status: "ready",
            allowed: true,
            blockers: [],
            warnings: [],
            evidence_refs: [{ kind: "beta_checklist", id: "checklist-1", label: "sample-world-beta" }],
          },
        },
      });
    });

    const checklistForm = formForHeading("Beta checklist");
    setFormValue(checklistForm, "worldline_id", "worldline-1");
    setFormValue(checklistForm, "run_key", "v2-release-checklist");
    setFormValue(
      checklistForm,
      "metadata",
      JSON.stringify({
        gate_decision: {
          status: "blocked",
          allowed: false,
          blockers: [{ code: "missing_release_profile", severity: "blocking" }],
          evidence_refs: [{ kind: "worldline_compare", id: "worldline-1" }],
        },
      }),
    );
    fireEvent.submit(checklistForm);

    await waitFor(() => {
      expect(createBetaChecklist).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
        run_key: "v2-release-checklist",
        metadata: {
          gate_decision: {
            status: "blocked",
            allowed: false,
            blockers: [{ code: "missing_release_profile", severity: "blocking" }],
            evidence_refs: [{ kind: "worldline_compare", id: "worldline-1" }],
          },
        },
      });
    });
  }, 180000);
});

function formForHeading(name: string): HTMLFormElement {
  const form = Array.from(document.querySelectorAll("form")).find((candidate) =>
    Array.from(candidate.querySelectorAll("h1,h2,h3,h4,h5,h6")).some(
      (heading) => heading.textContent?.trim() === name,
    ),
  );
  if (!(form instanceof HTMLFormElement)) {
    throw new Error(`Form for heading ${name} was not found.`);
  }
  return form;
}

function formForButton(name: string): HTMLFormElement {
  const button = buttonByName(name);
  const form = button.closest("form");
  if (!(form instanceof HTMLFormElement)) {
    throw new Error(`Form for button ${name} was not found.`);
  }
  return form;
}

function clickButton(name: string) {
  fireEvent.click(buttonByName(name));
}

function buttonByName(name: string): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll("button")).find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error(`Button ${name} was not found.`);
  }
  return button;
}

function setFormValue(form: HTMLFormElement, name: string, value: string) {
  const field = form.elements.namedItem(name);
  expect(field).not.toBeNull();
  fireEvent.change(field as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement, {
    target: { value },
  });
}

const compositionExport = {
  world: {
    slug: "first-world",
    name: "First World",
    description: null,
    rules_config: {},
    memory_backend_profile_key: null,
    memory_plugin_identifier: "builtin.mem0_oss_memory",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.default_world_rules",
    world_rules_plugin_config: {},
    is_active: true,
  },
  scenes: [],
  agents: [],
  schedule_rules: [],
  preset_references: [],
};

const RESERVED_WORLD_ID = "world/overview?mode=shortcuts#frag";

function eventRow(id: string, sequence: number, eventName: string): WorldEventAuditEntry {
  return {
    id,
    world_id: "world-1",
    sequence,
    event_name: eventName,
    importance: "system",
    payload: eventName === "agent.run_succeeded" ? { output: "ok" } : { error: "timeout" },
    wall_time: "2026-04-17T12:00:00.000Z",
    world_time: "2030-01-01T00:00:00.000Z",
    actor_ref: "agent:guide",
    causation_event_id: null,
    correlation_id: null,
    created_at: "2026-04-17T12:00:00.000Z",
  };
}

const workspaceData: WorldWorkspaceData = {
  worlds: [
    {
      id: "world-1",
      owner_user_id: "user-1",
      slug: "first-world",
      name: "First World",
      description: null,
      rules_config: {},
      memory_backend_profile_id: null,
      memory_plugin_identifier: "builtin.mem0_oss_memory",
      memory_plugin_config: {},
      world_rules_plugin_identifier: "builtin.default_world_rules",
      world_rules_plugin_config: {},
      is_active: true,
    },
  ],
  selectedWorld: {
    id: "world-1",
    owner_user_id: "user-1",
    slug: "first-world",
    name: "First World",
    description: null,
    rules_config: {},
    memory_backend_profile_id: null,
    memory_plugin_identifier: "builtin.mem0_oss_memory",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.default_world_rules",
    world_rules_plugin_config: {},
    is_active: true,
  },
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "classroom",
      name: "Classroom",
      description: null,
      region_key: "school",
      location_tags: ["school"],
      opening_rules: {},
      is_active: true,
    },
    {
      id: "scene-2",
      world_id: "world-1",
      scene_key: "courtyard",
      name: "Courtyard",
      description: null,
      region_key: "school",
      location_tags: [],
      opening_rules: {},
      is_active: true,
    },
  ],
  locationEdges: [
    {
      id: "edge-1",
      world_id: "world-1",
      source_scene_id: "scene-1",
      target_scene_id: "scene-2",
      source_scene_key: "classroom",
      target_scene_key: "courtyard",
      travel_label: "walkway",
      traversal_rules: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  agents: [],
  organizations: [
    {
      id: "org-1",
      world_id: "world-1",
      organization_key: "student-council",
      name: "Student Council",
      organization_type: "club",
      description: null,
      public_summary: "Runs school events.",
      hidden_summary: null,
      metadata: {},
      is_active: true,
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  worldlines: [
    {
      id: "worldline-1",
      world_id: "world-1",
      worldline_key: "primary",
      name: "Primary Worldline",
      description: "Default branch",
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: null,
      status: "active",
      created_by_actor_ref: "system:runtime",
      metadata: { primary: true },
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  gmAgendas: [
    {
      id: "agenda-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      title: "Festival route pressure",
      summary: "Keep the school festival route moving.",
      priority: 70,
      status: "active",
      focus_agents: ["guide"],
      focus_organizations: ["student-council"],
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  gmProposals: [
    {
      id: "proposal-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      agenda_id: "agenda-1",
      title: "Late-night club room",
      reason: "Relationship tension is ready.",
      event_name: "gm.route_pressure",
      proposed_payload: {},
      importance: "route",
      risk_score: 20,
      affected_agents: ["guide"],
      affected_organizations: ["student-council"],
      source_context: {},
      status: "proposed",
      review_note: null,
      resolved_event_id: null,
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  resolutionRules: [
    {
      id: "rule-1",
      world_id: "world-1",
      rule_key: "trust-gate",
      name: "Trust Gate",
      description: null,
      priority: 50,
      status: "active",
      conditions: { min_relationship_trust: 30 },
      effects: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  playerActors: [
    {
      id: "player-actor-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      actor_ref: "player:user-1:primary",
      display_name: "Player",
      current_scene_id: "scene-1",
      profile: {},
      is_active: true,
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  playerChoices: [
    {
      id: "choice-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      player_actor_id: "player-actor-1",
      choice_key: "help-festival",
      choice_kind: "intervention",
      prompt: "Help?",
      selected_option: "Stay late.",
      context: {},
      consequence_preview: {},
      applied_event_id: "event-choice",
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  livingWorldDashboard: {
    world_id: "world-1",
    worldline_id: "worldline-1",
    knowledge_count: 1,
    hidden_secret_count: 1,
    emotional_state_count: 1,
    open_hook_count: 1,
    unread_notification_count: 1,
    pending_intervention_count: 1,
    active_route_count: 1,
    pressure_summary: { risk: 20 },
  },
  knowledgeFacts: [
    {
      id: "knowledge-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      fact_key: "rival-route-note",
      knowledge_kind: "fact",
      content: "The rival noticed the late rehearsal.",
      source_event_id: null,
      source_ref: null,
      confidence: 90,
      visibility: "private",
      is_active: true,
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  secrets: [
    {
      id: "secret-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      secret_key: "hidden-letter",
      title: "Hidden letter",
      content: "The letter was left in the club room.",
      holder_agent_ids: ["agent-1"],
      reveal_conditions: {},
      consequence_metadata: {},
      visibility: "holders",
      status: "hidden",
      revealed_event_id: null,
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  emotionalStates: [
    {
      id: "emotion-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      mood: "restless",
      stress: 40,
      fatigue: 20,
      anticipation: 60,
      jealousy: 5,
      anger: 10,
      source_event_id: null,
      expires_at: null,
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  relationshipRepairs: [
    {
      id: "repair-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      relationship_id: "relationship-1",
      repair_kind: "apology",
      reason: "The hero apologizes for missing practice.",
      score_delta: { trust: 8 },
      status: "proposed",
      applied_event_id: null,
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  playerJournal: [
    {
      id: "journal-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      player_actor_id: "player-actor-1",
      entry_kind: "event",
      title: "Late rehearsal journal",
      body: "The route tension moved without direct intervention.",
      source_event_id: null,
      source_ref: null,
      visibility: "player_private",
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  notifications: [
    {
      id: "notification-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      notification_kind: "rumor",
      title: "Club room notice",
      body: "Someone mentioned a hidden letter.",
      source_event_id: null,
      source_ref: null,
      status: "unread",
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  interventions: [
    {
      id: "intervention-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      player_actor_id: "player-actor-1",
      intervention_kind: "contact",
      target_agent_id: "agent-1",
      target_scene_id: null,
      prompt: "Send a short message after school.",
      choice_id: "choice-1",
      event_id: "event-choice",
      status: "recorded",
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  gmStyleReviews: [
    {
      id: "style-review-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      source_kind: "manual",
      source_ref: null,
      reviewed_text: "As an AI chatbot, I can answer the user.",
      status: "warning",
      diagnostics: [{ code: "generic_chatbot_drift" }],
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  narrativeContinuityReviews: [
    {
      id: "continuity-review-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      artifact_id: null,
      source_kind: "manual",
      source_ref: null,
      reviewed_text: "Everyone knows the hidden letter.",
      status: "warning",
      issues: [{ code: "knowledge_leak_risk" }],
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  storyHooks: [
    {
      id: "hook-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      hook_key: "festival-promise",
      title: "Festival promise",
      hook_type: "promise",
      summary: "Guide promised to help.",
      status: "open",
      priority: 80,
      owner_agent_id: "agent-1",
      owner_agent_key: "guide",
      owner_agent_display_name: "Guide",
      target_agent_id: null,
      target_agent_key: null,
      target_agent_display_name: null,
      source_event_id: null,
      due_at: null,
      resolution: null,
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  plotThreads: [
    {
      id: "thread-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      thread_key: "festival-route",
      title: "Festival route",
      thread_type: "personal",
      status: "active",
      summary: "Festival route is moving.",
      stakes: "Club trust",
      next_beats: ["late rehearsal"],
      participant_agent_ids: ["agent-1"],
      organization_ids: ["org-1"],
      related_event_ids: [],
      priority: 70,
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  routeAffinities: [
    {
      id: "route-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      route_key: "guide-route",
      status: "active",
      affinity: 35,
      stage: 2,
      flags: ["festival"],
      last_choice_id: null,
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  routeMilestones: [
    {
      id: "milestone-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      route_affinity_id: "route-1",
      plot_thread_id: "thread-1",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      milestone_key: "confession-lock",
      title: "Festival confession lock",
      description: "The route can now lock the confession branch.",
      stage: 3,
      status: "active",
      conditions: { route_stage_min: 2 },
      evidence_metadata: { choice: "help-festival" },
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  endingCandidates: [
    {
      id: "ending-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      route_affinity_id: "route-1",
      plot_thread_id: "thread-1",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      ending_key: "guide-normal",
      title: "Guide normal ending",
      ending_type: "normal",
      status: "available",
      requirements: { min_route_stage: 2 },
      outcome_summary: "The festival route closes with a quiet confession.",
      evidence_metadata: { route: "guide-route" },
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  longRunEvals: [
    {
      id: "eval-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      eval_key: "seven-day-beta-eval",
      horizon_days: 7,
      status: "warning",
      started_at: "2026-05-07T12:00:00.000Z",
      finished_at: "2026-05-07T12:00:01.000Z",
      metrics: {
        event_density: 4,
        route_activity: 1,
        distribution: { day_coverage: 7 },
        traceability: {
          snapshot_ref_count: 1,
          refs: [
            { kind: "world_event", id: "event-1", label: "agent.run_succeeded" },
            { kind: "snapshot", id: "snapshot-1", label: "world_state.v1" },
          ],
        },
        review_warnings: { continuity_or_style_warning_count: 1 },
      },
      recommendations: [{ action: "add_daily_episode", reason: "low daily density" }],
      blockers: [],
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:01.000Z",
    },
  ],
  authoringTemplates: [
    {
      id: "template-1",
      world_id: "world-1",
      template_key: "sequel-world-bundle",
      template_kind: "world_bundle",
      name: "Sequel world bundle",
      description: "Source notes, character, event, and route template bundle.",
      content: { source_notes: [], characters: [], events: [], routes: [] },
      validation_issues: [],
      is_active: true,
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  authoringImportJobs: [
    {
      id: "authoring-job-1",
      world_id: "world-1",
      template_id: "template-1",
      status: "applied",
      preview_summary: {
        schema_version: "living-world-template/v2",
        validation_issue_count: 0,
        diff: { characters: ["guide"], events: ["festival"], routes: ["guide-route"] },
        audit: { action: "apply" },
      },
      applied_refs: {
        refs: [{ kind: "agent", id: "agent-1", label: "Guide" }],
      },
      validation_issues: [],
      metadata: { audit: { action: "apply" } },
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  releaseProfile: {
    id: "release-profile-1",
    world_id: "world-1",
    profile_key: "living-world-beta",
    status: "ready",
    branch_policy: { branch_review: true },
    backup_policy: { snapshot_before_beta: true },
    content_review_policy: { continuity_review_required: true },
    player_permission_policy: { invite_only: true },
    worldline_policy: { forks_allowed: true },
    checklist: {
      sample_world_required: true,
      gate_decision: {
        status: "ready",
        allowed: true,
        blockers: [],
        warnings: [],
        evidence_refs: [{ kind: "long_run_eval", id: "eval-1", label: "seven-day" }],
      },
    },
    metadata: {
      gate_decision: {
        status: "ready",
        allowed: true,
        blockers: [],
        warnings: [],
        evidence_refs: [{ kind: "long_run_eval", id: "eval-1", label: "seven-day" }],
      },
    },
    created_at: "2026-05-07T12:00:00.000Z",
    updated_at: "2026-05-07T12:00:00.000Z",
  },
  betaChecklists: [
    {
      id: "checklist-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      run_key: "sample-world-beta",
      status: "warning",
      summary: "Sample world beta has non-blocking recommendations.",
      evidence: {
        days: 7,
        refs: [{ kind: "long_run_eval", id: "eval-1", label: "seven-day" }],
      },
      blocker_count: 0,
      created_by_actor_ref: "user:user-1",
      metadata: {},
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  betaChecklistItems: [
    {
      id: "checklist-item-1",
      run_id: "checklist-1",
      item_key: "seven-day-simulation",
      title: "7-day simulation",
      status: "warning",
      evidence: {
        eval_run_id: "eval-1",
        refs: [{ kind: "long_run_eval", id: "eval-1", label: "seven-day" }],
      },
      recommendation: "Increase daily episode density before public beta.",
      created_at: "2026-05-07T12:00:00.000Z",
      updated_at: "2026-05-07T12:00:00.000Z",
    },
  ],
  triggerConditions: [
    {
      id: "trigger-1",
      world_id: "world-1",
      condition_key: "festival-gate",
      name: "Festival Gate",
      description: null,
      status: "active",
      priority: 50,
      conditions: { min_open_hooks: 1 },
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  sceneBeats: [
    {
      id: "beat-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      source_kind: "manual",
      source_ref: null,
      title: "Late rehearsal",
      setup: "Guide gathers around Late rehearsal.",
      dialogue_beats: [],
      choice_points: [],
      aftermath: "Follow up.",
      participant_agent_ids: ["agent-1"],
      scene_id: "scene-1",
      scene_key: "classroom",
      scene_name: "Classroom",
      status: "draft",
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  dailyEpisodes: [
    {
      id: "episode-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      source_candidate_id: null,
      title: "After-school episode",
      summary: "A low-risk daily episode.",
      scene_beat_draft_id: "beat-1",
      participant_agent_ids: ["agent-1"],
      status: "draft",
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  groupInteractions: [
    {
      id: "group-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      context_key: "festival-meeting",
      title: "Festival meeting",
      interaction_type: "organization_meeting",
      scene_id: "scene-1",
      scene_key: "classroom",
      scene_name: "Classroom",
      organization_id: "org-1",
      organization_key: "student-council",
      organization_name: "Student Council",
      participant_agent_ids: ["agent-1"],
      participant_roles: {},
      constraints: {},
      status: "planned",
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  relationshipSuggestions: [
    {
      id: "suggestion-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      relationship_id: "relationship-1",
      source_agent_id: "agent-1",
      source_agent_display_name: "Guide",
      target_agent_id: null,
      target_agent_display_name: null,
      title: "Relationship tension scene",
      reason: "Relationship pressure: rivalry 40",
      suggested_event_name: "relationship.suggested_event",
      score: 40,
      status: "suggested",
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  organizationConflicts: [
    {
      id: "conflict-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      organization_id: "org-1",
      organization_key: "student-council",
      organization_name: "Student Council",
      faction_track_id: "track-1",
      faction_track_key: "festival-plan",
      title: "Budget pressure",
      summary: "Budget pressure rises.",
      pressure_delta: 5,
      progress_delta: 2,
      status: "proposed",
      resolved_event_id: null,
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  rumors: [
    {
      id: "rumor-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      rumor_key: "late-rehearsal",
      title: "Late rehearsal rumor",
      content: "Guide stayed late.",
      source_agent_id: "agent-1",
      source_agent_display_name: "Guide",
      source_organization_id: null,
      source_organization_name: null,
      visibility: "group",
      known_agent_ids: ["agent-1"],
      status: "active",
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  rumorPropagations: [
    {
      id: "rumor-propagation-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      rumor_id: "rumor-1",
      rumor_title: "Late rehearsal rumor",
      source_agent_id: "agent-1",
      source_agent_display_name: "Guide",
      target_agent_id: null,
      target_agent_display_name: null,
      target_organization_id: "org-1",
      target_organization_name: "Student Council",
      propagation_reason: "Club members saw the lights.",
      status: "pending",
      delivered_event_id: null,
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  organizationMemberships: [
    {
      id: "membership-1",
      world_id: "world-1",
      organization_id: "org-1",
      organization_key: "student-council",
      organization_name: "Student Council",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      role_title: "President",
      visibility: "public",
      loyalty: 80,
      influence: 70,
      responsibilities: [],
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  factionTracks: [
    {
      id: "track-1",
      world_id: "world-1",
      organization_id: "org-1",
      organization_key: "student-council",
      organization_name: "Student Council",
      track_key: "festival-plan",
      name: "Festival Plan",
      track_type: "goal",
      progress: 30,
      pressure: 20,
      summary: "Venue search",
      metadata: {},
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  agentPresenceStates: [
    {
      id: "presence-1",
      world_id: "world-1",
      agent_id: "agent-1",
      agent_key: "guide",
      agent_display_name: "Guide",
      current_scene_id: "scene-1",
      current_scene_key: "classroom",
      current_scene_name: "Classroom",
      visibility_status: "visible",
      encounter_eligible: true,
      scheduled_movement: {},
      last_event_id: null,
      created_at: "2026-05-05T12:00:00.000Z",
      updated_at: "2026-05-05T12:00:00.000Z",
    },
  ],
  dailyLifePreview: null,
  dailyLifeCandidates: [],
  offscreenEvents: [],
  memberships: [],
  worldBible: null,
  memoryBackendProfiles: [],
  memoryPlugins: [
    {
      identifier: "builtin.mem0_oss_memory",
      category: "memory_backend",
      version: "0.1.0",
      config_schema: {},
      capabilities: [],
      built_in: true,
    },
  ],
  worldRulesPlugins: [
    {
      identifier: "builtin.default_world_rules",
      category: "world_rules",
      version: "0.1.0",
      config_schema: {},
      capabilities: [],
      built_in: true,
    },
  ],
  clock: {
    world_id: "world-1",
    status: "paused",
    current_world_time: "2030-01-01T00:00:00.000Z",
    effective_world_time: "2030-01-01T00:00:00.000Z",
    wall_time_anchor: null,
    speed_multiplier: "1",
    revision: 0,
  },
  clockTransitions: [
    {
      id: "transition-1",
      world_id: "world-1",
      transition_type: "resume",
      previous_status: "paused",
      new_status: "running",
      previous_world_time: "2030-01-01T00:00:00.000Z",
      new_world_time: "2030-01-01T00:01:00.000Z",
      wall_time: "2026-04-17T12:00:00.000Z",
      previous_revision: 0,
      new_revision: 1,
      actor_ref: "user:user-1",
      correlation_id: null,
      reason: "start",
      created_at: "2026-04-17T12:00:00.000Z",
    },
  ],
  replayState: {
    world_id: "world-1",
    schema_version: "world_state.v1",
    source_sequence: 1,
    clock: null,
    applied_event_count: 1,
    unhandled_event_count: 0,
  },
  latestSnapshot: null,
  snapshotIntegrity: {
    world_id: "world-1",
    status: "ok",
    latest_event_sequence: 1,
    latest_snapshot_id: null,
    covers_event_sequence: null,
    schema_version: null,
    payload_location: null,
    event_gap: 0,
    issues: [],
  },
  worldEventAudit: [eventRow("event-1", 1, "agent.run_succeeded")],
  calendarConflicts: {
    world_id: "world-1",
    start_world_time: "2030-01-01T00:00:00.000Z",
    horizon_hours: 168,
    conflict_count: 0,
    conflicts: [],
  },
  scheduleRules: [],
  worldDiagnostics: [],
  canManageSelectedWorld: true,
  isPlatformAdmin: true,
  loadError: null,
};
