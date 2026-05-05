import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/realtime", () => ({
  subscribeToEventStream: vi.fn(() => undefined),
}));

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>(
    "@/lib/worlds/client",
  );
  return {
    ...actual,
    getCalendarConflicts: vi.fn(),
    listWorldEvents: vi.fn(),
    previewScheduleRule: vi.fn(),
    validateWorldComposition: vi.fn(),
  };
});

import { WorldOverview } from "@/features/worlds/world-overview";
import {
  getCalendarConflicts,
  listWorldEvents,
  previewScheduleRule,
  validateWorldComposition,
} from "@/lib/worlds/client";
import type { WorldWorkspaceData } from "@/lib/worlds/server";
import type { WorldEventAuditEntry } from "@/lib/worlds/types";

describe("WorldOverview", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

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
    expect(screen.getByText("Gap 0")).toBeInTheDocument();
    expect(screen.getByText(/agent.run_succeeded/)).toBeInTheDocument();
    expect(screen.getByText('{"output":"ok"}')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("event.name"), {
      target: { value: "agent.run_failed" },
    });
    fireEvent.change(screen.getByPlaceholderText("actor:ref"), {
      target: { value: "agent:guide" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Filter events" }));

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

    fireEvent.click(screen.getByRole("button", { name: "Preview schedule" }));

    await waitFor(() => {
      expect(screen.getByText("Preview matches 1 windows for 1 agents.")).toBeInTheDocument();
    });
    expect(screen.getByText("hour 8 - 1 agents")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Check conflicts" }));

    await waitFor(() => {
      expect(screen.getByText(/calendar_entry_overlap/)).toBeInTheDocument();
    });
    expect(getCalendarConflicts).toHaveBeenCalledWith("world-1", {
      start_world_time: null,
      horizon_hours: 168,
      limit: 50,
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
    fireEvent.click(screen.getByRole("button", { name: "Validate composition" }));

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
  }, 10000);
});

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

function eventRow(id: string, sequence: number, eventName: string): WorldEventAuditEntry {
  return {
    id,
    world_id: "world-1",
    sequence,
    event_name: eventName,
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
  scenes: [],
  agents: [],
  memberships: [],
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
