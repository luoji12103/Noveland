"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { readerMediaObjectDownloadPath } from "@/lib/worlds/media";
import type {
  ReaderMediaDescriptor,
  ReaderMediaObjectDescriptor,
} from "@/lib/worlds/media";
import type { ConversationPlaybackData } from "@/lib/worlds/server";
import type {
  ConversationTurn,
  ConversationTurnPresentation,
} from "@/lib/worlds/types";

type ConversationPlaybackProps = {
  worldId: string;
  conversationId: string;
  data: ConversationPlaybackData;
};

type ResolvedTurnMedia = {
  image: ReaderMediaDescriptor | null;
  imageObject: ReaderMediaObjectDescriptor | null;
  audio: ReaderMediaDescriptor | null;
  audioObject: ReaderMediaObjectDescriptor | null;
};

export function ConversationPlayback({ worldId, conversationId, data }: ConversationPlaybackProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const activeTurn = data.turns[activeIndex] ?? null;
  const activePresentation = activeTurn === null ? null : data.presentationsByTurnId[activeTurn.id] ?? null;
  const mediaByAssetId = useMemo(
    () => new Map(data.media.map((item) => [item.asset_id, item])),
    [data.media],
  );
  const activeMedia =
    activeTurn === null || data.conversation === null
      ? emptyTurnMedia()
      : resolveTurnMedia(activeTurn, activePresentation, data.conversation.id, data.media, mediaByAssetId);

  if (data.selectedWorld === null || data.conversation === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{data.loadError ?? "Conversation not found."}</p>
      </section>
    );
  }

  const imageUrl =
    activeMedia.imageObject === null
      ? null
      : readerMediaObjectDownloadPath(activeMedia.imageObject.download_url);
  const audioUrl =
    activeMedia.audioObject === null
      ? null
      : readerMediaObjectDownloadPath(activeMedia.audioObject.download_url);

  return (
    <section className="management-section">
      {data.loadError !== null ? <p className="management-notice">{data.loadError}</p> : null}

      <section className="management-panel playback-grid" aria-labelledby="playback-title">
        <div className="playback-main">
          <div className="button-row">
            <Link className="secondary-button" href={`/worlds/${worldId}/reader`}>
              Back to reader
            </Link>
          </div>
          <h2 className="section-title" id="playback-title">
            Playback
          </h2>
          <p className="admin-section-copy">
            {data.conversation.title} · {data.conversation.status}
          </p>

          <div className="playback-stage">
            {imageUrl === null ? (
              <div className="playback-scene-empty">No reader-visible image for this turn.</div>
            ) : (
              <div
                aria-label="Reader-safe scene media"
                className="playback-scene-media"
                role="img"
                style={{ backgroundImage: `url(${imageUrl})` }}
              />
            )}
            <div className="playback-subtitle">
              {activeTurn === null ? (
                <p>No turns are available for playback.</p>
              ) : (
                <>
                  <p className="playback-speaker">
                    Turn {activeTurn.turn_index + 1} · {speakerLabel(activeTurn)}
                  </p>
                  <p>{turnText(activeTurn)}</p>
                </>
              )}
            </div>
          </div>

          <div className="playback-meta">
            <span>Render: {activePresentation?.render_state ?? "missing"}</span>
            <span>Emotion: {activePresentation?.emotion_key ?? "unset"}</span>
            <span>Media: {mediaSummary(activeMedia)}</span>
          </div>

          {audioUrl === null ? (
            <p className="management-notice">No reader-visible audio for this turn.</p>
          ) : (
            <audio aria-label="Turn audio" className="playback-audio" controls preload="none" src={audioUrl}>
              Audio playback is unavailable in this browser.
            </audio>
          )}
        </div>

        <aside className="playback-sidebar" aria-label="Playback turns">
          <h3>Turns</h3>
          <div className="playback-turn-list">
            {data.turns.length === 0 ? (
              <p>No turns are available.</p>
            ) : (
              data.turns.map((turn, index) => {
                const presentation = data.presentationsByTurnId[turn.id] ?? null;
                return (
                  <button
                    aria-pressed={index === activeIndex}
                    className="playback-turn-button"
                    key={turn.id}
                    onClick={() => setActiveIndex(index)}
                    type="button"
                  >
                    <span>Turn {turn.turn_index + 1}</span>
                    <small>
                      {speakerLabel(turn)} · {presentation?.render_state ?? "no presentation"}
                    </small>
                  </button>
                );
              })
            )}
          </div>
        </aside>
      </section>
    </section>
  );
}

function resolveTurnMedia(
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

function emptyTurnMedia(): ResolvedTurnMedia {
  return {
    image: null,
    imageObject: null,
    audio: null,
    audioObject: null,
  };
}

function speakerLabel(turn: ConversationTurn): string {
  if (turn.speaker_kind === "operator") {
    return "Operator";
  }
  return "Agent";
}

function turnText(turn: ConversationTurn): string {
  if (turn.status !== "succeeded") {
    return "Turn unavailable.";
  }
  return turn.output_text ?? turn.input_text;
}

function mediaSummary(media: ResolvedTurnMedia): string {
  const parts = [];
  if (media.image !== null) {
    parts.push("image");
  }
  if (media.audio !== null) {
    parts.push("audio");
  }
  return parts.length === 0 ? "none" : parts.join(", ");
}
