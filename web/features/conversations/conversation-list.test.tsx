import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", () => ({
  createConversation: vi.fn(),
}));

const assign = vi.fn();

import { ConversationList } from "@/features/conversations/conversation-list";
import { createConversation } from "@/lib/worlds/client";
import type { ConversationListData } from "@/lib/worlds/server";
import type { ConversationSession, World } from "@/lib/worlds/types";

describe("ConversationList", () => {
  afterEach(() => {
    vi.clearAllMocks();
    assign.mockReset();
  });

  it("encodes transcript links and create redirects for reserved route characters", async () => {
    vi.mocked(createConversation).mockResolvedValue(conversationWithId(CREATED_CONVERSATION_ID));
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { assign },
    });

    render(
      <ConversationList
        worldId={RESERVED_WORLD_ID}
        data={{
          ...conversationData,
          conversations: [conversationWithId(RESERVED_CONVERSATION_ID)],
        }}
      />,
    );

    expect(screen.getByRole("link", { name: "Open transcript" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/conversations/${encodeURIComponent(
        RESERVED_CONVERSATION_ID,
      )}`,
    );

    fireEvent.change(screen.getByPlaceholderText("session-key"), {
      target: { value: "new-session" },
    });
    fireEvent.change(screen.getByPlaceholderText("Conversation title"), {
      target: { value: "New conversation" },
    });
    fireEvent.change(screen.getByPlaceholderText("Objective"), {
      target: { value: "Continue safely." },
    });
    fireEvent.change(screen.getByPlaceholderText("Opening prompt"), {
      target: { value: "Begin." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create conversation" }));

    await waitFor(() => {
      expect(createConversation).toHaveBeenCalledWith(
        RESERVED_WORLD_ID,
        expect.objectContaining({ session_key: "new-session" }),
      );
    });
    expect(assign).toHaveBeenCalledWith(
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/conversations/${encodeURIComponent(
        CREATED_CONVERSATION_ID,
      )}`,
    );
  });
});

const RESERVED_WORLD_ID = "world/conversation?scope=true#frag";
const RESERVED_CONVERSATION_ID = "conversation/live?debug=true#frag";
const CREATED_CONVERSATION_ID = "conversation/created?debug=true#frag";

const world: World = {
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
};

const conversationData: ConversationListData = {
  worlds: [world],
  selectedWorld: world,
  scenes: [],
  agents: [],
  conversations: [],
  canManageSelectedWorld: true,
  loadError: null,
};

function conversationWithId(id: string): ConversationSession {
  return {
    id,
    world_id: "world-1",
    worldline_id: "worldline-1",
    scene_id: null,
    session_key: "manual-chain",
    title: "Manual Chain",
    scope_type: "world",
    mode: "manual_chain",
    status: "completed",
    objective: "Summarize the exchange.",
    opening_prompt: "Start.",
    max_turns: 4,
    next_turn_index: 2,
    policy: {
      error_policy: "fail_session",
      max_consecutive_failed_turns: 1,
      loop_guard_window: 4,
      repeat_output_threshold: 2,
      speaker_policy: "round_robin",
      manual_next_agent_id: null,
      participant_repeat_cooldown: 0,
      min_enabled_participants: 1,
      max_turn_budget: null,
    },
    writer_config: {
      provider_profile_id: null,
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
    terminal_reason: "max_turns_reached",
    created_at: "2026-04-21T00:00:00.000Z",
    updated_at: "2026-04-21T00:02:00.000Z",
  };
}
