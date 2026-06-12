import { describe, expect, it } from "vitest";

import { resolveTurnMedia } from "@/features/worlds/playback-media";
import type { ReaderMediaDescriptor } from "@/lib/worlds/media";
import type {
  ConversationTurn,
  ConversationTurnPresentation,
} from "@/lib/worlds/types";

describe("resolveTurnMedia", () => {
  it("does not substitute referenced media when explicit presentation media is unresolved", () => {
    const media = [
      mediaDescriptor("referenced-image", "image", "scene_background", 0),
      mediaDescriptor("referenced-audio", "audio", "speech_audio", 1),
    ];
    const resolved = resolveTurnMedia(
      turn,
      presentation({
        composite_scene_asset_id: "missing-image",
        tts_media_asset_id: "missing-audio",
      }),
      CONVERSATION_ID,
      media,
      mediaMap(media),
    );

    expect(resolved.image).toBeNull();
    expect(resolved.imageObject).toBeNull();
    expect(resolved.audio).toBeNull();
    expect(resolved.audioObject).toBeNull();
  });

  it("uses referenced media when the presentation has no explicit media ids", () => {
    const media = [
      mediaDescriptor("referenced-image", "image", "scene_background", 0),
      mediaDescriptor("referenced-audio", "audio", "speech_audio", 1),
    ];
    const resolved = resolveTurnMedia(
      turn,
      presentation(),
      CONVERSATION_ID,
      media,
      mediaMap(media),
    );

    expect(resolved.image?.asset_id).toBe("referenced-image");
    expect(resolved.imageObject?.object_id).toBe("referenced-image-object");
    expect(resolved.audio?.asset_id).toBe("referenced-audio");
    expect(resolved.audioObject?.object_id).toBe("referenced-audio-object");
  });

  it("keeps resolving alternate explicit image ids before blocking referenced fallback", () => {
    const media = [
      mediaDescriptor("explicit-background", "image", "scene_background", 0),
      mediaDescriptor("referenced-image", "image", "composite_image", 1),
    ];
    const resolved = resolveTurnMedia(
      turn,
      presentation({
        composite_scene_asset_id: "missing-composite",
        background_asset_id: "explicit-background",
      }),
      CONVERSATION_ID,
      media,
      mediaMap(media),
    );

    expect(resolved.image?.asset_id).toBe("explicit-background");
    expect(resolved.imageObject?.object_id).toBe("explicit-background-object");
  });
});

const CONVERSATION_ID = "conversation-1";

const turn: ConversationTurn = {
  id: "turn-1",
  session_id: CONVERSATION_ID,
  turn_index: 0,
  speaker_kind: "agent",
  speaker_agent_id: "agent-1",
  input_text: "Input.",
  output_text: "Output.",
  status: "succeeded",
  run_id: null,
  error_text: null,
  created_at: "2026-04-17T00:02:30.000Z",
  updated_at: "2026-04-17T00:02:30.000Z",
};

function presentation(
  overrides: Partial<ConversationTurnPresentation> = {},
): ConversationTurnPresentation {
  return {
    id: "presentation-1",
    world_id: "world-1",
    worldline_id: "worldline-1",
    conversation_id: CONVERSATION_ID,
    turn_id: turn.id,
    speaker_agent_id: "agent-1",
    emotion_key: "happy",
    emotion_intensity: 0.8,
    sprite_set_id: null,
    sprite_variant_id: null,
    voice_profile_id: null,
    tts_media_asset_id: null,
    background_asset_id: null,
    composite_scene_asset_id: null,
    transcript_id: null,
    presentation_json: {},
    render_state: "speech_rendered",
    created_at: "2026-04-17T00:02:40.000Z",
    updated_at: "2026-04-17T00:02:41.000Z",
    ...overrides,
  };
}

function mediaMap(media: ReaderMediaDescriptor[]): Map<string, ReaderMediaDescriptor> {
  return new Map(media.map((item) => [item.asset_id, item]));
}

function mediaDescriptor(
  assetId: string,
  assetKind: "image" | "audio",
  assetRole: string,
  displayOrder: number,
): ReaderMediaDescriptor {
  const contentType = assetKind === "image" ? "image/png" : "audio/wav";
  return {
    asset_id: assetId,
    world_id: "world-1",
    worldline_id: "worldline-1",
    asset_kind: assetKind,
    asset_role: assetRole,
    visibility: "reader_visible",
    title: null,
    description: null,
    content_type: contentType,
    size: 12,
    width: assetKind === "image" ? 100 : null,
    height: assetKind === "image" ? 80 : null,
    duration_ms: assetKind === "audio" ? 1000 : null,
    objects: [
      {
        object_id: `${assetId}-object`,
        object_role: "original",
        content_type: contentType,
        size: 12,
        checksum_sha256: "a".repeat(64),
        width: assetKind === "image" ? 100 : null,
        height: assetKind === "image" ? 80 : null,
        duration_ms: assetKind === "audio" ? 1000 : null,
        sample_rate_hz: assetKind === "audio" ? 24000 : null,
        audio_channels: assetKind === "audio" ? 1 : null,
        download_url: `/worlds/world-1/reader/media/worldlines/worldline-1/objects/${assetId}-object/download`,
      },
    ],
    references: [
      {
        reference_id: `${assetId}-reference`,
        ref_kind: "conversation_turn",
        ref_id: turn.id,
        ref_role: "output",
        display_order: displayOrder,
      },
    ],
    created_at: "2026-04-17T00:02:40.000Z",
    updated_at: "2026-04-17T00:02:40.000Z",
  };
}
