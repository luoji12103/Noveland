"use client";

import { FormEvent, type ReactNode, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import type { AuthSubject } from "@/lib/auth/types";
import {
  createAgent,
  createScene,
  createWorld,
  deactivateAgent,
  deactivateScene,
  deactivateWorld,
  deleteMembership,
  listAgents,
  listMemberCandidates,
  listMemberships,
  listScenes,
  updateAgent,
  updateScene,
  updateWorld,
  upsertMembership,
  WorldClientError,
} from "@/lib/worlds/client";
import type {
  Agent,
  AgentKind,
  MemberCandidate,
  Membership,
  Scene,
  World,
  WorldDashboardData,
  WorldRole,
} from "@/lib/worlds/types";

type WorldManagementDashboardProps = {
  subject: AuthSubject;
  initialData: WorldDashboardData;
};

export function WorldManagementDashboard({
  subject,
  initialData,
}: WorldManagementDashboardProps) {
  const router = useRouter();
  const [worlds, setWorlds] = useState(initialData.worlds);
  const [selectedWorldId, setSelectedWorldId] = useState(initialData.selectedWorldId);
  const [scenes, setScenes] = useState(initialData.scenes);
  const [agents, setAgents] = useState(initialData.agents);
  const [memberships, setMemberships] = useState(initialData.memberships);
  const [canManageSelectedWorld, setCanManageSelectedWorld] = useState(
    initialData.canManageSelectedWorld,
  );
  const [memberCandidates, setMemberCandidates] = useState<MemberCandidate[]>([]);
  const [notice, setNotice] = useState(initialData.loadError);
  const [isBusy, setIsBusy] = useState(false);

  const selectedWorld = useMemo(
    () => worlds.find((world) => world.id === selectedWorldId) ?? null,
    [selectedWorldId, worlds],
  );
  const isPlatformAdmin = subject.roles.includes("platform_admin");
  const canManage = selectedWorld !== null && canManageSelectedWorld;

  async function handleSelectWorld(nextWorldId: string) {
    if (nextWorldId === "") {
      return;
    }
    router.replace(`/?world=${nextWorldId}`);
    await loadWorld(nextWorldId);
  }

  async function loadWorld(worldId: string) {
    await runAction(async () => {
      const [nextScenes, nextAgents, nextMemberships] = await Promise.all([
        listScenes(worldId),
        listAgents(worldId),
        listMembershipsIfAllowed(worldId),
      ]);
      setSelectedWorldId(worldId);
      setScenes(nextScenes);
      setAgents(nextAgents);
      setMemberships(nextMemberships ?? []);
      setCanManageSelectedWorld(nextMemberships !== null);
      setMemberCandidates([]);
    });
  }

  async function handleCreateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const slug = formString(form, "slug");
    const name = formString(form, "name");
    if (slug === "" || name === "") {
      setNotice("World slug and name are required.");
      return;
    }

    await runAction(async () => {
      const world = await createWorld({ slug, name, description: optionalFormString(form, "description") });
      setWorlds((currentWorlds) => [...currentWorlds, world].sort(compareWorlds));
      setSelectedWorldId(world.id);
      setScenes([]);
      setAgents([]);
      setMemberships([
        {
          id: "local-owner",
          world_id: world.id,
          user_id: subject.user_id,
          role: "world_admin",
          user: {
            id: subject.user_id,
            email: subject.email,
            display_name: subject.display_name,
            is_active: true,
          },
        },
      ]);
      setCanManageSelectedWorld(true);
      setMemberCandidates([]);
      router.replace(`/?world=${world.id}`);
      event.currentTarget.reset();
    }, "World created.");
  }

  async function handleUpdateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const world = await updateWorld(selectedWorld.id, {
        name: formString(form, "name"),
        description: optionalFormString(form, "description"),
        is_active: form.get("is_active") === "on",
      });
      setWorlds((currentWorlds) => replaceById(currentWorlds, world));
    }, "World updated.");
  }

  async function handleDeactivateWorld() {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deactivateWorld(selectedWorld.id);
      setWorlds((currentWorlds) =>
        currentWorlds.map((world) =>
          world.id === selectedWorld.id ? { ...world, is_active: false } : world,
        ),
      );
    }, "World deactivated.");
  }

  async function handleCreateScene(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const scene_key = formString(form, "scene_key");
    const name = formString(form, "name");
    if (scene_key === "" || name === "") {
      setNotice("Scene key and name are required.");
      return;
    }
    await runAction(async () => {
      const scene = await createScene(selectedWorld.id, {
        scene_key,
        name,
        description: optionalFormString(form, "description"),
      });
      setScenes((currentScenes) => [...currentScenes, scene].sort(compareScenes));
      event.currentTarget.reset();
    }, "Scene created.");
  }

  async function handleUpdateScene(event: FormEvent<HTMLFormElement>, scene: Scene) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedScene = await updateScene(selectedWorld.id, scene.id, {
        name: formString(form, "name"),
        description: optionalFormString(form, "description"),
        is_active: form.get("is_active") === "on",
      });
      setScenes((currentScenes) => replaceById(currentScenes, updatedScene));
    }, "Scene updated.");
  }

  async function handleDeactivateScene(scene: Scene) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deactivateScene(selectedWorld.id, scene.id);
      setScenes((currentScenes) =>
        currentScenes.map((currentScene) =>
          currentScene.id === scene.id ? { ...currentScene, is_active: false } : currentScene,
        ),
      );
    }, "Scene deactivated.");
  }

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const agent_key = formString(form, "agent_key");
    const display_name = formString(form, "display_name");
    if (agent_key === "" || display_name === "") {
      setNotice("Agent key and display name are required.");
      return;
    }
    await runAction(async () => {
      const agent = await createAgent(selectedWorld.id, {
        agent_key,
        display_name,
        kind: formString(form, "kind") as AgentKind,
        home_scene_id: optionalFormString(form, "home_scene_id"),
        config: jsonObject(formString(form, "config")),
      });
      setAgents((currentAgents) => [...currentAgents, agent].sort(compareAgents));
      event.currentTarget.reset();
    }, "Agent created.");
  }

  async function handleUpdateAgent(event: FormEvent<HTMLFormElement>, agent: Agent) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updatedAgent = await updateAgent(selectedWorld.id, agent.id, {
        display_name: formString(form, "display_name"),
        home_scene_id: optionalFormString(form, "home_scene_id"),
        config: jsonObject(formString(form, "config")),
        is_enabled: form.get("is_enabled") === "on",
      });
      setAgents((currentAgents) => replaceById(currentAgents, updatedAgent));
    }, "Agent updated.");
  }

  async function handleDeactivateAgent(agent: Agent) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deactivateAgent(selectedWorld.id, agent.id);
      setAgents((currentAgents) =>
        currentAgents.map((currentAgent) =>
          currentAgent.id === agent.id ? { ...currentAgent, is_enabled: false } : currentAgent,
        ),
      );
    }, "Agent deactivated.");
  }

  async function handleSearchMembers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedWorld === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setMemberCandidates(await listMemberCandidates(selectedWorld.id, formString(form, "query")));
    });
  }

  async function handleUpsertMembership(candidate: MemberCandidate, role: WorldRole) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      const membership = await upsertMembership(selectedWorld.id, candidate.id, role);
      setMemberships((currentMemberships) => upsertByUserId(currentMemberships, membership));
      setMemberCandidates((currentCandidates) =>
        currentCandidates.map((currentCandidate) =>
          currentCandidate.id === candidate.id ? { ...currentCandidate, role } : currentCandidate,
        ),
      );
    }, "Membership saved.");
  }

  async function handleDeleteMembership(membership: Membership) {
    if (selectedWorld === null) {
      return;
    }
    await runAction(async () => {
      await deleteMembership(selectedWorld.id, membership.user_id);
      setMemberships((currentMemberships) =>
        currentMemberships.filter((currentMembership) => currentMembership.id !== membership.id),
      );
      setMemberCandidates((currentCandidates) =>
        currentCandidates.map((candidate) =>
          candidate.id === membership.user_id ? { ...candidate, role: null } : candidate,
        ),
      );
    }, "Membership removed.");
  }

  async function runAction(action: () => Promise<void>, successMessage?: string) {
    setNotice(null);
    setIsBusy(true);
    try {
      await action();
      if (successMessage !== undefined) {
        setNotice(successMessage);
      }
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section" aria-label="World management">
      {notice !== null ? (
        <p className="management-notice" role="status">
          {notice}
        </p>
      ) : null}

      <div className="dashboard-grid" aria-label="World overview">
        <Metric label="Worlds" value={`${worlds.length} visible`} />
        <Metric label="Scenes" value={selectedWorld === null ? "No world" : `${scenes.length} listed`} />
        <Metric label="Agents" value={selectedWorld === null ? "No world" : `${agents.length} listed`} />
      </div>

      <div className="world-toolbar">
        <label className="field-label" htmlFor="world-select">
          Active world
        </label>
        <select
          className="text-input"
          id="world-select"
          value={selectedWorldId ?? ""}
          onChange={(event) => void handleSelectWorld(event.target.value)}
        >
          {worlds.length === 0 ? <option value="">No worlds yet</option> : null}
          {worlds.map((world) => (
            <option key={world.id} value={world.id}>
              {world.name} ({world.slug})
            </option>
          ))}
        </select>
      </div>

      {isPlatformAdmin ? (
        <section className="management-panel" aria-label="Create world">
          <h2 className="section-title">Create world</h2>
          <form className="management-form" onSubmit={(event) => void handleCreateWorld(event)}>
            <input className="text-input" name="slug" placeholder="world-slug" />
            <input className="text-input" name="name" placeholder="World name" />
            <input className="text-input" name="description" placeholder="Description" />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create world
            </button>
          </form>
        </section>
      ) : null}

      {selectedWorld === null ? (
        <section className="management-panel">
          <h2 className="section-title">No world selected</h2>
          <p className="status-detail">Create or join a world to manage scenes and agents.</p>
        </section>
      ) : (
        <>
          <section className="management-panel" aria-label="Selected world" key={selectedWorld.id}>
            <h2 className="section-title">{selectedWorld.name}</h2>
            <p className="status-detail">
              {selectedWorld.slug} - {selectedWorld.is_active ? "Active" : "Inactive"}
            </p>
            {canManage ? (
              <form className="management-form" onSubmit={(event) => void handleUpdateWorld(event)}>
                <input className="text-input" name="name" defaultValue={selectedWorld.name} />
                <input
                  className="text-input"
                  name="description"
                  defaultValue={selectedWorld.description ?? ""}
                  placeholder="Description"
                />
                <label className="checkbox-label">
                  <input name="is_active" type="checkbox" defaultChecked={selectedWorld.is_active} />
                  Active
                </label>
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Save world
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() => void handleDeactivateWorld()}
                >
                  Deactivate world
                </button>
              </form>
            ) : (
              <p className="status-detail">Read-only world access.</p>
            )}
          </section>

          <section className="management-columns">
            <ResourcePanel title="Scenes">
              {canManage ? (
                <form className="management-form" onSubmit={(event) => void handleCreateScene(event)}>
                  <input className="text-input" name="scene_key" placeholder="scene-key" />
                  <input className="text-input" name="name" placeholder="Scene name" />
                  <input className="text-input" name="description" placeholder="Description" />
                  <button className="primary-button" type="submit" disabled={isBusy}>
                    Create scene
                  </button>
                </form>
              ) : null}
              <div className="resource-list">
                {scenes.map((scene) => (
                  <article className="resource-row" key={scene.id}>
                    <div>
                      <h3>{scene.name}</h3>
                      <p>{scene.scene_key} - {scene.is_active ? "Active" : "Inactive"}</p>
                    </div>
                    {canManage ? (
                      <form
                        className="inline-form"
                        onSubmit={(event) => void handleUpdateScene(event, scene)}
                      >
                        <input className="text-input" name="name" defaultValue={scene.name} />
                        <input
                          className="text-input"
                          name="description"
                          defaultValue={scene.description ?? ""}
                          placeholder="Description"
                        />
                        <label className="checkbox-label">
                          <input name="is_active" type="checkbox" defaultChecked={scene.is_active} />
                          Active
                        </label>
                        <button className="secondary-button" type="submit" disabled={isBusy}>
                          Save scene
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleDeactivateScene(scene)}
                        >
                          Deactivate scene
                        </button>
                      </form>
                    ) : null}
                  </article>
                ))}
              </div>
            </ResourcePanel>

            <ResourcePanel title="Agents">
              {canManage ? (
                <form className="management-form" onSubmit={(event) => void handleCreateAgent(event)}>
                  <input className="text-input" name="agent_key" placeholder="agent-key" />
                  <input className="text-input" name="display_name" placeholder="Display name" />
                  <select className="text-input" name="kind" defaultValue="role_agent">
                    <option value="role_agent">role_agent</option>
                    <option value="narrative_agent">narrative_agent</option>
                  </select>
                  <select className="text-input" name="home_scene_id" defaultValue="">
                    <option value="">No home scene</option>
                    {scenes.map((scene) => (
                      <option key={scene.id} value={scene.id}>
                        {scene.name}
                      </option>
                    ))}
                  </select>
                  <textarea className="text-input" name="config" placeholder="{}" rows={3} />
                  <button className="primary-button" type="submit" disabled={isBusy}>
                    Create agent
                  </button>
                </form>
              ) : null}
              <div className="resource-list">
                {agents.map((agent) => (
                  <article className="resource-row" key={agent.id}>
                    <div>
                      <h3>{agent.display_name}</h3>
                      <p>{agent.agent_key} - {agent.kind} - {agent.is_enabled ? "Enabled" : "Disabled"}</p>
                    </div>
                    {canManage ? (
                      <form
                        className="inline-form"
                        onSubmit={(event) => void handleUpdateAgent(event, agent)}
                      >
                        <input
                          className="text-input"
                          name="display_name"
                          defaultValue={agent.display_name}
                        />
                        <select className="text-input" name="home_scene_id" defaultValue={agent.home_scene_id ?? ""}>
                          <option value="">No home scene</option>
                          {scenes.map((scene) => (
                            <option key={scene.id} value={scene.id}>
                              {scene.name}
                            </option>
                          ))}
                        </select>
                        <textarea
                          className="text-input"
                          name="config"
                          defaultValue={JSON.stringify(agent.config)}
                          rows={3}
                        />
                        <label className="checkbox-label">
                          <input name="is_enabled" type="checkbox" defaultChecked={agent.is_enabled} />
                          Enabled
                        </label>
                        <button className="secondary-button" type="submit" disabled={isBusy}>
                          Save agent
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleDeactivateAgent(agent)}
                        >
                          Deactivate agent
                        </button>
                      </form>
                    ) : null}
                  </article>
                ))}
              </div>
            </ResourcePanel>
          </section>

          {canManage ? (
            <section className="management-panel" aria-label="World memberships">
              <h2 className="section-title">Members</h2>
              <form className="management-form" onSubmit={(event) => void handleSearchMembers(event)}>
                <input className="text-input" name="query" placeholder="Search email or display name" />
                <button className="secondary-button" type="submit" disabled={isBusy}>
                  Search users
                </button>
              </form>
              <div className="resource-list">
                {memberships.map((membership) => (
                  <article className="resource-row" key={membership.id}>
                    <div>
                      <h3>{membership.user.display_name}</h3>
                      <p>{membership.user.email} - {membership.role}</p>
                    </div>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={isBusy}
                      onClick={() => void handleDeleteMembership(membership)}
                    >
                      Remove member
                    </button>
                  </article>
                ))}
              </div>
              {memberCandidates.length > 0 ? (
                <div className="resource-list" aria-label="Member candidates">
                  {memberCandidates.map((candidate) => (
                    <article className="resource-row" key={candidate.id}>
                      <div>
                        <h3>{candidate.display_name}</h3>
                        <p>{candidate.email} - {candidate.role ?? "not a member"}</p>
                      </div>
                      <div className="button-row">
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleUpsertMembership(candidate, "human_user")}
                        >
                          Set human user
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleUpsertMembership(candidate, "world_admin")}
                        >
                          Set world admin
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null}
        </>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

function ResourcePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="management-panel">
      <h2 className="section-title">{title}</h2>
      {children}
    </section>
  );
}

async function listMembershipsIfAllowed(worldId: string): Promise<Membership[] | null> {
  try {
    return await listMemberships(worldId);
  } catch (error) {
    if (error instanceof WorldClientError && (error.status === 403 || error.status === 404)) {
      return null;
    }
    throw error;
  }
}

function formString(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function optionalFormString(form: FormData, key: string): string | null {
  const value = formString(form, key);
  return value === "" ? null : value;
}

function jsonObject(rawValue: string): Record<string, unknown> {
  if (rawValue.trim() === "") {
    return {};
  }
  const parsed = JSON.parse(rawValue) as unknown;
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Config must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

function messageForError(error: unknown): string {
  if (error instanceof WorldClientError) {
    if (error.status === 409) {
      return error.message;
    }
    if (error.status === 403) {
      return "Forbidden";
    }
    if (error.status === 422) {
      return "Check the fields and try again.";
    }
    return error.message;
  }
  if (error instanceof SyntaxError || error instanceof Error) {
    return error.message;
  }
  return "World request failed.";
}

function replaceById<T extends { id: string }>(items: T[], nextItem: T): T[] {
  return items.map((item) => (item.id === nextItem.id ? nextItem : item));
}

function upsertByUserId(items: Membership[], nextItem: Membership): Membership[] {
  const exists = items.some((item) => item.user_id === nextItem.user_id);
  if (!exists) {
    return [...items, nextItem].sort(compareMemberships);
  }
  return items
    .map((item) => (item.user_id === nextItem.user_id ? nextItem : item))
    .sort(compareMemberships);
}

function compareWorlds(left: World, right: World): number {
  return left.slug.localeCompare(right.slug);
}

function compareScenes(left: Scene, right: Scene): number {
  return left.scene_key.localeCompare(right.scene_key);
}

function compareAgents(left: Agent, right: Agent): number {
  return left.agent_key.localeCompare(right.agent_key);
}

function compareMemberships(left: Membership, right: Membership): number {
  return left.user.email.localeCompare(right.user.email);
}
