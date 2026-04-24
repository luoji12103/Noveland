import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  NarrativeReaderDetail,
  NarrativeReaderList,
} from "@/features/worlds/narrative-reader";
import type {
  NarrativeReaderDetailData,
  NarrativeReaderListData,
} from "@/lib/worlds/server";

describe("narrative reader", () => {
  it("renders reader list filters and artifact links", () => {
    render(<NarrativeReaderList worldId="world-1" data={listData} />);

    expect(screen.getByRole("heading", { name: "Reader filters" })).toBeVisible();
    expect(screen.getByDisplayValue("conversation_summary")).toBeVisible();
    expect(screen.getByRole("link", { name: "Manual Chain summary" })).toHaveAttribute(
      "href",
      "/worlds/world-1/reader/artifact-1",
    );
    expect(screen.getByText("Conversation: Manual Chain")).toBeVisible();
  });

  it("renders artifact detail with source conversation link", () => {
    render(<NarrativeReaderDetail worldId="world-1" data={detailData} />);

    expect(screen.getByRole("heading", { name: "Manual Chain summary" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to reader" })).toHaveAttribute(
      "href",
      "/worlds/world-1/reader",
    );
    expect(screen.getByRole("link", { name: "Open source conversation" })).toHaveAttribute(
      "href",
      "/worlds/world-1/conversations/conversation-1",
    );
    expect(screen.getByText("Summary body")).toBeVisible();
    expect(screen.getByText(/generation_mode/)).toBeVisible();
  });
});

const conversations = [
  {
    id: "conversation-1",
    world_id: "world-1",
    scene_id: null,
    session_key: "manual-chain",
    title: "Manual Chain",
    scope_type: "world" as const,
    mode: "manual_chain" as const,
    status: "completed" as const,
    objective: "Summarize the exchange.",
    opening_prompt: "Start.",
    max_turns: 4,
    next_turn_index: 2,
    policy: {
      error_policy: "fail_session" as const,
      max_consecutive_failed_turns: 1,
      loop_guard_window: 4,
      repeat_output_threshold: 2,
    },
    writer_config: {
      provider_profile_id: null,
      writer_plugin_identifier: "builtin.default_narrative_writer",
      writer_plugin_config: {},
      auto_generate_on_complete: true,
      generate_summary: true,
      generate_chapter: true,
    },
    memory_config: {
      write_turn_memory: true,
      retrieve_memory: true,
      max_context_items: 5,
      query_window: 4,
    },
    terminal_reason: "max_turns_reached" as const,
    created_at: "2026-04-21T00:00:00.000Z",
    updated_at: "2026-04-21T00:02:00.000Z",
  },
];

const artifacts = [
  {
    id: "artifact-1",
    world_id: "world-1",
    agent_id: null,
    source_run_id: null,
    source_conversation_id: "conversation-1",
    title: "Manual Chain summary",
    content: "Summary body",
    artifact_kind: "conversation_summary" as const,
    metadata: {
      generation_mode: "manual",
      scope_type: "world",
    },
    created_at: "2026-04-21T00:03:00.000Z",
  },
];

const listData: NarrativeReaderListData = {
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
  conversations,
  narrativeArtifacts: artifacts,
  selectedArtifactKind: "conversation_summary",
  selectedConversationId: "conversation-1",
  loadError: null,
};

const detailData: NarrativeReaderDetailData = {
  worlds: listData.worlds,
  selectedWorld: listData.selectedWorld,
  conversations,
  artifact: artifacts[0],
  loadError: null,
};
