import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>("@/lib/worlds/client");
  return {
    ...actual,
    listAgentMemory: vi.fn(),
    listAgentObservations: vi.fn(),
    listWorldDiagnostics: vi.fn(),
    listNarrativeArtifacts: vi.fn(),
    runAgent: vi.fn(),
  };
});

import { WorldManagementDashboard } from "@/features/dashboard/world-management-dashboard";
import type { AuthSubject } from "@/lib/auth/types";
import {
  listAgentMemory,
  listAgentObservations,
  listNarrativeArtifacts,
  listWorldDiagnostics,
  runAgent,
} from "@/lib/worlds/client";
import type { WorldDashboardData } from "@/lib/worlds/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("WorldManagementDashboard", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders an empty platform admin state with create controls", () => {
    render(<WorldManagementDashboard subject={platformAdmin} initialData={emptyData} />);

    expect(screen.getByRole("heading", { name: "Create world" })).toBeInTheDocument();
    expect(screen.getByText("0 visible")).toBeInTheDocument();
    expect(screen.getByText("No worlds yet")).toBeInTheDocument();
  });

  it("renders admin management controls for a selected world", () => {
    render(<WorldManagementDashboard subject={platformAdmin} initialData={adminData} />);

    expect(screen.getByRole("heading", { name: "First World" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save world" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "World clock" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resume clock" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Replay and snapshots" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create snapshot" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Schedule rules" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent calendar" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent memory" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent persona and observations" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Runtime control" })).toBeInTheDocument();
    expect(screen.getByText("Runtime iteration failed.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Provider profiles" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent runs" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Narrative artifacts" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create scene" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create agent" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Owner" })).toBeInTheDocument();
  });

  it("hides management controls for read-only world members", () => {
    render(<WorldManagementDashboard subject={humanUser} initialData={readOnlyData} />);

    expect(screen.getByText("Read-only world access.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save world" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume clock" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create snapshot" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Home" })).toBeInTheDocument();
  });

  it("shows a success notice after running an agent", async () => {
    vi.mocked(runAgent).mockResolvedValue({
      run_id: "run-2",
      world_id: "world-1",
      agent_id: "agent-1",
      status: "succeeded",
      prompt_text: "Say hello from runtime",
      response_text: "Hello from runtime",
      provider_profile_id: "profile-1",
      trigger_source: "manual",
      source_calendar_entry_id: null,
      source_schedule_rule_id: null,
      created_event_id: null,
      diagnostics: { persona_enabled: true, observation_count: 1 },
      started_at: "2026-04-17T00:05:00.000Z",
      finished_at: "2026-04-17T00:05:01.000Z",
    });
    vi.mocked(listNarrativeArtifacts).mockResolvedValue(adminData.narrativeArtifacts);
    vi.mocked(listAgentMemory).mockResolvedValue(adminData.memoryItems);
    vi.mocked(listAgentObservations).mockResolvedValue(adminData.agentObservations);
    vi.mocked(listWorldDiagnostics).mockResolvedValue(adminData.worldDiagnostics);

    render(<WorldManagementDashboard subject={platformAdmin} initialData={adminDataWithAgent} />);

    fireEvent.change(screen.getByPlaceholderText("Manual run prompt"), {
      target: { value: "Say hello from runtime" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run agent" }));

    await waitFor(() => {
      expect(screen.getByText("Agent run completed.")).toBeInTheDocument();
    });
    expect(screen.queryByText("Cannot read properties of null (reading 'reset')")).not.toBeInTheDocument();
  });
});

const platformAdmin: AuthSubject = {
  user_id: "00000000-0000-4000-8000-000000000001",
  email: "admin@example.test",
  display_name: "Admin",
  roles: ["platform_admin"],
};

const humanUser: AuthSubject = {
  user_id: "00000000-0000-4000-8000-000000000002",
  email: "member@example.test",
  display_name: "Member",
  roles: [],
};

const emptyData: WorldDashboardData = {
  worlds: [],
  selectedWorldId: null,
  scenes: [],
  agents: [],
  memberships: [],
  clock: null,
  replayState: null,
  latestSnapshot: null,
  worldEventAudit: [],
  selectedAgentId: null,
  calendarEntries: [],
  scheduleRules: [],
  memoryItems: [],
  agentRuns: [],
  agentPersona: null,
  agentObservations: [],
  narrativeArtifacts: [],
  providerProfiles: [],
  runtimeControl: null,
  runtimeStatus: null,
  runtimeDiagnostics: [],
  worldDiagnostics: [],
  canManageSelectedWorld: false,
  loadError: null,
};

const adminData: WorldDashboardData = {
  worlds: [
    {
      id: "world-1",
      owner_user_id: platformAdmin.user_id,
      slug: "first-world",
      name: "First World",
      description: null,
      rules_config: {},
      memory_backend_profile_id: null,
      memory_plugin_identifier: "builtin.local_pgvector_memory",
      memory_plugin_config: {},
      world_rules_plugin_identifier: "builtin.default_world_rules",
      world_rules_plugin_config: {},
      is_active: true,
    },
  ],
  selectedWorldId: "world-1",
  scenes: [],
  agents: [],
  memberships: [
    {
      id: "membership-1",
      world_id: "world-1",
      user_id: platformAdmin.user_id,
      role: "world_admin",
      user: {
        id: platformAdmin.user_id,
        email: platformAdmin.email,
        display_name: "Owner",
        is_active: true,
      },
    },
  ],
  clock: {
    world_id: "world-1",
    status: "paused",
    current_world_time: "2026-04-17T00:00:00.000Z",
    effective_world_time: "2026-04-17T00:00:00.000Z",
    wall_time_anchor: null,
    speed_multiplier: "1",
    revision: 0,
  },
  replayState: {
    world_id: "world-1",
    schema_version: "world_state.v1",
    source_sequence: 0,
    clock: null,
    applied_event_count: 0,
    unhandled_event_count: 0,
  },
  latestSnapshot: null,
  worldEventAudit: [],
  selectedAgentId: null,
  calendarEntries: [],
  scheduleRules: [
    {
      id: "rule-1",
      world_id: "world-1",
      rule_key: "weekday",
      name: "Weekday",
      kind: "weekday",
      config: {},
      is_enabled: true,
    },
  ],
  memoryItems: [
    {
      id: "memory-1",
      world_id: "world-1",
      agent_id: "agent-1",
      content: "Memory content",
      metadata: { source: "test" },
      backend: "local_pgvector",
      created_at: "2026-04-17T00:02:30.000Z",
      score: null,
    },
  ],
  agentRuns: [
    {
      run_id: "run-1",
      world_id: "world-1",
      agent_id: "agent-1",
      status: "succeeded",
      prompt_text: "Prompt",
      response_text: "Response",
      provider_profile_id: "profile-1",
      trigger_source: "manual",
      source_calendar_entry_id: null,
      source_schedule_rule_id: null,
      created_event_id: null,
      diagnostics: { persona_enabled: false, observation_count: 0 },
      started_at: "2026-04-17T00:03:00.000Z",
      finished_at: "2026-04-17T00:03:01.000Z",
    },
  ],
  agentPersona: {
    id: "persona-1",
    world_id: "world-1",
    agent_id: "agent-1",
    persona_text: "Careful guide.",
    behavior_policy: { tone: "direct" },
    policy_plugin_identifier: "builtin.default_persona_policy",
    policy_plugin_config: {},
    is_enabled: true,
    created_at: "2026-04-17T00:02:00.000Z",
    updated_at: "2026-04-17T00:02:00.000Z",
  },
  agentObservations: [
    {
      id: "observation-1",
      world_id: "world-1",
      agent_id: "agent-1",
      source_event_id: "event-1",
      observation_type: "world.clock_advanced",
      content: "World clock advanced.",
      metadata: {},
      observed_at: "2026-04-17T00:02:00.000Z",
      consumed_at: null,
      confidence_score: null,
      review_status: "unreviewed" as const,
      runtime_use_count: 0,
      last_used_run_id: null,
      created_at: "2026-04-17T00:02:00.000Z",
    },
  ],
  narrativeArtifacts: [
    {
      id: "artifact-1",
      world_id: "world-1",
      agent_id: "agent-1",
      source_conversation_id: null,
      source_run_id: "run-1",
      title: "Artifact",
      content: "Artifact content",
      artifact_kind: "agent_note",
      metadata: {},
      created_at: "2026-04-17T00:03:02.000Z",
    },
  ],
  providerProfiles: [
    {
      id: "profile-1",
      profile_key: "openai-local",
      name: "OpenAI Local",
      provider_type: "openai_compatible",
      plugin_identifier: "builtin.openai_compatible",
      plugin_config: {},
      base_url: "https://api.example.test/v1",
      model_name: "gpt-test",
      capabilities: {},
      api_key_ref: "openai-local",
      timeout_seconds: 20,
      retry_attempts: 1,
      rate_limit_per_minute: null,
      last_tested_at: null,
      last_test_status: null,
      last_test_error: null,
      is_enabled: true,
    },
  ],
  runtimeControl: {
    desired_state: "stopped",
    last_heartbeat_at: null,
    last_run_started_at: null,
    last_run_finished_at: null,
    last_error: null,
  },
  runtimeStatus: {
    desired_state: "stopped",
    last_heartbeat_at: null,
    last_run_started_at: null,
    last_run_finished_at: null,
    last_error: null,
    runtime_loop_interval_seconds: 5,
    runtime_batch_limit: 20,
	    memory_write_jobs: {
	      pending_count: 0,
	      processing_count: 0,
	      succeeded_count: 0,
	      failed_count: 0,
	      due_count: 0,
	      retryable_failed_count: 0,
	      terminal_failed_count: 0,
	      stalled_processing_count: 0,
	    },
	    runtime_health: {
	      status: "stopped",
	      reason: "Runtime desired state is stopped.",
	      recent_diagnostic_count: 0,
	      recent_error_count: 0,
	      heartbeat_age_seconds: null,
	    },
	  },
  runtimeDiagnostics: [
    {
      id: "diagnostic-1",
      severity: "error",
      component: "runtime",
      event_type: "runtime.iteration_failed",
      message: "Runtime iteration failed.",
      details: {},
      occurred_at: "2026-04-17T00:04:00.000Z",
      world_id: null,
      agent_id: null,
      run_id: null,
      provider_profile_id: null,
      created_at: "2026-04-17T00:04:00.000Z",
    },
  ],
  worldDiagnostics: [
    {
      id: "diagnostic-2",
      severity: "info",
      component: "agent",
      event_type: "agent.run_succeeded",
      message: "Agent runtime run succeeded.",
      details: {},
      occurred_at: "2026-04-17T00:05:00.000Z",
      world_id: "world-1",
      agent_id: "agent-1",
      run_id: "run-1",
      provider_profile_id: "profile-1",
      created_at: "2026-04-17T00:05:00.000Z",
    },
  ],
  canManageSelectedWorld: true,
  loadError: null,
};

const adminDataWithAgent: WorldDashboardData = {
  ...adminData,
  selectedAgentId: "agent-1",
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "home",
      name: "Home",
      description: null,
      is_active: true,
    },
  ],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      source_preset_id: null,
      agent_key: "guide",
      display_name: "Guide",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
  ],
  calendarEntries: [
    {
      id: "entry-1",
      world_id: "world-1",
      agent_id: "agent-1",
      title: "Morning scene",
      description: null,
      starts_at: "2030-01-01T08:00:00.000Z",
      ends_at: null,
      recurrence_rule: null,
      status: "active",
      metadata: {},
    },
  ],
};

const readOnlyData: WorldDashboardData = {
  worlds: adminData.worlds,
  selectedWorldId: "world-1",
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "home",
      name: "Home",
      description: null,
      is_active: true,
    },
  ],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      source_preset_id: null,
      agent_key: "guide",
      display_name: "Guide",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
  ],
  memberships: [],
  clock: {
    world_id: "world-1",
    status: "running",
    current_world_time: "2026-04-17T00:00:00.000Z",
    effective_world_time: "2026-04-17T00:01:00.000Z",
    wall_time_anchor: "2026-04-17T00:00:00.000Z",
    speed_multiplier: "1",
    revision: 1,
  },
  replayState: {
    world_id: "world-1",
    schema_version: "world_state.v1",
    source_sequence: 1,
    clock: {
      status: "running",
      current_world_time: "2026-04-17T00:01:00.000Z",
      effective_world_time: "2026-04-17T00:01:00.000Z",
      wall_time_anchor: "2026-04-17T00:00:00.000Z",
      speed_multiplier: "1",
      revision: 1,
      last_event_id: "event-1",
      last_event_sequence: 1,
    },
    applied_event_count: 1,
    unhandled_event_count: 0,
  },
  latestSnapshot: {
    id: "snapshot-1",
    world_id: "world-1",
    covers_event_sequence: 1,
    schema_version: "world_state.v1",
    status: "valid",
    payload: {},
    payload_uri: null,
    metadata: {},
    created_by_event_id: "event-2",
    created_at: "2026-04-17T00:02:00.000Z",
  },
  worldEventAudit: [],
  selectedAgentId: "agent-1",
  calendarEntries: [
    {
      id: "entry-1",
      world_id: "world-1",
      agent_id: "agent-1",
      title: "Morning scene",
      description: null,
      starts_at: "2030-01-01T08:00:00.000Z",
      ends_at: null,
      recurrence_rule: null,
      status: "active",
      metadata: {},
    },
  ],
  scheduleRules: [],
  memoryItems: [
    {
      id: "memory-1",
      world_id: "world-1",
      agent_id: "agent-1",
      content: "Read-only memory",
      metadata: {},
      backend: "local_pgvector",
      created_at: "2026-04-17T00:02:30.000Z",
      score: 0.91,
    },
  ],
  agentRuns: [
    {
      run_id: "run-1",
      world_id: "world-1",
      agent_id: "agent-1",
      status: "succeeded",
      prompt_text: "Prompt",
      response_text: "Response",
      provider_profile_id: "profile-1",
      trigger_source: "manual",
      source_calendar_entry_id: null,
      source_schedule_rule_id: null,
      created_event_id: null,
      diagnostics: { persona_enabled: false, observation_count: 0 },
      started_at: "2026-04-17T00:03:00.000Z",
      finished_at: "2026-04-17T00:03:01.000Z",
    },
  ],
  agentPersona: null,
  agentObservations: [],
  narrativeArtifacts: [
    {
      id: "artifact-1",
      world_id: "world-1",
      agent_id: "agent-1",
      source_conversation_id: null,
      source_run_id: "run-1",
      title: "Artifact",
      content: "Artifact content",
      artifact_kind: "agent_note",
      metadata: {},
      created_at: "2026-04-17T00:03:02.000Z",
    },
  ],
  providerProfiles: [],
  runtimeControl: null,
  runtimeStatus: null,
  runtimeDiagnostics: [],
  worldDiagnostics: [],
  canManageSelectedWorld: false,
  loadError: null,
};
