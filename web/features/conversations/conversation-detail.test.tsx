import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>("@/lib/worlds/client");
  return {
    ...actual,
    updateConversation: vi.fn(),
    stopConversation: vi.fn(),
    replaceConversationParticipants: vi.fn(),
    seedConversation: vi.fn(),
    advanceConversation: vi.fn(),
    startConversation: vi.fn(),
    pauseConversation: vi.fn(),
    resumeConversation: vi.fn(),
  };
});

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import { ConversationDetail } from "@/features/conversations/conversation-detail";
import {
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

    render(
      <ConversationDetail
        worldId="world-1"
        conversationId="conversation-1"
        data={adminData}
      />,
    );

    expect(screen.getByText("Conversation diagnostics")).toBeInTheDocument();
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
        },
      });
    });
    expect(refresh).toHaveBeenCalled();
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
    is_active: true,
  },
  scenes: [],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: null,
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
};

const readOnlyData: ConversationDetailData = {
  ...adminData,
  canManageSelectedWorld: false,
  diagnostics: [],
};
