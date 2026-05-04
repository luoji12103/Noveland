"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { createAgent, deactivateAgent } from "@/lib/worlds/client";
import type { AgentWorkspaceData } from "@/lib/worlds/server";
import type { AgentPreset } from "@/lib/worlds/types";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type AgentListProps = {
  worldId: string;
  data: AgentWorkspaceData;
};

export function AgentList({ worldId, data }: AgentListProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState("");
  const [selectedKind, setSelectedKind] = useState<"role_agent" | "narrative_agent">("role_agent");
  const presetMap = useMemo(
    () => new Map(data.agentPresets.map((preset) => [preset.id, preset])),
    [data.agentPresets],
  );
  const selectedPreset = selectedPresetId === "" ? null : (presetMap.get(selectedPresetId) ?? null);

  async function runAction(action: () => Promise<unknown>, success: string, refresh = true) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      if (refresh) {
        router.refresh();
      }
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
          preset_id: optionalFormString(form, "preset_id"),
          provider_profile_id: optionalFormString(form, "provider_profile_id"),
        });
        formElement.reset();
        setSelectedPresetId("");
        setSelectedKind("role_agent");
        window.location.assign(`/worlds/${worldId}/agents/${agent.id}`);
      },
      "Agent created.",
      false,
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}
      <section className="management-panel" aria-labelledby="create-agent-title">
        <h2 className="section-title" id="create-agent-title">
          Create agent
        </h2>
        {data.canManageSelectedWorld ? (
          <>
            <form className="management-form" onSubmit={handleCreateAgent}>
              <input className="text-input" name="agent_key" placeholder="agent-key" />
              <input className="text-input" name="display_name" placeholder="Display name" />
              <select
                className="text-input"
                name="preset_id"
                value={selectedPresetId}
                onChange={(event) => {
                  const nextPresetId = event.target.value;
                  setSelectedPresetId(nextPresetId);
                  const nextPreset =
                    nextPresetId === "" ? null : (presetMap.get(nextPresetId) ?? null);
                  if (nextPreset !== null) {
                    setSelectedKind(nextPreset.default_kind);
                  } else {
                    setSelectedKind("role_agent");
                  }
                }}
              >
                <option value="">No preset</option>
                {data.agentPresets.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.name}
                  </option>
                ))}
              </select>
              <select
                className="text-input"
                name="kind"
                value={selectedKind}
                onChange={(event) =>
                  setSelectedKind(event.target.value as "role_agent" | "narrative_agent")
                }
              >
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
                <option value="">Preset or first enabled provider</option>
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
            {selectedPreset !== null ? <PresetPreview preset={selectedPreset} /> : null}
          </>
        ) : (
          <p>Read-only agent catalog access.</p>
        )}
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
                  <p>
                    Source preset: {formatPresetLabel(presetMap.get(agent.source_preset_id ?? "") ?? null)}
                  </p>
                  <p>Source preset version: {agent.source_preset_version ?? "none"}</p>
                </div>
                <div className="button-row">
                  <Link className="secondary-button" href={`/worlds/${worldId}/agents/${agent.id}`}>
                    Open builder
                  </Link>
                  {data.canManageSelectedWorld ? (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        runAction(() => deactivateAgent(worldId, agent.id), "Agent disabled.")
                      }
                    >
                      Disable agent
                    </button>
                  ) : null}
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </section>
  );
}

function PresetPreview({ preset }: { preset: AgentPreset }) {
  return (
    <div className="resource-list">
      <article className="resource-row">
        <div>
          <h3>Preset preview</h3>
          <p>
            {preset.preset_key} - {preset.default_kind} - version {preset.version}
          </p>
          <p>Provider key: {preset.default_provider_profile_key ?? "none"}</p>
          <p>Calendar blueprint entries: {preset.calendar_blueprint.length}</p>
          <p>{preset.description ?? "No description."}</p>
        </div>
      </article>
    </div>
  );
}

function formatPresetLabel(preset: AgentPreset | null): string {
  if (preset === null) {
    return "none";
  }
  return `${preset.name} (${preset.preset_key} v${preset.version})`;
}
