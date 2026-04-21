"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createAgent, deactivateAgent } from "@/lib/worlds/client";
import type { AgentWorkspaceData } from "@/lib/worlds/server";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type AgentListProps = {
  worldId: string;
  data: AgentWorkspaceData;
};

export function AgentList({ worldId, data }: AgentListProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);

  async function runAction(action: () => Promise<unknown>, success: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      router.refresh();
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        const agent = await createAgent(worldId, {
          agent_key: formString(form, "agent_key"),
          display_name: formString(form, "display_name"),
          kind: formString(form, "kind") as "role_agent" | "narrative_agent",
          home_scene_id: optionalFormString(form, "home_scene_id"),
          provider_profile_id: optionalFormString(form, "provider_profile_id"),
        });
        formElement.reset();
        router.push(`/worlds/${worldId}/agents/${agent.id}`);
      },
      "Agent created.",
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}
      <section className="management-panel" aria-labelledby="create-agent-title">
        <h2 className="section-title" id="create-agent-title">
          Create agent
        </h2>
        <form className="management-form" onSubmit={handleCreateAgent}>
          <input className="text-input" name="agent_key" placeholder="agent-key" />
          <input className="text-input" name="display_name" placeholder="Display name" />
          <select className="text-input" name="kind" defaultValue="role_agent">
            <option value="role_agent">role_agent</option>
            <option value="narrative_agent">narrative_agent</option>
          </select>
          <select className="text-input" name="home_scene_id" defaultValue="">
            <option value="">No home scene</option>
            {data.scenes.map((scene) => (
              <option key={scene.id} value={scene.id}>
                {scene.name}
              </option>
            ))}
          </select>
          <select className="text-input" name="provider_profile_id" defaultValue="">
            <option value="">First enabled provider</option>
            {data.providerProfiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create agent
          </button>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="agents-title">
        <h2 className="section-title" id="agents-title">
          Agents
        </h2>
        <div className="resource-list">
          {data.agents.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No agents yet</h3>
                <p>Create role or narrative agents for this world.</p>
              </div>
            </article>
          ) : (
            data.agents.map((agent) => (
              <article className="resource-row" key={agent.id}>
                <div>
                  <h3>{agent.display_name}</h3>
                  <p>
                    {agent.agent_key} - {agent.kind} -{" "}
                    {agent.is_enabled ? "Enabled" : "Disabled"}
                  </p>
                  <p>
                    Default provider: {agent.provider_profile_id ?? "first enabled provider"}
                  </p>
                </div>
                <div className="button-row">
                  <Link className="secondary-button" href={`/worlds/${worldId}/agents/${agent.id}`}>
                    Open builder
                  </Link>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => deactivateAgent(worldId, agent.id), "Agent disabled.")
                    }
                  >
                    Disable agent
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </section>
  );
}
