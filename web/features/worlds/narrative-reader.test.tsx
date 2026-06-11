import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { subscribeToEventStream as subscribeToEventStreamFn } from "@/lib/realtime";
import type { WorldStreamPayload } from "@/lib/worlds/types";

const { subscribeToEventStream } = vi.hoisted(() => ({
  subscribeToEventStream: vi.fn<typeof subscribeToEventStreamFn>(() => () => {}),
}));

vi.mock("@/lib/realtime", async () => {
  const actual = await vi.importActual<typeof import("@/lib/realtime")>("@/lib/realtime");
  return {
    ...actual,
    subscribeToEventStream,
  };
});

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
    const data = readerListDataWithReservedIds();

    render(<NarrativeReaderList worldId={RESERVED_WORLD_ID} data={data} />);

    expect(screen.getByRole("heading", { name: "Reader filters" })).toBeVisible();
    expect(screen.getByDisplayValue("summary")).toBeVisible();
    expect(screen.getByDisplayValue("conversation_summary")).toBeVisible();
    expect(screen.getByDisplayValue("Conversation")).toBeVisible();
    expect(screen.getByDisplayValue("Publication timeline")).toBeVisible();
    expect(screen.getByRole("link", { name: "Manual Chain summary" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/reader/${encodeURIComponent(RESERVED_ARTIFACT_ID)}`,
    );
    expect(screen.getByText("Conversation: Manual Chain")).toBeVisible();
    expect(screen.getAllByText("Published Apr 21, 2026, 12:03 AM")[0]).toBeVisible();
    expect(screen.getByText("Timeline: published Apr 21, 2026, 12:03 AM")).toBeVisible();
  });

  it("renders artifact detail with source conversation link", () => {
    const data = readerDetailDataWithReservedIds();

    render(<NarrativeReaderDetail worldId={RESERVED_WORLD_ID} data={data} />);

    expect(screen.getByRole("heading", { name: "Manual Chain summary" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to reader" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/reader`,
    );
    expect(screen.getByRole("link", { name: "Open source conversation" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/conversations/${encodeURIComponent(
        RESERVED_CONVERSATION_ID,
      )}`,
    );
    expect(screen.getByRole("link", { name: "Open playback" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/reader/conversations/${encodeURIComponent(
        RESERVED_CONVERSATION_ID,
      )}/playback`,
    );
    expect(screen.getByText("Summary body")).toBeVisible();
    expect(screen.getByText("Published Apr 21, 2026, 12:03 AM")).toBeVisible();
    expect(screen.getByText(/generation_mode/)).toBeVisible();
  });


  it("encodes reader EventSource paths for reserved world identifiers", () => {
    render(<NarrativeReaderList worldId={RESERVED_WORLD_ID} data={listData} />);

    expect(subscribeToEventStream.mock.calls[0]?.[0]).toBe(
      `/api/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/stream`,
    );
  });

  it("merges published stream updates into the reader list", () => {
    subscribeToEventStream.mockImplementation(
      ((_, handler) => {
        handler({
          cursor: "cursor-streamed",
          event_type: "world.delta",
          occurred_at: "2026-04-21T00:04:00.000Z",
          world_id: "world-1",
          conversation_id: null,
          payload: {
            diagnostics: [],
            agent_runs: [],
            narrative_artifacts: [
              {
                ...artifacts[0],
                id: "artifact-streamed",
                title: "Streamed published summary",
                publication: {
                  ...artifacts[0].publication,
                  artifact_id: "artifact-streamed",
                },
              },
            ],
            conversations: [],
          },
        });
        return () => {};
      }) satisfies typeof subscribeToEventStreamFn<WorldStreamPayload>,
    );

    render(<NarrativeReaderList worldId="world-1" data={listData} />);

    expect(screen.getByRole("link", { name: "Streamed published summary" })).toBeVisible();
  });
});

const RESERVED_WORLD_ID = "world/reader?mode=list#frag";
const RESERVED_ARTIFACT_ID = "artifact/reader?draft=false#frag";
const RESERVED_CONVERSATION_ID = "conversation/source?mode=play#frag";

function readerListDataWithReservedIds(): NarrativeReaderListData {
  const conversation = { ...conversations[0], id: RESERVED_CONVERSATION_ID };
  const artifact = {
    ...artifacts[0],
    id: RESERVED_ARTIFACT_ID,
    source_conversation_id: RESERVED_CONVERSATION_ID,
    publication: {
      ...artifacts[0].publication,
      artifact_id: RESERVED_ARTIFACT_ID,
      source_draft_id: RESERVED_ARTIFACT_ID,
    },
  };

  return {
    ...listData,
    conversations: [conversation],
    narrativeArtifacts: [artifact],
  };
}

function readerDetailDataWithReservedIds(): NarrativeReaderDetailData {
  const list = readerListDataWithReservedIds();

  return {
    ...detailData,
    conversations: list.conversations,
    artifact: list.narrativeArtifacts[0],
  };
}

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
      speaker_policy: "round_robin" as const,
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
      target_length: "standard" as const,
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
      memory_query_strategy: "prompt" as const,
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
    publication: {
      id: "publication-1",
      world_id: "world-1",
      artifact_id: "artifact-1",
      source_draft_id: "artifact-1",
      status: "published" as const,
      reader_visible: true,
      metadata: { channel: "reader" },
      published_at: "2026-04-21T00:03:00.000Z",
      unpublished_at: null,
      published_by_user_id: "user-1",
      created_at: "2026-04-21T00:03:00.000Z",
      updated_at: "2026-04-21T00:03:00.000Z",
    },
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
  selectedSearch: "summary",
  selectedSourceKind: "conversation",
  selectedOrderBy: "published_at",
  loadError: null,
};

const detailData: NarrativeReaderDetailData = {
  worlds: listData.worlds,
  selectedWorld: listData.selectedWorld,
  conversations,
  artifact: artifacts[0],
  loadError: null,
};
