"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  advanceWorldClock,
  createScene,
  createScheduleRule,
  createSnapshot,
  deactivateScene,
  deleteMembership,
  exportWorldComposition,
  importWorldComposition,
  listMemberCandidates,
  pauseWorldClock,
  resumeWorldClock,
  skipWorldClock,
  updateWorld,
  upsertMembership,
} from "@/lib/worlds/client";
import { subscribeToEventStream } from "@/lib/realtime";
import type { WorldStreamEnvelope } from "@/lib/realtime";
import type { WorldWorkspaceData } from "@/lib/worlds/server";
import type {
  MemberCandidate,
  RuntimeDiagnostic,
  WorldClock,
  WorldRole,
} from "@/lib/worlds/types";
import {
  formString,
  jsonObject,
  messageForError,
  optionalFormString,
} from "@/features/workspace/form-utils";

type WorldOverviewProps = {
  data: WorldWorkspaceData;
};

export function WorldOverview({ data }: WorldOverviewProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [memberCandidates, setMemberCandidates] = useState<MemberCandidate[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [clock, setClock] = useState(data.clock);
  const [worldDiagnostics, setWorldDiagnostics] = useState(data.worldDiagnostics);
  const [exportedComposition, setExportedComposition] = useState("");
  const [compositionDraft, setCompositionDraft] = useState("");
  const world = data.selectedWorld;

  useEffect(() => {
    setClock(data.clock);
    setWorldDiagnostics(data.worldDiagnostics);
  }, [data.clock, data.worldDiagnostics]);

  useEffect(() => {
    if (world === null) {
      return;
    }
    return subscribeToEventStream<WorldStreamEnvelope["payload"]>(
      `/api/worlds/${world.id}/stream`,
      (envelope) => {
        if (envelope.payload.clock !== undefined) {
          setClock(envelope.payload.clock);
        }
        if (envelope.payload.diagnostics.length > 0) {
          setWorldDiagnostics((current) =>
            mergeWorldDiagnostics(current, envelope.payload.diagnostics),
          );
        }
      },
    );
  }, [world]);

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

  if (world === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{notice ?? "World not found."}</p>
      </section>
    );
  }
  const selectedWorld = world;

  async function handleUpdateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateWorld(selectedWorld.id, {
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          memory_plugin_identifier: formString(form, "memory_plugin_identifier"),
          memory_plugin_config: jsonObject(formString(form, "memory_plugin_config")),
          world_rules_plugin_identifier: formString(form, "world_rules_plugin_identifier"),
          world_rules_plugin_config: jsonObject(formString(form, "world_rules_plugin_config")),
        }),
      "World saved.",
    );
  }

  async function handleCreateScene(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createScene(selectedWorld.id, {
          scene_key: formString(form, "scene_key"),
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
        });
        formElement.reset();
      },
      "Scene created.",
    );
  }

  async function handleSearchUsers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setMemberCandidates(await listMemberCandidates(selectedWorld.id, formString(form, "query")));
    }, "User search completed.");
  }

  async function setMembership(userId: string, role: WorldRole) {
    await runAction(
      () => upsertMembership(selectedWorld.id, userId, role),
      "Membership saved.",
    );
  }

  async function handleCreateRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createScheduleRule(selectedWorld.id, {
          rule_key: formString(form, "rule_key"),
          name: formString(form, "name"),
          kind: formString(form, "kind") as "weekday" | "weekend" | "timetable",
          config: jsonObject(formString(form, "config")),
        });
        formElement.reset();
      },
      "Schedule rule created.",
    );
  }

  async function handleExportComposition() {
    await runAction(async () => {
      const composition = await exportWorldComposition(selectedWorld.id);
      const text = JSON.stringify(composition, null, 2);
      setExportedComposition(text);
      setCompositionDraft(text);
    }, "Composition exported.");
  }

  async function handleImportComposition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      async () => {
        const importedWorld = await importWorldComposition({
          slug: formString(form, "slug"),
          name: formString(form, "name"),
          owner_user_id: formString(form, "owner_user_id"),
          description: optionalFormString(form, "description"),
          rules_config:
            optionalFormString(form, "rules_config") === null
              ? undefined
              : jsonObject(formString(form, "rules_config")),
          composition: JSON.parse(formString(form, "composition")),
        });
        window.location.assign(`/worlds/${importedWorld.id}`);
      },
      "Composition imported.",
      false,
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="dashboard-grid" aria-label="World metrics">
        <div className="metric">
          <p className="metric-label">Scenes</p>
          <p className="metric-value">{data.scenes.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Agents</p>
          <p className="metric-value">{data.agents.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Members</p>
          <p className="metric-value">{data.memberships.length}</p>
        </div>
      </section>

      <section className="management-panel" aria-labelledby="world-title">
        <h2 className="section-title" id="world-title">
          {world.name}
        </h2>
        <p>
          {world.slug} - {world.is_active ? "Active" : "Inactive"}
        </p>
        <p>{world.description ?? "No description."}</p>
        {data.canManageSelectedWorld ? (
          <form className="management-form" onSubmit={handleUpdateWorld}>
            <input className="text-input" name="name" defaultValue={world.name} />
            <input
              className="text-input"
              name="description"
              defaultValue={world.description ?? ""}
              placeholder="Description"
            />
            <select
              aria-label="World memory plugin"
              className="text-input"
              name="memory_plugin_identifier"
              defaultValue={world.memory_plugin_identifier}
            >
              {data.memoryPlugins.map((plugin) => (
                <option key={plugin.identifier} value={plugin.identifier}>
                  {plugin.identifier}
                </option>
              ))}
            </select>
            <textarea
              className="text-input"
              name="memory_plugin_config"
              rows={3}
              defaultValue={JSON.stringify(world.memory_plugin_config, null, 2)}
              placeholder="Memory plugin config"
            />
            <select
              aria-label="World rules plugin"
              className="text-input"
              name="world_rules_plugin_identifier"
              defaultValue={world.world_rules_plugin_identifier}
            >
              {data.worldRulesPlugins.map((plugin) => (
                <option key={plugin.identifier} value={plugin.identifier}>
                  {plugin.identifier}
                </option>
              ))}
            </select>
            <textarea
              className="text-input"
              name="world_rules_plugin_config"
              rows={3}
              defaultValue={JSON.stringify(world.world_rules_plugin_config, null, 2)}
              placeholder="World rules plugin config"
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Save world
            </button>
          </form>
        ) : (
          <>
            <p>Read-only world access.</p>
            <p>Memory plugin: {world.memory_plugin_identifier}</p>
            <p>World rules plugin: {world.world_rules_plugin_identifier}</p>
          </>
        )}
      </section>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="scenes-title">
          <h2 className="section-title" id="scenes-title">
            Scenes
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handleCreateScene}>
              <input className="text-input" name="scene_key" placeholder="scene-key" />
              <input className="text-input" name="name" placeholder="Scene name" />
              <input className="text-input" name="description" placeholder="Description" />
              <button className="primary-button" type="submit" disabled={isBusy}>
                Create scene
              </button>
            </form>
          ) : null}
          <div className="resource-list">
            {data.scenes.length === 0 ? (
              <article className="resource-row">
                <div>
                  <h3>None yet</h3>
                  <p>No records are available.</p>
                </div>
              </article>
            ) : (
              data.scenes.map((scene) => (
                <article className="resource-row" key={scene.id}>
                  <div>
                    <h3>{scene.name}</h3>
                    <p>
                      {scene.scene_key} - {scene.is_active ? "Active" : "Inactive"}
                    </p>
                  </div>
                  {data.canManageSelectedWorld ? (
                    <div className="button-row">
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isBusy}
                        onClick={() =>
                          runAction(
                            () => deactivateScene(selectedWorld.id, scene.id),
                            "Scene deactivated.",
                          )
                        }
                      >
                        Deactivate scene
                      </button>
                    </div>
                  ) : null}
                </article>
              ))
            )}
          </div>
        </section>

        <section className="management-panel" aria-labelledby="members-title">
          <h2 className="section-title" id="members-title">
            Members
          </h2>
          {data.canManageSelectedWorld ? (
            <form className="inline-form" onSubmit={handleSearchUsers}>
              <input
                className="text-input"
                name="query"
                placeholder="Search email or display name"
              />
              <button className="secondary-button" type="submit" disabled={isBusy}>
                Search users
              </button>
            </form>
          ) : null}
          <div className="resource-list">
            {memberCandidates.map((candidate) => (
              <article className="resource-row" key={candidate.id}>
                <div>
                  <h3>{candidate.display_name}</h3>
                  <p>
                    {candidate.email} - {candidate.role ?? "not a member"}
                  </p>
                </div>
                <div className="button-row">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => setMembership(candidate.id, "human_user")}
                  >
                    Set human user
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => setMembership(candidate.id, "world_admin")}
                  >
                    Set world admin
                  </button>
                </div>
              </article>
            ))}
            {data.memberships.map((membership) => (
              <article className="resource-row" key={membership.id}>
                <div>
                  <h3>{membership.user.display_name}</h3>
                  <p>
                    {membership.user.email} - {membership.role}
                  </p>
                </div>
                {data.canManageSelectedWorld ? (
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={isBusy}
                      onClick={() =>
                        runAction(
                          () => deleteMembership(selectedWorld.id, membership.user_id),
                          "Membership removed.",
                        )
                      }
                    >
                      Remove member
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      </div>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="clock-title">
          <h2 className="section-title" id="clock-title">
            World clock
          </h2>
          {clock !== null ? (
            <>
              <div className="clock-grid">
                <div>
                  <p className="metric-label">Status</p>
                  <p className="metric-value">{clock.status}</p>
                </div>
                <div>
                  <p className="metric-label">Effective time</p>
                  <p>{clock.effective_world_time}</p>
                </div>
                <div>
                  <p className="metric-label">Revision</p>
                  <p className="metric-value">{clock.revision}</p>
                </div>
              </div>
              {data.canManageSelectedWorld ? (
                <div className="clock-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => pauseWorldClock(selectedWorld.id), "Clock paused.")
                    }
                  >
                    Pause clock
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => resumeWorldClock(selectedWorld.id), "Clock resumed.")
                    }
                  >
                    Resume clock
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      runAction(() => advanceWorldClock(selectedWorld.id), "Clock advanced.")
                    }
                  >
                    Advance clock
                  </button>
                  <form
                    className="inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void runAction(
                        () =>
                          skipWorldClock(
                            selectedWorld.id,
                            formString(form, "target_world_time"),
                          ),
                        "Clock skipped.",
                      );
                    }}
                  >
                    <input
                      className="text-input"
                      name="target_world_time"
                      placeholder="2030-01-01T00:00:00Z"
                    />
                    <button className="secondary-button" type="submit">
                      Skip clock
                    </button>
                  </form>
                  <form
                    className="inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void runAction(
                        () =>
                          resumeWorldClock(
                            selectedWorld.id,
                            optionalFormString(form, "speed_multiplier") ?? undefined,
                          ),
                        "Clock resumed.",
                      );
                    }}
                  >
                    <input
                      className="text-input"
                      name="speed_multiplier"
                      placeholder="Speed multiplier"
                    />
                    <button className="secondary-button" type="submit">
                      Resume with multiplier
                    </button>
                  </form>
                </div>
              ) : null}
            </>
          ) : (
            <p>Clock state unavailable.</p>
          )}
        </section>

        <section className="management-panel" aria-labelledby="replay-title">
          <h2 className="section-title" id="replay-title">
            Replay and snapshots
          </h2>
          <p>Replay sequence: {data.replayState?.source_sequence ?? 0}</p>
          <p>Unhandled events: {data.replayState?.unhandled_event_count ?? 0}</p>
          <p>
            Latest snapshot:{" "}
            {data.latestSnapshot === null
              ? "none"
              : `covers sequence ${data.latestSnapshot.covers_event_sequence}`}
          </p>
          {data.canManageSelectedWorld ? (
            <button
              className="primary-button"
              type="button"
              onClick={() => runAction(() => createSnapshot(selectedWorld.id), "Snapshot created.")}
            >
              Create snapshot
            </button>
          ) : null}
        </section>
      </div>

      <section className="management-panel" aria-labelledby="rules-title">
        <h2 className="section-title" id="rules-title">
          Schedule rules
        </h2>
        {data.canManageSelectedWorld ? (
          <form className="management-form" onSubmit={handleCreateRule}>
            <input className="text-input" name="rule_key" placeholder="rule-key" />
            <input className="text-input" name="name" placeholder="Rule name" />
            <select className="text-input" name="kind" defaultValue="weekday">
              <option value="weekday">weekday</option>
              <option value="weekend">weekend</option>
              <option value="timetable">timetable</option>
            </select>
            <input className="text-input" name="config" placeholder="{}" />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create schedule rule
            </button>
          </form>
        ) : null}
        <ResourceList
          rows={data.scheduleRules.map((rule) => ({
            id: rule.id,
            title: rule.name,
            detail: `${rule.rule_key} - ${rule.kind} - ${
              rule.is_enabled ? "Enabled" : "Disabled"
            }`,
          }))}
        />
      </section>

      <section className="management-panel" aria-labelledby="next-title">
        <h2 className="section-title" id="next-title">
          Workspace pages
        </h2>
        <div className="button-row">
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/agents`}>
            Build agents
          </Link>
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/conversations`}>
            Open conversations
          </Link>
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/narrative`}>
            Narrative artifacts
          </Link>
          <Link className="secondary-button" href={`/worlds/${selectedWorld.id}/reader`}>
            Reader
          </Link>
        </div>
      </section>

      <section className="management-panel" aria-labelledby="composition-title">
        <h2 className="section-title" id="composition-title">
          World composition
        </h2>
        {data.canManageSelectedWorld ? (
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() => void handleExportComposition()}
            >
              Export composition
            </button>
          </div>
        ) : (
          <p>Read-only world composition access.</p>
        )}
        <textarea
          className="text-input"
          rows={10}
          readOnly
          value={exportedComposition}
          placeholder="Exported composition JSON appears here."
        />
        {data.isPlatformAdmin ? (
          <form className="management-form" onSubmit={handleImportComposition}>
            <input className="text-input" name="slug" placeholder="imported-world-slug" />
            <input className="text-input" name="name" placeholder="Imported world name" />
            <input
              className="text-input"
              name="owner_user_id"
              defaultValue={selectedWorld.owner_user_id}
              placeholder="Owner user id"
            />
            <input className="text-input" name="description" placeholder="Override description" />
            <textarea
              className="text-input"
              name="rules_config"
              rows={3}
              defaultValue={JSON.stringify(selectedWorld.rules_config, null, 2)}
            />
            <textarea
              className="text-input"
              name="composition"
              rows={10}
              value={compositionDraft}
              onChange={(event) => setCompositionDraft(event.target.value)}
              placeholder="Paste exported composition JSON"
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Import as new world
            </button>
          </form>
        ) : null}
        <p>
          Export includes world metadata, scenes, agents, schedule rules, and preset references.
          It excludes memberships, auth/session, clock state, events, diagnostics, memory,
          observations, conversations, and narrative artifacts.
        </p>
      </section>

      <section className="management-panel" aria-labelledby="world-diagnostics-title">
        <h2 className="section-title" id="world-diagnostics-title">
          World diagnostics
        </h2>
        <ResourceList
          rows={worldDiagnostics.map((diagnostic) => ({
            id: diagnostic.id,
            title: `${diagnostic.severity} - ${diagnostic.component}`,
            detail: diagnostic.message,
          }))}
        />
      </section>
    </section>
  );
}

function mergeWorldDiagnostics(
  current: RuntimeDiagnostic[],
  incoming: RuntimeDiagnostic[],
): RuntimeDiagnostic[] {
  const byId = new Map(current.map((diagnostic) => [diagnostic.id, diagnostic]));
  for (const diagnostic of incoming) {
    byId.set(diagnostic.id, diagnostic);
  }
  return Array.from(byId.values()).sort((left, right) =>
    right.occurred_at.localeCompare(left.occurred_at),
  );
}

function ResourceList({ rows }: { rows: { id: string; title: string; detail: string }[] }) {
  if (rows.length === 0) {
    return (
      <div className="resource-list">
        <article className="resource-row">
          <div>
            <h3>None yet</h3>
            <p>No records are available.</p>
          </div>
        </article>
      </div>
    );
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
