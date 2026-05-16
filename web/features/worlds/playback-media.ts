import type {
  ReaderMediaDescriptor,
  ReaderMediaObjectDescriptor,
} from "@/lib/worlds/media";
import type {
  ConversationTurn,
  ConversationTurnPresentation,
} from "@/lib/worlds/types";

export type ResolvedTurnMedia = {
  image: ReaderMediaDescriptor | null;
  imageObject: ReaderMediaObjectDescriptor | null;
  audio: ReaderMediaDescriptor | null;
  audioObject: ReaderMediaObjectDescriptor | null;
};

export function resolveTurnMedia(
  turn: ConversationTurn,
  presentation: ConversationTurnPresentation | null,
  conversationId: string,
  media: ReaderMediaDescriptor[],
  mediaByAssetId: Map<string, ReaderMediaDescriptor>,
): ResolvedTurnMedia {
  const referenced = media.filter((item) =>
    item.references.some(
      (reference) =>
        (reference.ref_kind === "conversation_turn" && reference.ref_id === turn.id)
        || (reference.ref_kind === "conversation_session" && reference.ref_id === conversationId),
    ),
  );
  const image =
    assetFromId(mediaByAssetId, presentation?.composite_scene_asset_id, "image")
    ?? assetFromId(mediaByAssetId, presentation?.background_asset_id, "image")
    ?? preferredReferencedMedia(referenced, "image");
  const audio =
    assetFromId(mediaByAssetId, presentation?.tts_media_asset_id, "audio")
    ?? preferredReferencedMedia(referenced, "audio");
  return {
    image,
    imageObject: primaryObject(image),
    audio,
    audioObject: primaryObject(audio),
  };
}

export function emptyTurnMedia(): ResolvedTurnMedia {
  return {
    image: null,
    imageObject: null,
    audio: null,
    audioObject: null,
  };
}

export function speakerLabel(turn: ConversationTurn): string {
  if (turn.speaker_kind === "operator") {
    return "Operator";
  }
  return "Agent";
}

export function turnText(turn: ConversationTurn): string {
  if (turn.status !== "succeeded") {
    return "Turn unavailable.";
  }
  return turn.output_text ?? turn.input_text;
}

export function mediaSummary(media: ResolvedTurnMedia): string {
  const parts = [];
  if (media.image !== null) {
    parts.push("image");
  }
  if (media.audio !== null) {
    parts.push("audio");
  }
  return parts.length === 0 ? "none" : parts.join(", ");
}

function assetFromId(
  mediaByAssetId: Map<string, ReaderMediaDescriptor>,
  assetId: string | null | undefined,
  kind: "image" | "audio",
): ReaderMediaDescriptor | null {
  if (assetId === null || assetId === undefined) {
    return null;
  }
  const media = mediaByAssetId.get(assetId) ?? null;
  return media?.asset_kind === kind ? media : null;
}

function preferredReferencedMedia(
  media: ReaderMediaDescriptor[],
  kind: "image" | "audio",
): ReaderMediaDescriptor | null {
  return (
    media
      .filter((item) => item.asset_kind === kind)
      .sort((left, right) => mediaPriority(left) - mediaPriority(right))[0] ?? null
  );
}

function mediaPriority(media: ReaderMediaDescriptor): number {
  if (media.asset_role === "composite_image") {
    return 0;
  }
  if (media.asset_role === "scene_background") {
    return 1;
  }
  if (media.asset_role === "character_sprite") {
    return 2;
  }
  if (media.asset_role === "speech_audio") {
    return 0;
  }
  return 10;
}

function primaryObject(media: ReaderMediaDescriptor | null): ReaderMediaObjectDescriptor | null {
  return media?.objects[0] ?? null;
}
