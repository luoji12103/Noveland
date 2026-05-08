"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createNarrativeArtifact,
  publishNarrativeArtifact,
  unpublishNarrativeArtifact,
} from "@/lib/worlds/client";
import { mergeById, subscribeToEventStream } from "@/lib/realtime";
import type { WorldStreamEnvelope } from "@/lib/realtime";
import type { NarrativeWorkspaceData } from "@/lib/worlds/server";
import type { NarrativeArtifact } from "@/lib/worlds/types";
import {
  formString,
  messageForError,
  optionalFormString,
} from "@/features/workspace/form-utils";

type NarrativeWorkspaceProps = {
  worldId: string;
  data: NarrativeWorkspaceData;
};

export function NarrativeWorkspace({ worldId, data }: NarrativeWorkspaceProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [busyArtifactId, setBusyArtifactId] = useState<string | null>(null);
  const [streamedArtifacts, setStreamedArtifacts] = useState<NarrativeArtifact[]>([]);

  useEffect(() => {
    return subscribeToEventStream<WorldStreamEnvelope["payload"]>(
      `/api/worlds/${worldId}/stream`,
      (envelope) => {
        if (envelope.payload.narrative_artifacts.length > 0) {
          setStreamedArtifacts((current) =>
            mergeArtifacts(current, envelope.payload.narrative_artifacts),
          );
        }
      },
    );
  }, [worldId]);

  async function handleCreateArtifact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setIsBusy(true);
    setNotice(null);
    try {
      await createNarrativeArtifact(worldId, {
        title: formString(form, "title"),
        content: formString(form, "content"),
        artifact_kind: formString(form, "artifact_kind") as "agent_note" | "world_summary",
        agent_id: optionalFormString(form, "agent_id"),
      });
      formElement.reset();
      setNotice("Narrative artifact created.");
      router.refresh();
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePublishArtifact(artifactId: string) {
    setBusyArtifactId(artifactId);
    setNotice(null);
    try {
      await publishNarrativeArtifact(worldId, artifactId, {
        reader_visible: true,
        metadata: { channel: "reader" },
        override_style_warning: true,
      });
      setNotice("Narrative artifact published.");
      router.refresh();
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setBusyArtifactId(null);
    }
  }

  async function handleUnpublishArtifact(artifactId: string) {
    setBusyArtifactId(artifactId);
    setNotice(null);
    try {
      await unpublishNarrativeArtifact(worldId, artifactId, {
        metadata: { reason: "operator_unpublished" },
      });
      setNotice("Narrative artifact unpublished.");
      router.refresh();
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setBusyArtifactId(null);
    }
  }

  const narrativeArtifacts = mergeArtifacts(data.narrativeArtifacts, streamedArtifacts);
  const publishedArtifacts = narrativeArtifacts.filter(
    (artifact) =>
      artifact.publication?.status === "published" && artifact.publication.reader_visible,
  );
  const draftArtifacts = narrativeArtifacts.filter(
    (artifact) =>
      artifact.publication === null ||
      artifact.publication.status !== "published" ||
      !artifact.publication.reader_visible,
  );

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      {data.canManageSelectedWorld ? (
        <section className="management-panel" aria-labelledby="create-artifact-title">
          <h2 className="section-title" id="create-artifact-title">
            Create narrative artifact
          </h2>
          <form className="management-form" onSubmit={handleCreateArtifact}>
            <input className="text-input" name="title" placeholder="Artifact title" />
            <select className="text-input" name="artifact_kind" defaultValue="world_summary">
              <option value="world_summary">world_summary</option>
              <option value="agent_note">agent_note</option>
            </select>
            <select className="text-input" name="agent_id" defaultValue="">
              <option value="">World level</option>
              {data.agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.display_name}
                </option>
              ))}
            </select>
            <textarea
              className="text-input"
              name="content"
              placeholder="Artifact content"
              rows={5}
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create artifact
            </button>
          </form>
        </section>
      ) : null}

      <section className="management-panel" aria-labelledby="artifacts-title">
        <h2 className="section-title" id="artifacts-title">
          Draft artifacts
        </h2>
        <ArtifactList
          artifacts={draftArtifacts}
          agents={data.agents}
          emptyTitle="No drafts"
          emptyBody="Run agents or create a world summary to begin."
          busyArtifactId={busyArtifactId}
          canManage={data.canManageSelectedWorld}
          onPublish={handlePublishArtifact}
          onUnpublish={handleUnpublishArtifact}
        />
      </section>

      <section className="management-panel" aria-labelledby="published-artifacts-title">
        <h2 className="section-title" id="published-artifacts-title">
          Published artifacts
        </h2>
        <ArtifactList
          artifacts={publishedArtifacts}
          agents={data.agents}
          emptyTitle="No published artifacts"
          emptyBody="Publish a draft to make it visible in the reader."
          busyArtifactId={busyArtifactId}
          canManage={data.canManageSelectedWorld}
          onPublish={handlePublishArtifact}
          onUnpublish={handleUnpublishArtifact}
        />
      </section>
    </section>
  );
}

function ArtifactList({
  artifacts,
  agents,
  emptyTitle,
  emptyBody,
  busyArtifactId,
  canManage,
  onPublish,
  onUnpublish,
}: {
  artifacts: NarrativeArtifact[];
  agents: NarrativeWorkspaceData["agents"];
  emptyTitle: string;
  emptyBody: string;
  busyArtifactId: string | null;
  canManage: boolean;
  onPublish: (artifactId: string) => void;
  onUnpublish: (artifactId: string) => void;
}) {
  return (
    <div className="resource-list">
      {artifacts.length === 0 ? (
        <article className="resource-row">
          <div>
            <h3>{emptyTitle}</h3>
            <p>{emptyBody}</p>
          </div>
        </article>
      ) : (
        artifacts.map((artifact) => {
          const agent = agents.find((item) => item.id === artifact.agent_id);
          const isPublished =
            artifact.publication?.status === "published" &&
            artifact.publication.reader_visible;
          return (
            <article className="resource-row" key={artifact.id}>
              <div>
                <h3>{artifact.title}</h3>
                <p>
                  {artifact.artifact_kind} - {agent?.display_name ?? "world"} -{" "}
                  {isPublished ? "published" : "draft"}
                </p>
                <p>{artifact.content}</p>
                {artifact.publication !== null ? (
                  <p>
                    Publication: {artifact.publication.status}
                    {artifact.publication.published_at === null
                      ? ""
                      : ` at ${formatDateTime(artifact.publication.published_at)}`}
                  </p>
                ) : null}
                {artifact.publication?.publication_gate ? (
                  <p>{publicationGateLabel(artifact.publication.publication_gate)}</p>
                ) : null}
              </div>
              {canManage ? (
                <div className="button-row">
                  {isPublished ? (
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={busyArtifactId === artifact.id}
                      onClick={() => onUnpublish(artifact.id)}
                    >
                      Unpublish
                    </button>
                  ) : (
                    <button
                      className="primary-button"
                      type="button"
                      disabled={busyArtifactId === artifact.id}
                      onClick={() => onPublish(artifact.id)}
                    >
                      Publish
                    </button>
                  )}
                </div>
              ) : null}
            </article>
          );
        })
      )}
    </div>
  );
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function publicationGateLabel(gate: Record<string, unknown>): string {
  const status = typeof gate.status === "string" ? gate.status : "unknown";
  const issueCount = typeof gate.issue_count === "number" ? gate.issue_count : 0;
  return `Publication gate: ${status} (${issueCount} issue${issueCount === 1 ? "" : "s"})`;
}

function mergeArtifacts(current: NarrativeArtifact[], incoming: NarrativeArtifact[]): NarrativeArtifact[] {
  return mergeById(current, incoming).sort((left, right) =>
    right.created_at.localeCompare(left.created_at),
  );
}
