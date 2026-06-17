import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", () => ({
  createAgentCalendarEntry: vi.fn(),
  createAgentObservation: vi.fn(),
  createAgentRelationship: vi.fn(),
  forgetAgentMemory: vi.fn(),
  getAgentRunDetail: vi.fn(),
  listAgentMemory: vi.fn(),
  refreshAgentMemoryProfileSnapshot: vi.fn(),
  refreshAgentObservations: vi.fn(),
  runAgent: vi.fn(),
  searchAgentMemory: vi.fn(),
  updateAgent: vi.fn(),
  updateAgentPersona: vi.fn(),
  updateAgentRelationship: vi.fn(),
  validateAgentPersona: vi.fn(),
}));

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import { AgentBuilder } from "@/features/agents/agent-builder";
import {
  createAgentRelationship,
  getAgentRunDetail,
  updateAgent,
  updateAgentRelationship,
} from "@/lib/worlds/client";
import type { AgentDetailData } from "@/lib/worlds/server";

describe("AgentBuilder", () => {
  afterEach(() => {
    vi.clearAllMocks();
    refresh.mockReset();
  });

  it("redacts sensitive agent builder JSON and run text", async () => {
    const dirtyData: AgentDetailData = {
      ...agentData,
      selectedAgent: {
        ...agentData.selectedAgent!,
        character_profile: {
          story_function: "route heroine",
          clientSecret: "sk-agent-secret",
          nested: { storageUri: "media://agent-secret" },
        },
        config: { safeMode: true, rawPrompt: "system prompt", filePath: "/tmp/agent-config.json" },
      },
      relationships: [
        {
          ...agentData.relationships[0],
          metadata: { reason: "shared promise", bearerToken: "Bearer agent-token" },
        },
      ],
      agentPersona: {
        id: "persona-1",
        world_id: "world-1",
        agent_id: "agent-1",
        persona_text: "Careful guide.",
        behavior_policy: { tone: "direct", promptSnapshotId: "snapshot-agent" },
        policy_plugin_identifier: "builtin.default_persona_policy",
        policy_plugin_config: { endpoint: "/v1/chat/completions", rawOutput: "model output" },
        is_enabled: true,
        created_at: "2026-05-05T00:00:00.000Z",
        updated_at: "2026-05-05T00:00:00.000Z",
      },
      agentRuns: [
        {
          run_id: "run-1",
          world_id: "world-1",
          agent_id: "agent-1",
          status: "failed",
          prompt_text: "Prompt with rawPrompt and media://run-secret",
          response_text: "Response with sk-run-secret",
          provider_profile_id: "profile-1",
          trigger_source: "manual",
          source_calendar_entry_id: null,
          source_schedule_rule_id: null,
          created_event_id: null,
          diagnostics: { promptSnapshotId: "snapshot-run" },
          started_at: "2026-05-05T00:00:00.000Z",
          finished_at: "2026-05-05T00:00:01.000Z",
        },
      ],
    };
    vi.mocked(updateAgent).mockResolvedValue({
      ...dirtyData.selectedAgent!,
      character_profile: { story_function: "route heroine", nested: {} },
      config: { safeMode: true },
    });
    vi.mocked(getAgentRunDetail).mockResolvedValue({
      run: {
        ...dirtyData.agentRuns[0],
        diagnostics: { safe: "ok", rawOutput: "model output", storageUri: "media://diag-secret" },
      },
      provider_profile: null,
      conversation_turns: [],
    });

    render(<AgentBuilder worldId="world-1" agentId="agent-1" data={dirtyData} />);

    expect(screen.getByDisplayValue(/story_function/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/safeMode/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/shared promise/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/tone/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/rawPrompt|media:\/\/run-secret|sk-run-secret/i);
    expect(
      screen.queryAllByDisplayValue(
        /clientSecret|sk-agent-secret|storageUri|media:\/\/agent-secret|rawPrompt|filePath|\/tmp\/agent-config|bearerToken|Bearer agent-token|promptSnapshotId|snapshot-agent|rawOutput/i,
      ),
    ).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: "Save agent" }));

    await waitFor(() => {
      expect(updateAgent).toHaveBeenCalledWith(
        "world-1",
        "agent-1",
        expect.objectContaining({
          character_profile: { story_function: "route heroine", nested: {} },
          config: { safeMode: true },
        }),
      );
    });
    expect(JSON.stringify(vi.mocked(updateAgent).mock.calls[0][2])).not.toMatch(
      /clientSecret|sk-agent-secret|storageUri|media:\/\/agent-secret|rawPrompt|filePath|\/tmp\/agent-config/i,
    );

    fireEvent.click(screen.getByRole("button", { name: "Inspect run" }));

    await waitFor(() => {
      expect(screen.getByText("Run inspector")).toBeInTheDocument();
    });
    expect(document.body.textContent).toContain("safe");
    expect(document.body.textContent).not.toMatch(/rawOutput|storageUri|media:\/\/diag-secret|snapshot-run/i);
  });

  it("renders character profile and submits relationship updates", async () => {
    vi.mocked(updateAgent).mockResolvedValue(agentData.selectedAgent!);
    vi.mocked(createAgentRelationship).mockResolvedValue({
      ...agentData.relationships[0],
      id: "relationship-2",
      target_agent_id: "agent-3",
      target_agent_key: "rival",
      target_display_name: "Rival",
      trust: 20,
    });
    vi.mocked(updateAgentRelationship).mockResolvedValue({
      ...agentData.relationships[0],
      trust: 55,
      metadata: { reason: "kept promise" },
    });

    render(<AgentBuilder worldId="world-1" agentId="agent-1" data={agentData} />);

    expect(screen.getByRole("heading", { name: "Character profile sheet" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Autonomous world state" })).toBeInTheDocument();
    expect(document.body.textContent).toContain("route heroine");
    expect(screen.getAllByText("Club Room").length).toBeGreaterThan(0);
    expect(screen.getByText("Student Council")).toBeInTheDocument();
    expect(screen.getByText("Target - friendship")).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("lead"), { target: { value: "major" } });
    fireEvent.click(screen.getByRole("button", { name: "Save agent" }));

    await waitFor(() => {
      expect(updateAgent).toHaveBeenCalledWith(
        "world-1",
        "agent-1",
        expect.objectContaining({
          importance: "major",
          character_profile: expect.objectContaining({ story_function: "route heroine" }),
        }),
      );
    });

    fireEvent.change(screen.getByDisplayValue("Target agent"), { target: { value: "agent-3" } });
    fireEvent.click(screen.getByRole("button", { name: "Create relationship" }));

    await waitFor(() => {
      expect(createAgentRelationship).toHaveBeenCalledWith(
        "world-1",
        "agent-1",
        expect.objectContaining({ target_agent_id: "agent-3", relationship_type: "friendship" }),
      );
    });

    const trustInputs = screen.getAllByPlaceholderText("Trust");
    fireEvent.change(trustInputs[1], { target: { value: "55" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Update edge" })[0]);

    await waitFor(() => {
      expect(updateAgentRelationship).toHaveBeenCalledWith(
        "world-1",
        "agent-1",
        "relationship-1",
        expect.objectContaining({ trust: 55 }),
      );
    });
  });
});

const agentData: AgentDetailData = {
  worlds: [
    {
      id: "world-1",
      owner_user_id: "user-1",
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
  selectedWorld: {
    id: "world-1",
    owner_user_id: "user-1",
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
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "club-room",
      name: "Club Room",
      description: null,
      region_key: "school",
      location_tags: ["club"],
      opening_rules: {},
      is_active: true,
    },
  ],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      source_preset_id: null,
      source_preset_version: null,
      agent_key: "heroine",
      display_name: "Heroine",
      kind: "role_agent",
      provider_profile_id: null,
      narrative_role: "main_character",
      importance: "lead",
      canon_status: "post_canon",
      character_category: "main_character",
      character_profile: { story_function: "route heroine", goals: ["reopen the club"] },
      config: {},
      is_enabled: true,
    },
    {
      id: "agent-2",
      world_id: "world-1",
      home_scene_id: null,
      source_preset_id: null,
      source_preset_version: null,
      agent_key: "target",
      display_name: "Target",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
    {
      id: "agent-3",
      world_id: "world-1",
      home_scene_id: null,
      source_preset_id: null,
      source_preset_version: null,
      agent_key: "rival",
      display_name: "Rival",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
  ],
  providerProfiles: [],
  agentPresets: [],
  personaPolicyPlugins: [],
  canManageSelectedWorld: true,
  isPlatformAdmin: true,
  loadError: null,
  selectedAgent: {
    id: "agent-1",
    world_id: "world-1",
    home_scene_id: "scene-1",
    source_preset_id: null,
    source_preset_version: null,
    agent_key: "heroine",
    display_name: "Heroine",
    kind: "role_agent",
    provider_profile_id: null,
    narrative_role: "main_character",
    importance: "lead",
    canon_status: "post_canon",
    character_category: "main_character",
    character_profile: { story_function: "route heroine", goals: ["reopen the club"] },
    config: {},
    is_enabled: true,
  },
  presence: {
    id: "presence-1",
    world_id: "world-1",
    agent_id: "agent-1",
    agent_key: "heroine",
    agent_display_name: "Heroine",
    current_scene_id: "scene-1",
    current_scene_key: "club-room",
    current_scene_name: "Club Room",
    visibility_status: "visible",
    encounter_eligible: true,
    scheduled_movement: {},
    last_event_id: null,
    created_at: "2026-05-05T00:00:00.000Z",
    updated_at: "2026-05-05T00:00:00.000Z",
  },
  organizationMemberships: [
    {
      id: "membership-1",
      world_id: "world-1",
      organization_id: "org-1",
      organization_key: "student-council",
      organization_name: "Student Council",
      agent_id: "agent-1",
      agent_key: "heroine",
      agent_display_name: "Heroine",
      role_title: "President",
      visibility: "public",
      loyalty: 80,
      influence: 70,
      responsibilities: ["agenda"],
      metadata: {},
      created_at: "2026-05-05T00:00:00.000Z",
      updated_at: "2026-05-05T00:00:00.000Z",
    },
  ],
  relationships: [
    {
      id: "relationship-1",
      world_id: "world-1",
      source_agent_id: "agent-1",
      source_agent_key: "heroine",
      source_display_name: "Heroine",
      target_agent_id: "agent-2",
      target_agent_key: "target",
      target_display_name: "Target",
      relationship_type: "friendship",
      affection: 42,
      trust: 35,
      hostility: 0,
      intimacy: 20,
      obligation: 10,
      rivalry: 0,
      debt: 0,
      metadata: { reason: "shared promise" },
      created_at: "2026-05-05T00:00:00.000Z",
      updated_at: "2026-05-05T00:00:00.000Z",
    },
  ],
  calendarEntries: [],
  memoryItems: [],
  memoryProfileSnapshot: null,
  agentRuns: [],
  agentPersona: null,
  agentObservations: [],
};
