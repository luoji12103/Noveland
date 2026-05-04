import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>("@/lib/worlds/client");
  return {
    ...actual,
    getConversationMemorySummary: vi.fn(),
    getConversationSpeakerPreview: vi.fn(),
    previewConversationNarrativePrompt: vi.fn(),
    updateConversation: vi.fn(),
    stopConversation: vi.fn(),
    replaceConversationParticipants: vi.fn(),
    seedConversation: vi.fn(),
    advanceConversation: vi.fn(),
    generateConversationNarrativeArtifacts: vi.fn(),
    startConversation: vi.fn(),
    pauseConversation: vi.fn(),
    resumeConversation: vi.fn(),
  };
});

vi.mock("@/lib/realtime", () => ({
  createConversationLiveSocket: vi.fn(() => ({
    close: vi.fn(),
    readyState: 3,
  })),
  mergeById: <T extends { id: string }>(current: T[], incoming: T[]) => {
    const byId = new Map(current.map((item) => [item.id, item]));
    for (const item of incoming) {
      byId.set(item.id, item);
    }
    return Array.from(byId.values());
  },
  nextRequestId: vi.fn(() => "request-1"),
  subscribeToEventStream: vi.fn(() => () => {}),
}));

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import { ConversationDetail } from "@/features/conversations/conversation-detail";
import {
  generateConversationNarrativeArtifacts,
  getConversationMemorySummary,
  getConversationSpeakerPreview,
  previewConversationNarrativePrompt,
  stopConversation,
  updateConversation,
} from "@/lib/worlds/client";
import type { ConversationDetailData } from "@/lib/worlds/server";

describe("ConversationDetail", () => {
  afterEach(() => {
    vi.clearAllMocks();
    refresh.mockReset();
  });

  it("renders policy and diagnostics for admins and updates policy", async () => {
    vi.mocked(updateConversation).mockResolvedValue(adminData.conversation!);
    vi.mocked(getConversationSpeakerPreview).mockResolvedValue({
      session_id: "conversation-1",
      policy_mode: "round_robin",
      selected_agent_id: "agent-1",
      selected_reason: "round-robin turn order",
      candidates: [],
    });
    vi.mocked(getConversationMemorySummary).mockResolvedValue({
      ...adminData.conversation!.memory_config,
      latest_backend: "local_pgvector",
      latest_hit_count: 2,
      latest_retrieval_enabled: true,
      latest_write_enabled: true,
      recent_memory_diagnostics: [],
    });

    render(
      <ConversationDetail
        worldId="world-1"
        conversationId="conversation-1"
        data={adminData}
      />,
    );

    expect(screen.getByText("Conversation diagnostics")).toBeInTheDocument();
    expect(
      screen.getByText("Recent provider diagnostics may explain degraded conversation behavior."),
    ).toBeInTheDocument();
    expect(screen.getByText("Conversation turn skipped after speaker failure.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Conversation error policy"), {
      target: { value: "retry_once_then_skip" },
    });
    fireEvent.change(screen.getByLabelText("Conversation repeat output threshold"), {
      target: { value: "4" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save policy" }));

    await waitFor(() => {
      expect(updateConversation).toHaveBeenCalledWith("world-1", "conversation-1", {
        policy: {
          error_policy: "retry_once_then_skip",
          max_consecutive_failed_turns: 2,
          loop_guard_window: 4,
          repeat_output_threshold: 4,
          speaker_policy: "round_robin",
          manual_next_agent_id: null,
          participant_repeat_cooldown: 0,
          min_enabled_participants: 1,
          max_turn_budget: null,
        },
      });
    });
    expect(refresh).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Preview speaker" }));

    await waitFor(() => {
      expect(getConversationSpeakerPreview).toHaveBeenCalledWith("world-1", "conversation-1");
    });
    expect(screen.getByText("Next speaker preview")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh memory summary" }));

    await waitFor(() => {
      expect(getConversationMemorySummary).toHaveBeenCalledWith("world-1", "conversation-1");
    });
    expect(screen.getByText("Memory summary")).toBeInTheDocument();
  });

  it("updates writer config and generates conversation narrative", async () => {
    vi.mocked(updateConversation).mockResolvedValue(adminData.conversation!);
    vi.mocked(generateConversationNarrativeArtifacts).mockResolvedValue(
      adminData.narrativeArtifacts,
    );
    vi.mocked(previewConversationNarrativePrompt).mockResolvedValue({
      world_id: "world-1",
      conversation_id: "conversation-1",
      artifact_set: "summary_and_chapter",
      provider_profile_id: "profile-1",
      provider_profile_key: "runtime-profile",
      writer_plugin_identifier: "builtin.default_narrative_writer",
      prompt_text: "Writer controls:\n\nPrompt body",
      source_turn_count: 2,
      existing_artifact_count: 0,
      warnings: [],
    });

    render(
      <ConversationDetail
        worldId="world-1"
        conversationId="conversation-1"
        data={adminData}
      />,
    );

    fireEvent.click(screen.getByLabelText("Auto generate on complete"));
    fireEvent.click(screen.getByRole("button", { name: "Save writer config" }));

    await waitFor(() => {
      expect(updateConversation).toHaveBeenCalledWith("world-1", "conversation-1", {
        writer_config: {
          provider_profile_id: "profile-1",
          writer_plugin_identifier: "builtin.default_narrative_writer",
          writer_plugin_config: {},
          auto_generate_on_complete: false,
          generate_summary: true,
          generate_chapter: true,
          style_guide: "",
          target_length: "standard",
          source_constraints: "",
          include_prompt_preview: true,
        },
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Preview narrative prompt" }));
    await waitFor(() => {
      expect(previewConversationNarrativePrompt).toHaveBeenCalledWith(
        "world-1",
        "conversation-1",
        "summary_and_chapter",
        "profile-1",
      );
    });
    expect(screen.getByText("Narrative prompt preview")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Generate summary + chapter" }));

    await waitFor(() => {
      expect(generateConversationNarrativeArtifacts).toHaveBeenCalledWith(
        "world-1",
        "conversation-1",
        "summary_and_chapter",
        "profile-1",
      );
    });
    expect(screen.getByText("Conversation summary")).toBeInTheDocument();
  });

  it("stops a conversation and hides admin controls for read-only members", async () => {
    vi.mocked(stopConversation).mockResolvedValue({
      ...adminData.conversation!,
      status: "stopped",
      terminal_reason: "operator_stopped",
    });

    const { rerender } = render(
      <ConversationDetail
        worldId="world-1"
        conversationId="conversation-1"
        data={adminData}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));

    await waitFor(() => {
      expect(stopConversation).toHaveBeenCalledWith("world-1", "conversation-1");
    });

    rerender(
      <ConversationDetail
        worldId="world-1"
        conversationId="conversation-1"
        data={readOnlyData}
      />,
    );

    expect(screen.getByText("Read-only transcript access.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save policy" })).not.toBeInTheDocument();
    expect(screen.queryByText("Conversation diagnostics")).not.toBeInTheDocument();
  });
});

const adminData: ConversationDetailData = {
  worlds: [
    {
      id: "world-1",
      owner_user_id: "user-1",
      slug: "world-1",
      name: "World 1",
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
    slug: "world-1",
    name: "World 1",
    description: null,
    rules_config: {},
    memory_backend_profile_id: null,
    memory_plugin_identifier: "builtin.local_pgvector_memory",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.default_world_rules",
    world_rules_plugin_config: {},
    is_active: true,
  },
  scenes: [],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: null,
      source_preset_id: null,
      agent_key: "guide",
      display_name: "Guide",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
  ],
  conversations: [],
  canManageSelectedWorld: true,
  loadError: null,
  conversation: {
    id: "conversation-1",
    world_id: "world-1",
    scene_id: null,
    session_key: "scene-chat",
    title: "Scene chat",
    scope_type: "world",
    mode: "manual_chain",
    status: "draft",
    objective: "Keep it moving.",
    opening_prompt: "Start here.",
    max_turns: 6,
    next_turn_index: 1,
    policy: {
      error_policy: "retry_once_then_fail",
      max_consecutive_failed_turns: 2,
      loop_guard_window: 4,
      repeat_output_threshold: 3,
      speaker_policy: "round_robin",
      manual_next_agent_id: null,
      participant_repeat_cooldown: 0,
      min_enabled_participants: 1,
      max_turn_budget: null,
    },
    writer_config: {
      provider_profile_id: "profile-1",
      writer_plugin_identifier: "builtin.default_narrative_writer",
      writer_plugin_config: {},
      auto_generate_on_complete: true,
      generate_summary: true,
      generate_chapter: true,
      style_guide: "",
      target_length: "standard",
      source_constraints: "",
      include_prompt_preview: true,
    },
    memory_config: {
      write_turn_memory: true,
      retrieve_memory: true,
      max_context_items: 5,
      query_window: 4,
      include_recent_turns: true,
      include_agent_observations: true,
      memory_query_strategy: "prompt",
    },
    terminal_reason: null,
    created_at: "2026-04-21T00:00:00.000Z",
    updated_at: "2026-04-21T00:00:01.000Z",
  },
  participants: [
    {
      id: "participant-1",
      session_id: "conversation-1",
      agent_id: "agent-1",
      turn_order: 0,
      is_enabled: true,
      created_at: "2026-04-21T00:00:00.000Z",
      updated_at: "2026-04-21T00:00:00.000Z",
    },
  ],
  turns: [
    {
      id: "turn-1",
      session_id: "conversation-1",
      turn_index: 0,
      speaker_kind: "agent",
      speaker_agent_id: "agent-1",
      input_text: "Prompt",
      output_text: "Reply",
      status: "succeeded",
      run_id: "run-1",
      error_text: null,
      created_at: "2026-04-21T00:00:00.000Z",
      updated_at: "2026-04-21T00:00:00.000Z",
    },
  ],
  diagnostics: [
    {
      id: "diagnostic-1",
      severity: "warning",
      component: "conversation",
      event_type: "conversation.turn_skipped",
      message: "Conversation turn skipped after speaker failure.",
      details: { conversation_id: "conversation-1" },
      occurred_at: "2026-04-21T00:00:02.000Z",
      world_id: "world-1",
      agent_id: "agent-1",
      run_id: "run-1",
      provider_profile_id: null,
      created_at: "2026-04-21T00:00:02.000Z",
    },
  ],
  diagnosticsSummary: {
    session_status: "running",
    terminal_reason: null,
    last_turn_status: "skipped",
    last_turn_error: "upstream timeout",
    provider_diagnostic_count: 1,
    memory_diagnostic_count: 0,
    recent_diagnostics: [],
    operator_message: "Recent provider diagnostics may explain degraded conversation behavior.",
  },
  narrativeArtifacts: [
    {
      id: "artifact-1",
      world_id: "world-1",
      agent_id: null,
      source_run_id: null,
      source_conversation_id: "conversation-1",
      title: "Conversation summary",
      content: "Summary body",
      artifact_kind: "conversation_summary",
      metadata: { generation_mode: "manual" },
      created_at: "2026-04-21T00:00:03.000Z",
      publication: null,
    },
  ],
  narrativeWriterPlugins: [
    {
      identifier: "builtin.default_narrative_writer",
      category: "narrative_writer",
      version: "0.1.0",
      config_schema: {},
      capabilities: [],
      built_in: true,
    },
  ],
};

const readOnlyData: ConversationDetailData = {
  ...adminData,
  canManageSelectedWorld: false,
  diagnostics: [],
  diagnosticsSummary: null,
};
