"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  bindPlayerActor,
  createIntervention,
  previewPlayerChoiceConsequences,
  recordPlayerChoice,
} from "@/lib/worlds/client";
import type { PlayerInteractionData } from "@/lib/worlds/server";
import type { ChoiceConsequencePreview, PlayerChoiceCreateInput } from "@/lib/worlds/types";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type PlayerInteractionsProps = {
  worldId: string;
  data: PlayerInteractionData;
};

type NoticeTone = "success" | "warning" | "error";

export function PlayerInteractions({ worldId, data }: PlayerInteractionsProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<{ message: string; tone: NoticeTone } | null>(null);
  const [preview, setPreview] = useState<ChoiceConsequencePreview | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const activeActor = data.playerActors[0] ?? null;
  const latestRouteChoice =
    data.playerChoices.find((choice) => choice.choice_kind === "route") ?? data.playerChoices[0] ?? null;
  const routeDiagnostics = useMemo(
    () => safeDiagnostics(preview, latestRouteChoice?.consequence_preview ?? null),
    [latestRouteChoice, preview],
  );

  if (data.selectedWorld === null) {
    return (
      <section className="management-section">
        <p className="management-notice" data-tone="error">
          {data.loadError ?? "Player interactions are unavailable."}
        </p>
      </section>
    );
  }

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ message: successMessage, tone: "success" });
      router.refresh();
    } catch (error) {
      setNotice({ message: messageForError(error), tone: "error" });
    } finally {
      setIsBusy(false);
    }
  }

  async function handleBindActor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      await bindPlayerActor(worldId, {
        worldline_id: data.selectedWorldlineId,
        display_name: formString(form, "display_name"),
        current_scene_id: optionalFormString(form, "current_scene_id"),
        profile: {},
      });
      formElement.reset();
    }, activeActor === null ? "Player actor bound." : "Player actor updated.");
  }

  async function handleChoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    const shouldApply = submitter instanceof HTMLButtonElement && submitter.value === "apply";
    const input: PlayerChoiceCreateInput = {
      worldline_id: data.selectedWorldlineId,
      player_actor_id: formString(form, "player_actor_id"),
      choice_key: formString(form, "choice_key"),
      choice_kind: formString(form, "choice_kind") as PlayerChoiceCreateInput["choice_kind"],
      prompt: formString(form, "prompt"),
      selected_option: formString(form, "selected_option"),
      context: { source: "player_interaction_ui" },
      effects: {},
      apply: shouldApply,
    };
    await runAction(async () => {
      if (shouldApply) {
        await recordPlayerChoice(worldId, input);
        setPreview(null);
      } else {
        setPreview(await previewPlayerChoiceConsequences(worldId, input));
      }
    }, shouldApply ? "Player choice recorded." : "Choice consequence preview loaded.");
  }

  async function handleIntervention(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      await createIntervention(worldId, {
        worldline_id: data.selectedWorldlineId,
        player_actor_id: formString(form, "player_actor_id"),
        intervention_kind: formString(form, "intervention_kind") as "contact",
        target_agent_id: optionalFormString(form, "target_agent_id"),
        target_scene_id: optionalFormString(form, "target_scene_id"),
        prompt: formString(form, "prompt"),
        metadata: { source: "player_interaction_ui" },
      });
      formElement.reset();
    }, "Intervention recorded.");
  }

  return (
    <section className="management-section player-surface">
      {notice !== null ? (
        <p className="management-notice" data-tone={notice.tone} role={notice.tone === "error" ? "alert" : "status"}>
          {notice.message}
        </p>
      ) : null}

      <section className="management-panel player-summary" aria-labelledby="player-summary-title">
        <div>
          <h2 className="section-title" id="player-summary-title">
            Player interactions
          </h2>
          <p className="admin-section-copy">
            {data.selectedWorld.name} · {data.worldlines.length} worldline(s)
          </p>
        </div>
        <div className="player-metrics" aria-label="Player interaction counts">
          <span>{data.playerChoices.length} choices</span>
          <span>{data.interventions.length} interventions</span>
          <span>{data.notifications.filter((item) => item.status === "unread").length} unread</span>
        </div>
      </section>

      <div className="player-grid">
        <section className="management-panel" aria-labelledby="player-actor-title">
          <h2 className="section-title" id="player-actor-title">
            Player actor
          </h2>
          {activeActor === null ? (
            <p className="management-notice" data-tone="warning">
              No player actor is bound for this worldline.
            </p>
          ) : (
            <article className="resource-row">
              <div>
                <h3>{activeActor.display_name}</h3>
                <p>{sceneName(data, activeActor.current_scene_id)}</p>
              </div>
            </article>
          )}
          <form className="inline-form" onSubmit={handleBindActor}>
            <input
              className="text-input"
              name="display_name"
              placeholder="Player display name"
              defaultValue={activeActor?.display_name ?? ""}
              required
            />
            <select className="text-input" name="current_scene_id" defaultValue={activeActor?.current_scene_id ?? ""}>
              <option value="">No current scene</option>
              {data.scenes.map((scene) => (
                <option key={scene.id} value={scene.id}>
                  {scene.name}
                </option>
              ))}
            </select>
            <button className="primary-button" type="submit" disabled={isBusy}>
              {activeActor === null ? "Bind player actor" : "Update player actor"}
            </button>
          </form>
        </section>

        <section className="management-panel" aria-labelledby="route-feedback-title">
          <h2 className="section-title" id="route-feedback-title">
            Route feedback
          </h2>
          {latestRouteChoice === null ? (
            <p className="management-notice">No player choice has been recorded yet.</p>
          ) : (
            <article className="resource-row">
              <div>
                <h3>{latestRouteChoice.choice_key}</h3>
                <p>
                  {latestRouteChoice.choice_kind} · {latestRouteChoice.selected_option}
                </p>
              </div>
            </article>
          )}
          <ul className="compact-list">
            {routeDiagnostics.length === 0 ? (
              <li>Feedback contains only player-visible summaries.</li>
            ) : (
              routeDiagnostics.map((diagnostic) => <li key={diagnostic}>{diagnostic}</li>)
            )}
          </ul>
        </section>
      </div>

      <section className="management-panel" aria-labelledby="choice-title">
        <h2 className="section-title" id="choice-title">
          Choices
        </h2>
        <form className="player-form" onSubmit={handleChoice}>
          <ActorSelect actors={data.playerActors} disabled={isBusy} />
          <input className="text-input" name="choice_key" placeholder="choice-key" required />
          <select className="text-input" name="choice_kind" defaultValue="route">
            <option value="route">Route</option>
            <option value="dialogue">Dialogue</option>
            <option value="travel">Travel</option>
            <option value="contact">Contact</option>
            <option value="intervention">Intervention</option>
          </select>
          <textarea className="text-input" name="prompt" placeholder="Choice prompt" rows={3} required />
          <input className="text-input" name="selected_option" placeholder="Selected option" required />
          <div className="button-row">
            <button className="secondary-button" type="submit" value="preview" disabled={isBusy || activeActor === null}>
              Preview choice
            </button>
            <button className="primary-button" type="submit" value="apply" disabled={isBusy || activeActor === null}>
              Record choice
            </button>
          </div>
        </form>
        <RecordList
          emptyLabel="No player choices."
          items={data.playerChoices.map((choice) => ({
            id: choice.id,
            title: choice.choice_key,
            body: `${choice.choice_kind} · ${choice.selected_option}`,
            meta: dateLabel(choice.created_at),
          }))}
        />
      </section>

      <div className="player-grid">
        <section className="management-panel" aria-labelledby="journal-title">
          <h2 className="section-title" id="journal-title">
            Journal
          </h2>
          <RecordList
            emptyLabel="No journal entries."
            items={data.playerJournal.map((entry) => ({
              id: entry.id,
              title: entry.title,
              body: entry.body,
              meta: `${entry.entry_kind} · ${dateLabel(entry.created_at)}`,
            }))}
          />
        </section>

        <section className="management-panel" aria-labelledby="notifications-title">
          <h2 className="section-title" id="notifications-title">
            Notifications
          </h2>
          <RecordList
            emptyLabel="No notifications."
            items={data.notifications.map((notification) => ({
              id: notification.id,
              title: notification.title,
              body: notification.body,
              meta: `${notification.notification_kind} · ${notification.status}`,
            }))}
          />
        </section>
      </div>

      <section className="management-panel" aria-labelledby="intervention-title">
        <h2 className="section-title" id="intervention-title">
          Interventions
        </h2>
        <form className="player-form" onSubmit={handleIntervention}>
          <ActorSelect actors={data.playerActors} disabled={isBusy} />
          <select className="text-input" name="intervention_kind" defaultValue="contact">
            <option value="observe">Observe</option>
            <option value="reply">Reply</option>
            <option value="travel">Travel</option>
            <option value="contact">Contact</option>
            <option value="push_event">Push event</option>
          </select>
          <select className="text-input" name="target_agent_id" defaultValue="">
            <option value="">No target agent</option>
            {data.agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.display_name}
              </option>
            ))}
          </select>
          <select className="text-input" name="target_scene_id" defaultValue="">
            <option value="">No target scene</option>
            {data.scenes.map((scene) => (
              <option key={scene.id} value={scene.id}>
                {scene.name}
              </option>
            ))}
          </select>
          <textarea className="text-input" name="prompt" placeholder="Intervention prompt" rows={3} required />
          <button className="primary-button" type="submit" disabled={isBusy || activeActor === null}>
            Submit intervention
          </button>
        </form>
        <RecordList
          emptyLabel="No interventions."
          items={data.interventions.map((intervention) => ({
            id: intervention.id,
            title: intervention.intervention_kind,
            body: intervention.status,
            meta: dateLabel(intervention.created_at),
          }))}
        />
      </section>
    </section>
  );
}

function ActorSelect({
  actors,
  disabled,
}: {
  actors: PlayerInteractionData["playerActors"];
  disabled: boolean;
}) {
  return (
    <select className="text-input" name="player_actor_id" disabled={disabled || actors.length === 0} required>
      {actors.length === 0 ? <option value="">No player actor</option> : null}
      {actors.map((actor) => (
        <option key={actor.id} value={actor.id}>
          {actor.display_name}
        </option>
      ))}
    </select>
  );
}

function RecordList({
  emptyLabel,
  items,
}: {
  emptyLabel: string;
  items: { id: string; title: string; body: string; meta: string }[];
}) {
  if (items.length === 0) {
    return <p className="management-notice">{emptyLabel}</p>;
  }
  return (
    <div className="resource-list">
      {items.map((item) => (
        <article className="resource-row" key={item.id}>
          <div>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
            <p>{item.meta}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function safeDiagnostics(
  preview: ChoiceConsequencePreview | null,
  storedPreview: Record<string, unknown> | null,
): string[] {
  const rawDiagnostics = preview?.diagnostics ?? storedPreview?.diagnostics;
  if (!Array.isArray(rawDiagnostics)) {
    return [];
  }
  return rawDiagnostics
    .filter((item): item is string => typeof item === "string")
    .filter((item) => !containsForbiddenEvidence(item));
}

function containsForbiddenEvidence(value: string): boolean {
  return /storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret|\/var\/|\/tmp\//i.test(value);
}

function sceneName(data: PlayerInteractionData, sceneId: string | null): string {
  if (sceneId === null) {
    return "No current scene";
  }
  return data.scenes.find((scene) => scene.id === sceneId)?.name ?? "Unknown scene";
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
