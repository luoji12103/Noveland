import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConversationSceneView } from "@/features/worlds/conversation-scene-view";
import type { ConversationPlaybackData } from "@/lib/worlds/server";

describe("ConversationSceneView", () => {
  it("renders a focused scene with reader-safe image and audio", () => {
    render(<ConversationSceneView worldId="world-1" conversationId="conversation-1" data={sceneData} />);

    fireEvent.click(screen.getByRole("button", { name: /Turn 2/ }));

    expect(screen.getByRole("heading", { name: "Scene view" })).toBeVisible();
    expect(screen.getByText("Guide replies to the reader.")).toBeVisible();
    expect(screen.getByLabelText("Reader-safe scene image")).toHaveStyle({
      backgroundImage:
        "url(/api/worlds/world-1/reader/media/objects/composite-object-1/download)",
    });
    expect(screen.getByLabelText("Scene audio")).toHaveAttribute(
      "src",
      "/api/worlds/world-1/reader/media/objects/audio-object-1/download",
    );
    expect(serializedDocument()).not.toMatch(
      /storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret|\/var\/|\/tmp\//i,
    );
  });

  it("encodes playback route links for reserved identifiers", () => {
    render(
      <ConversationSceneView
        worldId={RESERVED_WORLD_ID}
        conversationId={RESERVED_CONVERSATION_ID}
        data={sceneData}
      />,
    );

    expect(screen.getByRole("link", { name: "Reader" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/reader`,
    );
    expect(screen.getByRole("link", { name: "Playback" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/reader/conversations/${encodeURIComponent(
        RESERVED_CONVERSATION_ID,
      )}/playback`,
    );
  });

  it("switches turns and shows deterministic missing-media fallbacks", () => {
    render(<ConversationSceneView worldId="world-1" conversationId="conversation-1" data={sceneData} />);

    expect(screen.getByText("Seed the conversation.")).toBeVisible();
    expect(screen.getByText("No reader-visible scene image for this turn.")).toBeVisible();
    expect(screen.getByText("Scene dialogue is still available. No media diagnostics are exposed here.")).toBeVisible();
    expect(screen.getByText("Audio is not available for this turn. Continue with the visible dialogue.")).toBeVisible();
    expect(screen.queryByRole("button", { name: /edit|compose|generate/i })).toBeNull();
  });

  it("shows a safe empty state", () => {
    render(
      <ConversationSceneView
        worldId="world-1"
        conversationId="missing"
        data={{ ...sceneData, conversation: null, turns: [], loadError: "Conversation not found." }}
      />,
    );

    expect(screen.getByText("Conversation not found.")).toBeVisible();
  });
});

function serializedDocument(): string {
  return document.body.textContent ?? "";
}

const RESERVED_WORLD_ID = "world/reader?mode=scene#frag";
const RESERVED_CONVERSATION_ID = "conversation/live?debug=true#frag";

const sceneData: ConversationPlaybackData = {
  worlds: [],
  selectedWorld: {
    id: "world-1",
    owner_user_id: "user-1",
    slug: "world-one",
    name: "World One",
    description: null,
    rules_config: {},
    memory_backend_profile_id: null,
    memory_plugin_identifier: "builtin.mem0",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.rules",
    world_rules_plugin_config: {},
    is_active: true,
  },
  conversations: [],
  conversation: {
    id: "conversation-1",
    world_id: "world-1",
    worldline_id: "worldline-1",
    scene_id: null,
    session_key: "seed",
    title: "Seed Reader Conversation",
    scope_type: "world",
    mode: "manual_chain",
    status: "completed",
    objective: "Seed playback.",
    opening_prompt: "Begin.",
    max_turns: 2,
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
      target_length: "brief",
      source_constraints: "",
      include_prompt_preview: false,
    },
    memory_config: {
      write_turn_memory: true,
      retrieve_memory: true,
      max_context_items: 5,
      query_window: 4,
      include_recent_turns: true,
      include_agent_observations: true,
      memory_query_strategy: "transcript",
    },
    terminal_reason: "max_turns_reached",
    created_at: "2026-04-17T00:02:00.000Z",
    updated_at: "2026-04-17T00:03:04.000Z",
  },
  turns: [
    {
      id: "turn-1",
      session_id: "conversation-1",
      turn_index: 0,
      speaker_kind: "operator",
      speaker_agent_id: null,
      input_text: "Seed the conversation.",
      output_text: "Seed the conversation.",
      status: "succeeded",
      run_id: null,
      error_text: null,
      created_at: "2026-04-17T00:02:30.000Z",
      updated_at: "2026-04-17T00:02:30.000Z",
    },
    {
      id: "turn-2",
      session_id: "conversation-1",
      turn_index: 1,
      speaker_kind: "agent",
      speaker_agent_id: "agent-1",
      input_text: "Seed the conversation.",
      output_text: "Guide replies to the reader.",
      status: "succeeded",
      run_id: null,
      error_text: null,
      created_at: "2026-04-17T00:02:31.000Z",
      updated_at: "2026-04-17T00:02:31.000Z",
    },
  ],
  presentationsByTurnId: {
    "turn-1": null,
    "turn-2": {
      id: "presentation-2",
      world_id: "world-1",
      worldline_id: "worldline-1",
      conversation_id: "conversation-1",
      turn_id: "turn-2",
      speaker_agent_id: "agent-1",
      emotion_key: "happy",
      emotion_intensity: 0.8,
      sprite_set_id: "sprite-set-1",
      sprite_variant_id: "variant-1",
      voice_profile_id: "voice-1",
      tts_media_asset_id: "audio-asset-1",
      background_asset_id: "background-asset-1",
      composite_scene_asset_id: "composite-asset-1",
      transcript_id: null,
      presentation_json: { caption: "safe caption" },
      render_state: "speech_rendered",
      created_at: "2026-04-17T00:02:40.000Z",
      updated_at: "2026-04-17T00:02:41.000Z",
    },
  },
  media: [
    {
      asset_id: "composite-asset-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      asset_kind: "image",
      asset_role: "composite_image",
      visibility: "reader_visible",
      title: null,
      description: null,
      content_type: "image/png",
      size: 12,
      width: 100,
      height: 80,
      duration_ms: null,
      objects: [
        {
          object_id: "composite-object-1",
          object_role: "original",
          content_type: "image/png",
          size: 12,
          checksum_sha256: "a".repeat(64),
          width: 100,
          height: 80,
          duration_ms: null,
          sample_rate_hz: null,
          audio_channels: null,
          download_url: "/worlds/world-1/reader/media/objects/composite-object-1/download",
        },
      ],
      references: [
        {
          reference_id: "ref-1",
          ref_kind: "conversation_turn",
          ref_id: "turn-2",
          ref_role: "output",
          display_order: 0,
        },
      ],
      created_at: "2026-04-17T00:02:40.000Z",
      updated_at: "2026-04-17T00:02:40.000Z",
    },
    {
      asset_id: "audio-asset-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      asset_kind: "audio",
      asset_role: "speech_audio",
      visibility: "reader_visible",
      title: null,
      description: null,
      content_type: "audio/wav",
      size: 20,
      width: null,
      height: null,
      duration_ms: 1000,
      objects: [
        {
          object_id: "audio-object-1",
          object_role: "original",
          content_type: "audio/wav",
          size: 20,
          checksum_sha256: "b".repeat(64),
          width: null,
          height: null,
          duration_ms: 1000,
          sample_rate_hz: 24000,
          audio_channels: 1,
          download_url: "/worlds/world-1/reader/media/objects/audio-object-1/download",
        },
      ],
      references: [
        {
          reference_id: "ref-2",
          ref_kind: "conversation_turn",
          ref_id: "turn-2",
          ref_role: "output",
          display_order: 1,
        },
      ],
      created_at: "2026-04-17T00:02:41.000Z",
      updated_at: "2026-04-17T00:02:41.000Z",
    },
  ],
  loadError: null,
};
