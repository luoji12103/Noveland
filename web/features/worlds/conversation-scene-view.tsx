"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { readerMediaObjectDownloadPath } from "@/lib/worlds/media";
import type { ConversationPlaybackData } from "@/lib/worlds/server";
import {
  emptyTurnMedia,
  mediaSummary,
  resolveTurnMedia,
  speakerLabel,
  turnText,
} from "@/features/worlds/playback-media";

type ConversationSceneViewProps = {
  worldId: string;
  conversationId: string;
  data: ConversationPlaybackData;
};

export function ConversationSceneView({ worldId, conversationId, data }: ConversationSceneViewProps) {
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
  const imageUrl =
    activeMedia.imageObject === null
      ? null
      : readerMediaObjectDownloadPath(activeMedia.imageObject.download_url);
  const audioUrl =
    activeMedia.audioObject === null
      ? null
      : readerMediaObjectDownloadPath(activeMedia.audioObject.download_url);

  if (data.selectedWorld === null || data.conversation === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{data.loadError ?? "Conversation not found."}</p>
      </section>
    );
  }

  return (
    <section className="management-section scene-view">
      {data.loadError !== null ? <p className="management-notice">{data.loadError}</p> : null}

      <section className="scene-shell" aria-labelledby="scene-view-title">
        <div className="scene-toolbar">
          <div>
            <h2 id="scene-view-title">Scene view</h2>
            <p>
              {data.conversation.title} - {data.conversation.status}
            </p>
          </div>
          <div className="button-row">
            <Link className="secondary-button" href={`/worlds/${worldId}/reader`}>
              Reader
            </Link>
            <Link
              className="secondary-button"
              href={`/worlds/${worldId}/reader/conversations/${conversationId}/playback`}
            >
              Playback
            </Link>
          </div>
        </div>

        <div className="scene-stage">
          {imageUrl === null ? (
            <div className="scene-fallback" role="img" aria-label="Missing scene media">
              <div className="media-fallback-copy">
                <p>No reader-visible scene image for this turn.</p>
                <p>Scene dialogue is still available. No media diagnostics are exposed here.</p>
              </div>
            </div>
          ) : (
            <div
              aria-label="Reader-safe scene image"
              className="scene-image"
              role="img"
              style={{ backgroundImage: `url(${imageUrl})` }}
            />
          )}

          <div className="scene-dialogue" aria-live="polite">
            {activeTurn === null ? (
              <p>No turns are available for scene view.</p>
            ) : (
              <>
                <p className="scene-speaker">
                  Turn {activeTurn.turn_index + 1} - {speakerLabel(activeTurn)}
                </p>
                <p>{turnText(activeTurn)}</p>
              </>
            )}
          </div>
        </div>

        <div className="scene-controls">
          <div className="scene-meta" aria-label="Scene media state">
            <span>Render: {activePresentation?.render_state ?? "missing"}</span>
            <span>Emotion: {activePresentation?.emotion_key ?? "unset"}</span>
            <span>Media: {mediaSummary(activeMedia)}</span>
          </div>
          {audioUrl === null ? (
            <p className="management-notice" data-tone="warning">
              Audio is not available for this turn. Continue with the visible dialogue.
            </p>
          ) : (
            <audio aria-label="Scene audio" className="playback-audio" controls preload="none" src={audioUrl}>
              Audio playback is unavailable in this browser.
            </audio>
          )}
        </div>

        <nav className="scene-turns" aria-label="Scene turns">
          {data.turns.length === 0 ? (
            <p>No turns are available.</p>
          ) : (
            data.turns.map((turn, index) => {
              const presentation = data.presentationsByTurnId[turn.id] ?? null;
              return (
                <button
                  aria-pressed={index === activeIndex}
                  className="scene-turn-button"
                  key={turn.id}
                  onClick={() => setActiveIndex(index)}
                  type="button"
                >
                  <span>Turn {turn.turn_index + 1}</span>
                  <small>
                    {speakerLabel(turn)} - {presentation?.render_state ?? "no presentation"}
                  </small>
                </button>
              );
            })
          )}
        </nav>
      </section>
    </section>
  );
}
