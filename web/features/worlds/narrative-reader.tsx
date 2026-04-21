import Link from "next/link";

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
  if (data.selectedWorld === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{data.loadError ?? "World not found."}</p>
      </section>
    );
  }

  const conversationsById = new Map(data.conversations.map((conversation) => [conversation.id, conversation]));

  return (
    <section className="management-section">
      {data.loadError !== null ? <p className="management-notice">{data.loadError}</p> : null}

      <section className="management-panel" aria-labelledby="reader-filters-title">
        <h2 className="section-title" id="reader-filters-title">
          Reader filters
        </h2>
        <form className="inline-form" method="get">
          <select className="text-input" name="artifact_kind" defaultValue={data.selectedArtifactKind}>
            <option value="">All readable artifacts</option>
            <option value="conversation_summary">conversation_summary</option>
            <option value="chapter_draft">chapter_draft</option>
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
          <Link className="secondary-button" href={`/worlds/${worldId}/reader`}>
            Clear
          </Link>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="reader-list-title">
        <h2 className="section-title" id="reader-list-title">
          Narrative reader
        </h2>
        <div className="resource-list">
          {data.narrativeArtifacts.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No readable artifacts</h3>
                <p>Try a different filter or generate narrative from a conversation.</p>
              </div>
            </article>
          ) : (
            data.narrativeArtifacts.map((artifact) => {
              const sourceConversation =
                artifact.source_conversation_id === null
                  ? null
                  : conversationsById.get(artifact.source_conversation_id) ?? null;
              return (
                <article className="resource-row" key={artifact.id}>
                  <div>
                    <h3>
                      <Link href={`/worlds/${worldId}/reader/${artifact.id}`}>{artifact.title}</Link>
                    </h3>
                    <p>
                      {artifact.artifact_kind} - {formatDateTime(artifact.created_at)}
                    </p>
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
          <Link className="secondary-button" href={`/worlds/${worldId}/reader`}>
            Back to reader
          </Link>
          {sourceConversation !== null ? (
            <Link
              className="secondary-button"
              href={`/worlds/${worldId}/conversations/${sourceConversation.id}`}
            >
              Open source conversation
            </Link>
          ) : null}
        </div>

        <h2 className="section-title" id="artifact-title">
          {data.artifact.title}
        </h2>
        <p>
          {data.artifact.artifact_kind} - {formatDateTime(data.artifact.created_at)}
        </p>
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
