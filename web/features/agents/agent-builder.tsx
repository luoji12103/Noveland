"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createAgentRelationship,
  createAgentCalendarEntry,
  createAgentObservation,
  forgetAgentMemory,
  getAgentRunDetail,
  listAgentMemory,
  refreshAgentMemoryProfileSnapshot,
  refreshAgentObservations,
  runAgent,
  searchAgentMemory,
  updateAgent,
  updateAgentRelationship,
  updateAgentPersona,
  validateAgentPersona,
} from "@/lib/worlds/client";
import type { AgentDetailData } from "@/lib/worlds/server";
import type {
  AgentRelationship,
  AgentPreset,
  AgentRunDetail,
  CharacterCategory,
  CharacterImportance,
  ContinuityStatus,
  NarrativeRole,
  RelationshipType,
} from "@/lib/worlds/types";
import {
  formString,
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
  const [memoryItems, setMemoryItems] = useState(data.memoryItems);
  const [memoryProfileSnapshot, setMemoryProfileSnapshot] = useState(data.memoryProfileSnapshot);
  const [relationships, setRelationships] = useState(data.relationships);
  const [selectedRunDetail, setSelectedRunDetail] = useState<AgentRunDetail | null>(null);
  const agent = data.selectedAgent;
  const sourcePreset = useMemo(
    () => data.agentPresets.find((preset) => preset.id === agent?.source_preset_id) ?? null,
    [agent?.source_preset_id, data.agentPresets],
  );
  const providerProfileMap = useMemo(
    () => new Map(data.providerProfiles.map((profile) => [profile.id, profile.profile_key])),
    [data.providerProfiles],
  );

  useEffect(() => {
    setMemoryItems(data.memoryItems);
  }, [data.memoryItems]);

  useEffect(() => {
    setMemoryProfileSnapshot(data.memoryProfileSnapshot);
  }, [data.memoryProfileSnapshot]);

  useEffect(() => {
    setRelationships(data.relationships);
  }, [data.relationships]);

  useEffect(() => {
    setSelectedRunDetail(null);
  }, [agentId]);

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

  async function inspectRun(runId: string) {
    await runAction(async () => {
      setSelectedRunDetail(await getAgentRunDetail(worldId, agentId, runId));
    }, "Agent run detail loaded.");
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
          narrative_role: optionalFormString(form, "narrative_role") as NarrativeRole | null,
          importance: optionalFormString(form, "importance") as CharacterImportance | null,
          canon_status: optionalFormString(form, "canon_status") as ContinuityStatus | null,
          character_category: optionalFormString(form, "character_category") as CharacterCategory | null,
          character_profile: jsonObject(formString(form, "character_profile")),
          is_enabled: form.get("is_enabled") === "on",
          config: jsonObject(formString(form, "config")),
        }),
      "Agent saved.",
    );
  }

  async function handleCreateRelationship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        const edge = await createAgentRelationship(worldId, agentId, {
          source_agent_id: agentId,
          target_agent_id: formString(form, "target_agent_id"),
          relationship_type: formString(form, "relationship_type") as RelationshipType,
          affection: numberValue(form, "affection", 0),
          trust: numberValue(form, "trust", 0),
          hostility: numberValue(form, "hostility", 0),
          intimacy: numberValue(form, "intimacy", 0),
          obligation: numberValue(form, "obligation", 0),
          rivalry: numberValue(form, "rivalry", 0),
          debt: numberValue(form, "debt", 0),
          metadata: jsonObject(formString(form, "metadata")),
        });
        setRelationships((current) => [...current, edge]);
        formElement.reset();
      },
      "Relationship created.",
    );
  }

  async function handleUpdateRelationship(
    relationshipId: string,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        const edge = await updateAgentRelationship(worldId, agentId, relationshipId, {
          affection: numberValue(form, "affection", 0),
          trust: numberValue(form, "trust", 0),
          hostility: numberValue(form, "hostility", 0),
          intimacy: numberValue(form, "intimacy", 0),
          obligation: numberValue(form, "obligation", 0),
          rivalry: numberValue(form, "rivalry", 0),
          debt: numberValue(form, "debt", 0),
          metadata: jsonObject(formString(form, "metadata")),
        });
        setRelationships((current) =>
          current.map((item) => (item.id === relationshipId ? edge : item)),
        );
      },
      "Relationship updated.",
    );
  }

  async function handlePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateAgentPersona(worldId, agentId, personaInputFromForm(form)),
      "Persona saved.",
    );
  }

  async function handleValidatePersona(formElement: HTMLFormElement) {
    const form = new FormData(formElement);
    await runAction(async () => {
      const validation = await validateAgentPersona(worldId, agentId, personaInputFromForm(form));
      if (!validation.valid) {
        throw new Error(validation.issues.map((issue) => issue.message).join(" "));
      }
    }, "Persona policy is valid.");
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
          confidence_score: optionalNumber(form, "confidence_score"),
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

  async function handleMemorySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setIsBusy(true);
    setNotice(null);
    try {
      const items = await searchAgentMemory(worldId, agentId, {
        query_text: formString(form, "query_text"),
        limit: Number(optionalFormString(form, "limit") ?? "10"),
      });
      setMemoryItems(items);
      setNotice(`Memory search returned ${items.length} item(s).`);
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRefreshMemory() {
    setIsBusy(true);
    setNotice(null);
    try {
      const items = await listAgentMemory(worldId, agentId);
      setMemoryItems(items);
      setNotice("Memory list refreshed.");
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRefreshMemoryProfileSnapshot() {
    await runAction(async () => {
      const snapshot = await refreshAgentMemoryProfileSnapshot(worldId, agentId);
      setMemoryProfileSnapshot(snapshot);
    }, "Memory profile snapshot refreshed.");
  }

  async function handleForgetMemory() {
    await runAction(async () => {
      await forgetAgentMemory(worldId, agentId);
      setMemoryItems([]);
      setMemoryProfileSnapshot(null);
    }, "Agent long-term memory forgotten.");
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
            <select className="text-input" name="narrative_role" defaultValue={agent.narrative_role ?? ""}>
              <option value="">Narrative role unset</option>
              <option value="protagonist">protagonist</option>
              <option value="main_character">main_character</option>
              <option value="side_character">side_character</option>
              <option value="supporting_cast">supporting_cast</option>
              <option value="ordinary_member">ordinary_member</option>
              <option value="organization_member">organization_member</option>
              <option value="original_character">original_character</option>
              <option value="narrative_agent">narrative_agent</option>
            </select>
            <select className="text-input" name="importance" defaultValue={agent.importance ?? ""}>
              <option value="">Importance unset</option>
              <option value="lead">lead</option>
              <option value="major">major</option>
              <option value="minor">minor</option>
              <option value="background">background</option>
            </select>
            <select className="text-input" name="canon_status" defaultValue={agent.canon_status ?? ""}>
              <option value="">Canon status unset</option>
              <option value="canon">canon</option>
              <option value="post_canon">post_canon</option>
              <option value="alternate">alternate</option>
              <option value="original_expansion">original_expansion</option>
            </select>
            <select
              className="text-input"
              name="character_category"
              defaultValue={agent.character_category ?? ""}
            >
              <option value="">Character category unset</option>
              <option value="player">player</option>
              <option value="main_character">main_character</option>
              <option value="side_character">side_character</option>
              <option value="ordinary_member">ordinary_member</option>
              <option value="organization_member">organization_member</option>
              <option value="original_character">original_character</option>
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
              name="character_profile"
              rows={5}
              defaultValue={JSON.stringify(agent.character_profile ?? {}, null, 2)}
            />
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

      <section className="management-panel" aria-labelledby="character-profile-title">
        <h2 className="section-title" id="character-profile-title">
          Character profile sheet
        </h2>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Role</p>
            <p className="metric-value">{agent.narrative_role ?? "unset"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Importance</p>
            <p className="metric-value">{agent.importance ?? "unset"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Continuity</p>
            <p className="metric-value">{agent.canon_status ?? "unset"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Category</p>
            <p className="metric-value">{agent.character_category ?? "unset"}</p>
          </div>
        </div>
        <pre>{JSON.stringify(agent.character_profile ?? {}, null, 2)}</pre>
      </section>

      <section className="management-panel" aria-labelledby="relationships-title">
        <h2 className="section-title" id="relationships-title">
          Relationship graph
        </h2>
        {data.canManageSelectedWorld ? (
          <form className="management-form" onSubmit={handleCreateRelationship}>
            <select className="text-input" name="target_agent_id" defaultValue="">
              <option value="">Target agent</option>
              {data.agents
                .filter((candidate) => candidate.id !== agentId)
                .map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.display_name}
                  </option>
                ))}
            </select>
            <select className="text-input" name="relationship_type" defaultValue="friendship">
              <option value="affection">affection</option>
              <option value="friendship">friendship</option>
              <option value="rivalry">rivalry</option>
              <option value="family">family</option>
              <option value="alliance">alliance</option>
              <option value="hostility">hostility</option>
              <option value="obligation">obligation</option>
              <option value="debt">debt</option>
              <option value="secret">secret</option>
              <option value="custom">custom</option>
            </select>
            <RelationshipScoreInputs />
            <textarea className="text-input" name="metadata" rows={3} placeholder="{}" />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create relationship
            </button>
          </form>
        ) : null}
        {relationships.length === 0 ? (
          <ResourceList rows={[]} />
        ) : (
          <div className="resource-list">
            {relationships.map((edge) => (
              <article className="resource-row" key={edge.id}>
                <div>
                  <h3>
                    {edge.target_display_name} - {edge.relationship_type}
                  </h3>
                  <p>
                    affection {edge.affection} / trust {edge.trust} / hostility {edge.hostility} /
                    intimacy {edge.intimacy}
                  </p>
                  <p>
                    obligation {edge.obligation} / rivalry {edge.rivalry} / debt {edge.debt}
                  </p>
                  <pre>{JSON.stringify(edge.metadata, null, 2)}</pre>
                </div>
                {data.canManageSelectedWorld ? (
                  <form
                    className="inline-form"
                    onSubmit={(event) => void handleUpdateRelationship(edge.id, event)}
                  >
                    <RelationshipScoreInputs edge={edge} />
                    <textarea
                      className="text-input"
                      name="metadata"
                      rows={2}
                      defaultValue={JSON.stringify(edge.metadata, null, 2)}
                    />
                    <button className="secondary-button" type="submit" disabled={isBusy}>
                      Update edge
                    </button>
                  </form>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="persona-title">
          <h2 className="section-title" id="persona-title">
            Persona
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handlePersona}>
              <select
                aria-label="Persona policy plugin"
                className="text-input"
                name="policy_plugin_identifier"
                defaultValue={
                  data.agentPersona?.policy_plugin_identifier
                  ?? data.personaPolicyPlugins[0]?.identifier
                  ?? ""
                }
              >
                {data.personaPolicyPlugins.map((plugin) => (
                  <option key={plugin.identifier} value={plugin.identifier}>
                    {plugin.identifier}
                  </option>
                ))}
              </select>
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
              <textarea
                className="text-input"
                name="policy_plugin_config"
                rows={3}
                defaultValue={JSON.stringify(data.agentPersona?.policy_plugin_config ?? {}, null, 2)}
                placeholder="Policy plugin config"
              />
              <label className="checkbox-label">
                <input
                  name="is_enabled"
                  type="checkbox"
                  defaultChecked={data.agentPersona?.is_enabled ?? true}
                />
                Persona enabled
              </label>
              <div className="button-row">
                <button className="primary-button" type="submit">
                  Save persona
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={(event) => {
                    const form = event.currentTarget.form;
                    if (form !== null) {
                      void handleValidatePersona(form);
                    }
                  }}
                >
                  Validate persona
                </button>
              </div>
            </form>
          ) : (
            <>
              <p>
                Plugin: {data.agentPersona?.policy_plugin_identifier ?? "No persona plugin configured."}
              </p>
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
                <input className="text-input" name="confidence_score" placeholder="Confidence 0-1" />
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
              detail: `${observation.content} - ${observation.review_status} - used ${observation.runtime_use_count}`,
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
          <p>Long-term memory is written asynchronously by runtime. This view is read-only.</p>
          {data.canManageSelectedWorld ? (
            <div className="button-row">
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => void handleRefreshMemoryProfileSnapshot()}
              >
                Refresh memory profile
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => void handleForgetMemory()}
              >
                Forget agent memory
              </button>
            </div>
          ) : null}
          <div className="resource-list">
            <article className="resource-row">
              <div>
                <h3>Profile snapshot</h3>
                <p>{memoryProfileDetail(memoryProfileSnapshot)}</p>
              </div>
            </article>
          </div>
          <form className="inline-form" onSubmit={handleMemorySearch}>
            <textarea className="text-input" name="query_text" placeholder="Search memory context" rows={4} />
            <input className="text-input" name="limit" placeholder="10" />
            <div className="button-row">
              <button className="primary-button" type="submit" disabled={isBusy}>
                Search memory
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => void handleRefreshMemory()}
              >
                Refresh memory
              </button>
            </div>
          </form>
          <ResourceList
            rows={memoryItems.map((item) => ({
              id: item.id,
              title: item.content,
              detail: memoryDetail(item),
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
        {data.agentRuns.length === 0 ? (
          <ResourceList rows={[]} />
        ) : (
          <div className="resource-list">
            {data.agentRuns.map((run) => (
              <article className="resource-row" key={run.run_id}>
                <div>
                  <h3>{run.status}</h3>
                  <p>{run.trigger_source}</p>
                  <p>{run.response_text ?? run.prompt_text}</p>
                </div>
                {data.canManageSelectedWorld ? (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => void inspectRun(run.run_id)}
                  >
                    Inspect run
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        )}
        {selectedRunDetail !== null ? (
          <section aria-labelledby="run-inspector-title">
            <h3 id="run-inspector-title">Run inspector</h3>
            <p className="status-detail">
              Provider: {selectedRunDetail.provider_profile?.profile_key ?? "none"}
            </p>
            <p className="status-detail">
              Sources: {selectedRunDetail.run.source_calendar_entry_id ?? "no calendar"} /{" "}
              {selectedRunDetail.run.source_schedule_rule_id ?? "no schedule"}
            </p>
            <p className="status-detail">
              Conversation turns: {selectedRunDetail.conversation_turns.length}
            </p>
            <pre>{JSON.stringify(selectedRunDetail.run.diagnostics, null, 2)}</pre>
          </section>
        ) : null}
      </section>
    </section>
  );
}

function personaInputFromForm(form: FormData) {
  return {
    persona_text: formString(form, "persona_text"),
    behavior_policy: jsonObject(formString(form, "behavior_policy")),
    policy_plugin_identifier: formString(form, "policy_plugin_identifier"),
    policy_plugin_config: jsonObject(formString(form, "policy_plugin_config")),
    is_enabled: form.get("is_enabled") === "on",
  };
}

function optionalNumber(form: FormData, key: string): number | null {
  const value = optionalFormString(form, key);
  if (value === null) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function numberValue(form: FormData, key: string, fallback: number): number {
  const value = optionalNumber(form, key);
  return value ?? fallback;
}

function RelationshipScoreInputs({ edge }: { edge?: AgentRelationship }) {
  return (
    <>
      <input className="text-input" name="affection" defaultValue={edge?.affection ?? 0} placeholder="Affection" />
      <input className="text-input" name="trust" defaultValue={edge?.trust ?? 0} placeholder="Trust" />
      <input className="text-input" name="hostility" defaultValue={edge?.hostility ?? 0} placeholder="Hostility" />
      <input className="text-input" name="intimacy" defaultValue={edge?.intimacy ?? 0} placeholder="Intimacy" />
      <input className="text-input" name="obligation" defaultValue={edge?.obligation ?? 0} placeholder="Obligation" />
      <input className="text-input" name="rivalry" defaultValue={edge?.rivalry ?? 0} placeholder="Rivalry" />
      <input className="text-input" name="debt" defaultValue={edge?.debt ?? 0} placeholder="Debt" />
    </>
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

function memoryDetail(item: AgentDetailData["memoryItems"][number]): string {
  const parts = [
    `backend ${item.backend}`,
    item.created_at ?? "unknown time",
    item.score === null ? null : `score ${item.score.toFixed(2)}`,
    attribution(item.metadata),
  ].filter((part): part is string => part !== null && part !== "");
  return parts.join(" - ");
}

function memoryProfileDetail(snapshot: AgentDetailData["memoryProfileSnapshot"]): string {
  if (snapshot === null) {
    return "No structured memory profile snapshot yet.";
  }
  return [
    `aliases ${snapshot.aliases.length}`,
    `identity ${snapshot.identity_notes.length}`,
    `preferences ${snapshot.durable_preferences.length}`,
    `goals ${snapshot.long_lived_goals.length}`,
    `style ${snapshot.language_style_preferences.length}`,
    `refreshed ${snapshot.refreshed_at}`,
  ].join(" - ");
}

function attribution(metadata: Record<string, unknown>): string {
  if (typeof metadata.turn_id === "string") {
    return `turn ${metadata.turn_id}`;
  }
  if (typeof metadata.run_id === "string") {
    return `run ${metadata.run_id}`;
  }
  if (typeof metadata.source_event_id === "string") {
    return `event ${metadata.source_event_id}`;
  }
  if (typeof metadata.conversation_id === "string") {
    return `conversation ${metadata.conversation_id}`;
  }
  return "";
}
