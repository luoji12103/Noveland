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

type ConversationPlaybackProps = {
  worldId: string;
  conversationId: string;
  data: ConversationPlaybackData;
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
            <Link className="secondary-button" href={`/worlds/${encodeURIComponent(worldId)}/reader`}>
              Back to reader
            </Link>
            <Link
              className="secondary-button"
              href={`/worlds/${encodeURIComponent(worldId)}/reader/conversations/${encodeURIComponent(conversationId)}/scene`}
            >
              Scene view
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
              <div className="playback-scene-empty">
                <div className="media-fallback-copy">
                  <p>No reader-visible image for this turn.</p>
                  <p>Dialogue remains available while media is missing or still rendering.</p>
                </div>
              </div>
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
            <p className="management-notice" data-tone="warning">
              No reader-visible audio for this turn. Continue with text playback.
            </p>
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
