"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { mergeById, subscribeToEventStream } from "@/lib/realtime";
import type { WorldStreamEnvelope } from "@/lib/realtime";
import type {
  NarrativeReaderDetailData,
  NarrativeReaderListData,
} from "@/lib/worlds/server";

type NarrativeReaderListProps = {
  worldId: string;
  data: NarrativeReaderListData;
};

type NarrativeReaderDetailProps = {
  worldId: string;
  data: NarrativeReaderDetailData;
};

export function NarrativeReaderList({ worldId, data }: NarrativeReaderListProps) {
  const [streamedArtifacts, setStreamedArtifacts] = useState<
    NarrativeReaderListData["narrativeArtifacts"]
  >([]);

  useEffect(() => {
    return subscribeToEventStream<WorldStreamEnvelope["payload"]>(
      `/api/worlds/${worldId}/stream`,
      (envelope) => {
        const publishedArtifacts = envelope.payload.narrative_artifacts.filter(
          (artifact) =>
            artifact.publication?.status === "published" &&
            artifact.publication.reader_visible &&
            matchesReaderFilters(artifact, data),
        );
        if (publishedArtifacts.length > 0) {
          setStreamedArtifacts((current) =>
            mergeTimelineArtifacts(current, publishedArtifacts, data.selectedOrderBy),
          );
        }
      },
    );
  }, [data, worldId]);

  if (data.selectedWorld === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{data.loadError ?? "World not found."}</p>
      </section>
    );
  }

  const conversationsById = new Map(data.conversations.map((conversation) => [conversation.id, conversation]));
  const filteredStreamedArtifacts = streamedArtifacts.filter((artifact) =>
    matchesReaderFilters(artifact, data),
  );
  const narrativeArtifacts = mergeTimelineArtifacts(
    data.narrativeArtifacts,
    filteredStreamedArtifacts,
    data.selectedOrderBy,
  );

  return (
    <section className="management-section">
      {data.loadError !== null ? <p className="management-notice">{data.loadError}</p> : null}

      <section className="management-panel" aria-labelledby="reader-filters-title">
        <h2 className="section-title" id="reader-filters-title">
          Reader filters
        </h2>
        <form className="inline-form" method="get">
          <input
            className="text-input"
            name="q"
            placeholder="Search title or content"
            defaultValue={data.selectedSearch}
          />
          <select className="text-input" name="artifact_kind" defaultValue={data.selectedArtifactKind}>
            <option value="">All readable artifacts</option>
            <option value="conversation_summary">conversation_summary</option>
            <option value="chapter_draft">chapter_draft</option>
          </select>
          <select className="text-input" name="source_kind" defaultValue={data.selectedSourceKind}>
            <option value="">All sources</option>
            <option value="world">World level</option>
            <option value="agent">Agent note</option>
            <option value="agent_run">Agent run</option>
            <option value="conversation">Conversation</option>
          </select>
          <select className="text-input" name="order_by" defaultValue={data.selectedOrderBy}>
            <option value="published_at">Publication timeline</option>
            <option value="created_at">Draft creation</option>
          </select>
          <select
            className="text-input"
            name="source_conversation_id"
            defaultValue={data.selectedConversationId}
          >
            <option value="">All conversations</option>
            {data.conversations.map((conversation) => (
              <option key={conversation.id} value={conversation.id}>
                {conversation.title}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit">
            Apply filters
          </button>
          <Link className="secondary-button" href={`/worlds/${encodeURIComponent(worldId)}/reader`}>
            Clear
          </Link>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="reader-list-title">
        <h2 className="section-title" id="reader-list-title">
          Narrative reader
        </h2>
        <div className="resource-list">
          {narrativeArtifacts.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No readable artifacts</h3>
                <p>Try a different search or filter, or generate narrative from a conversation.</p>
              </div>
            </article>
          ) : (
            narrativeArtifacts.map((artifact) => {
              const sourceConversation =
                artifact.source_conversation_id === null
                  ? null
                  : conversationsById.get(artifact.source_conversation_id) ?? null;
              return (
                <article className="resource-row" key={artifact.id}>
                  <div>
                    <h3>
                      <Link href={`/worlds/${encodeURIComponent(worldId)}/reader/${encodeURIComponent(artifact.id)}`}>{artifact.title}</Link>
                    </h3>
                    <p>
                      {artifact.artifact_kind} - {formatDateTime(artifact.created_at)}
                    </p>
                    {artifact.publication !== null ? (
                      <p>
                        Published{" "}
                        {artifact.publication.published_at === null
                          ? "for readers"
                          : formatDateTime(artifact.publication.published_at)}
                      </p>
                    ) : null}
                    <p>Timeline: {timelineLabel(artifact)}</p>
                    <p>
                      {sourceConversation === null
                        ? "World-level artifact"
                        : `Conversation: ${sourceConversation.title}`}
                    </p>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>
    </section>
  );
}

function timelineLabel(artifact: NarrativeReaderListData["narrativeArtifacts"][number]): string {
  if (artifact.publication?.published_at) {
    return `published ${formatDateTime(artifact.publication.published_at)}`;
  }
  return `drafted ${formatDateTime(artifact.created_at)}`;
}

function matchesReaderFilters(
  artifact: NarrativeReaderListData["narrativeArtifacts"][number],
  data: NarrativeReaderListData,
): boolean {
  if (data.selectedArtifactKind !== "" && artifact.artifact_kind !== data.selectedArtifactKind) {
    return false;
  }
  if (
    data.selectedConversationId !== "" &&
    artifact.source_conversation_id !== data.selectedConversationId
  ) {
    return false;
  }
  if (data.selectedSourceKind !== "" && sourceKindForArtifact(artifact) !== data.selectedSourceKind) {
    return false;
  }
  if (data.selectedSearch !== "") {
    const needle = data.selectedSearch.toLowerCase();
    return (
      artifact.title.toLowerCase().includes(needle) ||
      artifact.content.toLowerCase().includes(needle)
    );
  }
  return true;
}

function sourceKindForArtifact(
  artifact: NarrativeReaderListData["narrativeArtifacts"][number],
): string {
  if (artifact.source_conversation_id !== null) {
    return "conversation";
  }
  if (artifact.source_run_id !== null) {
    return "agent_run";
  }
  if (artifact.agent_id !== null) {
    return "agent";
  }
  return "world";
}

function mergeTimelineArtifacts(
  current: NarrativeReaderListData["narrativeArtifacts"],
  incoming: NarrativeReaderListData["narrativeArtifacts"],
  orderBy: string,
): NarrativeReaderListData["narrativeArtifacts"] {
  return mergeById(current, incoming).sort((left, right) => {
    const leftDate = orderBy === "created_at" ? left.created_at : timelineDate(left);
    const rightDate = orderBy === "created_at" ? right.created_at : timelineDate(right);
    return rightDate.localeCompare(leftDate);
  });
}

function timelineDate(artifact: NarrativeReaderListData["narrativeArtifacts"][number]): string {
  return artifact.publication?.published_at ?? artifact.created_at;
}

export function NarrativeReaderDetail({ worldId, data }: NarrativeReaderDetailProps) {
  if (data.selectedWorld === null || data.artifact === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{data.loadError ?? "Narrative artifact not found."}</p>
      </section>
    );
  }

  const sourceConversation =
    data.artifact.source_conversation_id === null
      ? null
      : data.conversations.find(
          (conversation) => conversation.id === data.artifact?.source_conversation_id,
        ) ?? null;

  return (
    <section className="management-section">
      {data.loadError !== null ? <p className="management-notice">{data.loadError}</p> : null}

      <section className="management-panel" aria-labelledby="artifact-title">
        <div className="button-row">
          <Link className="secondary-button" href={`/worlds/${encodeURIComponent(worldId)}/reader`}>
            Back to reader
          </Link>
          {sourceConversation !== null ? (
            <Link
              className="secondary-button"
              href={`/worlds/${encodeURIComponent(worldId)}/conversations/${encodeURIComponent(sourceConversation.id)}`}
            >
              Open source conversation
            </Link>
          ) : null}
          {sourceConversation !== null ? (
            <Link
              className="secondary-button"
              href={`/worlds/${encodeURIComponent(worldId)}/reader/conversations/${encodeURIComponent(sourceConversation.id)}/playback`}
            >
              Open playback
            </Link>
          ) : null}
        </div>

        <h2 className="section-title" id="artifact-title">
          {data.artifact.title}
        </h2>
        <p>
          {data.artifact.artifact_kind} - {formatDateTime(data.artifact.created_at)}
        </p>
        {data.artifact.publication !== null ? (
          <p>
            Published{" "}
            {data.artifact.publication.published_at === null
              ? "for readers"
              : formatDateTime(data.artifact.publication.published_at)}
          </p>
        ) : null}
        <p>
          {sourceConversation === null
            ? "World-level artifact"
            : `Conversation: ${sourceConversation.title}`}
        </p>
        <div className="resource-list">
          <article className="resource-row">
            <div>
              <h3>Content</h3>
              <p style={{ whiteSpace: "pre-wrap" }}>{data.artifact.content}</p>
            </div>
          </article>
          <article className="resource-row">
            <div>
              <h3>Metadata</h3>
              <p style={{ whiteSpace: "pre-wrap" }}>
                {JSON.stringify(data.artifact.metadata, null, 2)}
              </p>
            </div>
          </article>
        </div>
      </section>
    </section>
  );
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
