"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createAgentCalendarEntry,
  createAgentMemoryItem,
  createAgentObservation,
  refreshAgentObservations,
  runAgent,
  updateAgent,
  updateAgentPersona,
} from "@/lib/worlds/client";
import type { AgentDetailData } from "@/lib/worlds/server";
import type { AgentPreset } from "@/lib/worlds/types";
import {
  formString,
  jsonNumberArray,
  jsonObject,
  messageForError,
  optionalFormString,
} from "@/features/workspace/form-utils";

type AgentBuilderProps = {
  worldId: string;
  agentId: string;
  data: AgentDetailData;
};

export function AgentBuilder({ worldId, agentId, data }: AgentBuilderProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const agent = data.selectedAgent;
  const sourcePreset = useMemo(
    () => data.agentPresets.find((preset) => preset.id === agent?.source_preset_id) ?? null,
    [agent?.source_preset_id, data.agentPresets],
  );
  const providerProfileMap = useMemo(
    () => new Map(data.providerProfiles.map((profile) => [profile.id, profile.profile_key])),
    [data.providerProfiles],
  );

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

  if (agent === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{notice ?? "Agent not found."}</p>
      </section>
    );
  }

  async function handleSaveAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateAgent(worldId, agentId, {
          display_name: formString(form, "display_name"),
          kind: formString(form, "kind") as "role_agent" | "narrative_agent",
          home_scene_id: optionalFormString(form, "home_scene_id"),
          provider_profile_id: optionalFormString(form, "provider_profile_id"),
          is_enabled: form.get("is_enabled") === "on",
          config: jsonObject(formString(form, "config")),
        }),
      "Agent saved.",
    );
  }

  async function handlePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateAgentPersona(worldId, agentId, {
          persona_text: formString(form, "persona_text"),
          behavior_policy: jsonObject(formString(form, "behavior_policy")),
          is_enabled: form.get("is_enabled") === "on",
        }),
      "Persona saved.",
    );
  }

  async function handleObservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createAgentObservation(worldId, agentId, {
          observation_type: formString(form, "observation_type") || "manual",
          content: formString(form, "content"),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Observation added.",
    );
  }

  async function handleCalendar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createAgentCalendarEntry(worldId, agentId, {
          title: formString(form, "title"),
          description: optionalFormString(form, "description"),
          starts_at: formString(form, "starts_at"),
        });
        formElement.reset();
      },
      "Calendar entry created.",
    );
  }

  async function handleMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createAgentMemoryItem(worldId, agentId, {
          content: formString(form, "content"),
          embedding: jsonNumberArray(formString(form, "embedding")),
          metadata: jsonObject(formString(form, "metadata")),
        });
        formElement.reset();
      },
      "Memory item added.",
    );
  }

  async function handleRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        runAgent(worldId, agentId, {
          prompt: optionalFormString(form, "prompt") ?? undefined,
          create_memory: form.get("create_memory") === "on",
          create_narrative_artifact: form.get("create_narrative_artifact") === "on",
        }),
      "Agent run completed.",
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}
      <section className="management-panel" aria-labelledby="agent-builder-title">
        <h2 className="section-title" id="agent-builder-title">
          Agent builder
        </h2>
        <div className="resource-list">
          <article className="resource-row">
            <div>
              <h3>Preset provenance</h3>
              <p>
                Source preset:{" "}
                {sourcePreset === null ? "none" : `${sourcePreset.name} (${sourcePreset.preset_key})`}
              </p>
              <p>
                Provider source:{" "}
                {agent.provider_profile_id === null
                  ? sourcePreset?.default_provider_profile_key ?? "first enabled provider"
                  : (providerProfileMap.get(agent.provider_profile_id) ?? agent.provider_profile_id)}
              </p>
              <p>{presetOverrideSummary(agent, sourcePreset, providerProfileMap)}</p>
            </div>
          </article>
        </div>
        {data.canManageSelectedWorld ? (
          <form className="inline-form" onSubmit={handleSaveAgent}>
            <input className="text-input" name="display_name" defaultValue={agent.display_name} />
            <select className="text-input" name="kind" defaultValue={agent.kind}>
              <option value="role_agent">role_agent</option>
              <option value="narrative_agent">narrative_agent</option>
            </select>
            <select className="text-input" name="home_scene_id" defaultValue={agent.home_scene_id ?? ""}>
              <option value="">No home scene</option>
              {data.scenes.map((scene) => (
                <option key={scene.id} value={scene.id}>
                  {scene.name}
                </option>
              ))}
            </select>
            <select
              className="text-input"
              name="provider_profile_id"
              defaultValue={agent.provider_profile_id ?? ""}
            >
              <option value="">Preset or first enabled provider</option>
              {data.providerProfiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                </option>
              ))}
            </select>
            <label className="checkbox-label">
              <input name="is_enabled" type="checkbox" defaultChecked={agent.is_enabled} />
              Enabled
            </label>
            <textarea
              className="text-input"
              name="config"
              rows={4}
              defaultValue={JSON.stringify(agent.config, null, 2)}
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Save agent
            </button>
          </form>
        ) : (
          <p>Read-only agent configuration access.</p>
        )}
      </section>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="persona-title">
          <h2 className="section-title" id="persona-title">
            Persona
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handlePersona}>
              <textarea
                className="text-input"
                name="persona_text"
                rows={6}
                defaultValue={data.agentPersona?.persona_text ?? ""}
                placeholder="Persona text"
              />
              <textarea
                className="text-input"
                name="behavior_policy"
                rows={4}
                defaultValue={JSON.stringify(data.agentPersona?.behavior_policy ?? {}, null, 2)}
              />
              <label className="checkbox-label">
                <input
                  name="is_enabled"
                  type="checkbox"
                  defaultChecked={data.agentPersona?.is_enabled ?? true}
                />
                Persona enabled
              </label>
              <button className="primary-button" type="submit">
                Save persona
              </button>
            </form>
          ) : (
            <>
              <p>{data.agentPersona?.persona_text ?? "No persona configured."}</p>
              <pre>{JSON.stringify(data.agentPersona?.behavior_policy ?? {}, null, 2)}</pre>
            </>
          )}
        </section>

        <section className="management-panel" aria-labelledby="observations-title">
          <h2 className="section-title" id="observations-title">
            Observations
          </h2>
          {data.canManageSelectedWorld ? (
            <>
              <form className="inline-form" onSubmit={handleObservation}>
                <input className="text-input" name="observation_type" placeholder="manual" />
                <textarea className="text-input" name="content" placeholder="Observation" rows={4} />
                <textarea className="text-input" name="metadata" placeholder="{}" rows={3} />
                <button className="primary-button" type="submit">
                  Add observation
                </button>
              </form>
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  runAction(
                    () => refreshAgentObservations(worldId, agentId),
                    "Observations refreshed.",
                  )
                }
              >
                Refresh observations
              </button>
            </>
          ) : null}
          <ResourceList
            rows={data.agentObservations.map((observation) => ({
              id: observation.id,
              title: observation.observation_type,
              detail: observation.content,
            }))}
          />
        </section>
      </div>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="calendar-title">
          <h2 className="section-title" id="calendar-title">
            Calendar
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handleCalendar}>
              <input className="text-input" name="title" placeholder="Calendar title" />
              <input className="text-input" name="starts_at" placeholder="2030-01-01T08:00:00Z" />
              <input className="text-input" name="description" placeholder="Description" />
              <button className="primary-button" type="submit">
                Create calendar entry
              </button>
            </form>
          ) : null}
          <ResourceList
            rows={data.calendarEntries.map((entry) => ({
              id: entry.id,
              title: entry.title,
              detail: `${entry.starts_at} - ${entry.status}`,
            }))}
          />
        </section>

        <section className="management-panel" aria-labelledby="memory-title">
          <h2 className="section-title" id="memory-title">
            Memory
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handleMemory}>
              <textarea className="text-input" name="content" placeholder="Memory content" rows={4} />
              <input className="text-input" name="embedding" placeholder="[1,0,0]" />
              <textarea className="text-input" name="metadata" placeholder="{}" rows={3} />
              <button className="primary-button" type="submit">
                Add memory item
              </button>
            </form>
          ) : null}
          <ResourceList
            rows={data.memoryItems.map((item) => ({
              id: item.id,
              title: item.content,
              detail: item.is_active ? "Active memory" : "Inactive memory",
            }))}
          />
        </section>
      </div>

      <section className="management-panel" aria-labelledby="runs-title">
        <h2 className="section-title" id="runs-title">
          Runs
        </h2>
        {data.canManageSelectedWorld ? (
          <form className="inline-form" onSubmit={handleRun}>
            <textarea className="text-input" name="prompt" placeholder="Manual run prompt" rows={4} />
            <label className="checkbox-label">
              <input name="create_memory" type="checkbox" defaultChecked />
              Write memory
            </label>
            <label className="checkbox-label">
              <input name="create_narrative_artifact" type="checkbox" defaultChecked />
              Create narrative artifact
            </label>
            <button className="primary-button" type="submit">
              Run agent
            </button>
          </form>
        ) : null}
        <ResourceList
          rows={data.agentRuns.map((run) => ({
            id: run.run_id,
            title: run.status,
            detail: run.response_text ?? run.prompt_text,
          }))}
        />
      </section>
    </section>
  );
}

function presetOverrideSummary(
  agent: NonNullable<AgentDetailData["selectedAgent"]>,
  sourcePreset: AgentPreset | null,
  providerProfileMap: Map<string, string>,
): string {
  if (sourcePreset === null) {
    return "No preset materialized for this agent.";
  }
  const differences: string[] = [];
  if (agent.kind !== sourcePreset.default_kind) {
    differences.push(`kind overrides ${sourcePreset.default_kind}`);
  }
  const providerKey =
    agent.provider_profile_id === null
      ? null
      : (providerProfileMap.get(agent.provider_profile_id) ?? agent.provider_profile_id);
  if (
    providerKey !== null
    && providerKey !== sourcePreset.default_provider_profile_key
  ) {
    differences.push(`provider overrides ${sourcePreset.default_provider_profile_key ?? "none"}`);
  }
  if (differences.length === 0) {
    return "Agent still matches preset defaults at the structured field level.";
  }
  return differences.join("; ");
}

function ResourceList({ rows }: { rows: { id: string; title: string; detail: string }[] }) {
  if (rows.length === 0) {
    return <p>No records yet.</p>;
  }
  return (
    <div className="resource-list">
      {rows.map((row) => (
        <article className="resource-row" key={row.id}>
          <div>
            <h3>{row.title}</h3>
            <p>{row.detail}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
