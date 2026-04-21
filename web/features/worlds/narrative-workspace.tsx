"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createNarrativeArtifact } from "@/lib/worlds/client";
import type { NarrativeWorkspaceData } from "@/lib/worlds/server";
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
          Narrative artifacts
        </h2>
        <div className="resource-list">
          {data.narrativeArtifacts.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No artifacts yet</h3>
                <p>Run agents or create a world summary to begin.</p>
              </div>
            </article>
          ) : (
            data.narrativeArtifacts.map((artifact) => {
              const agent = data.agents.find((item) => item.id === artifact.agent_id);
              return (
                <article className="resource-row" key={artifact.id}>
                  <div>
                    <h3>{artifact.title}</h3>
                    <p>
                      {artifact.artifact_kind} - {agent?.display_name ?? "world"}
                    </p>
                    <p>{artifact.content}</p>
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
