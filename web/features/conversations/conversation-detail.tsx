"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  advanceConversation,
  generateConversationNarrativeArtifacts,
  pauseConversation,
  replaceConversationParticipants,
  resumeConversation,
  seedConversation,
  startConversation,
  stopConversation,
  updateConversation,
} from "@/lib/worlds/client";
import type { ConversationDetailData } from "@/lib/worlds/server";
import type {
  ConversationNarrativeArtifactSet,
  ConversationPolicy,
  ConversationWriterConfig,
  NarrativeArtifact,
  RuntimeDiagnostic,
} from "@/lib/worlds/types";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type ConversationDetailProps = {
  worldId: string;
  conversationId: string;
  data: ConversationDetailData;
};

export function ConversationDetail({ worldId, conversationId, data }: ConversationDetailProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [narrativeArtifacts, setNarrativeArtifacts] = useState(data.narrativeArtifacts);
  const conversation = data.conversation;
  const participantIds = useMemo(
    () => new Set(data.participants.map((participant) => participant.agent_id)),
    [data.participants],
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

  if (conversation === null) {
    return (
      <section className="management-section">
        <p className="management-notice">{notice ?? "Conversation not found."}</p>
      </section>
    );
  }

  async function handleParticipants(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const agentIds = form
      .getAll("agent_id")
      .filter((value): value is string => typeof value === "string" && value !== "");
    await runAction(
      () =>
        replaceConversationParticipants(
          worldId,
          conversationId,
          agentIds.map((agentId, index) => ({
            agent_id: agentId,
            turn_order: index,
            is_enabled: true,
          })),
        ),
      "Participants saved.",
    );
  }

  async function handleSeed(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await seedConversation(worldId, conversationId, {
          input_text: formString(form, "input_text"),
        });
        formElement.reset();
      },
      "Conversation seeded.",
    );
  }

  async function handlePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateConversation(worldId, conversationId, {
          policy: policyFromForm(form),
        }),
      "Conversation policy updated.",
    );
  }

  async function handleWriterConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateConversation(worldId, conversationId, {
          writer_config: writerConfigFromForm(form),
        }),
      "Writer config updated.",
    );
  }

  async function handleGenerateNarrative(artifactSet: ConversationNarrativeArtifactSet) {
    await runAction(
      async () => {
        const artifacts = await generateConversationNarrativeArtifacts(
          worldId,
          conversationId,
          artifactSet,
          conversation?.writer_config.provider_profile_id ?? null,
        );
        setNarrativeArtifacts(artifacts);
      },
      "Conversation narrative generated.",
    );
  }

  const canManage = data.canManageSelectedWorld;

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}
      <section className="management-panel" aria-labelledby="conversation-title">
        <h2 className="section-title" id="conversation-title">
          {conversation.title}
        </h2>
        <p>
          {conversation.session_key} - {conversation.mode} - {conversation.status}
        </p>
        {conversation.terminal_reason !== null ? (
          <p>Terminal reason: {conversation.terminal_reason}</p>
        ) : null}
        <p>{conversation.objective || "No objective configured."}</p>
        {canManage ? (
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                runAction(() => advanceConversation(worldId, conversationId), "Turn advanced.")
              }
            >
              Advance one turn
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                runAction(() => startConversation(worldId, conversationId), "Conversation started.")
              }
            >
              Start auto dialogue
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                runAction(() => pauseConversation(worldId, conversationId), "Conversation paused.")
              }
            >
              Pause
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                runAction(() => resumeConversation(worldId, conversationId), "Conversation resumed.")
              }
            >
              Resume
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                runAction(() => stopConversation(worldId, conversationId), "Conversation stopped.")
              }
            >
              Stop
            </button>
          </div>
        ) : null}
      </section>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="policy-title">
          <h2 className="section-title" id="policy-title">
            Conversation policy
          </h2>
          {canManage ? (
            <form className="inline-form" onSubmit={handlePolicy}>
              <select
                aria-label="Conversation error policy"
                className="text-input"
                name="error_policy"
                defaultValue={conversation.policy.error_policy}
              >
                <option value="retry_once_then_fail">retry_once_then_fail</option>
                <option value="retry_once_then_skip">retry_once_then_skip</option>
                <option value="fail_session">fail_session</option>
                <option value="skip_turn">skip_turn</option>
              </select>
              <input
                aria-label="Conversation max consecutive failed turns"
                className="text-input"
                name="max_consecutive_failed_turns"
                defaultValue={String(conversation.policy.max_consecutive_failed_turns)}
              />
              <input
                aria-label="Conversation loop guard window"
                className="text-input"
                name="loop_guard_window"
                defaultValue={String(conversation.policy.loop_guard_window)}
              />
              <input
                aria-label="Conversation repeat output threshold"
                className="text-input"
                name="repeat_output_threshold"
                defaultValue={String(conversation.policy.repeat_output_threshold)}
              />
              <button className="primary-button" type="submit" disabled={isBusy}>
                Save policy
              </button>
            </form>
          ) : (
            <p>
              {conversation.policy.error_policy} / failures{" "}
              {conversation.policy.max_consecutive_failed_turns} / loop{" "}
              {conversation.policy.repeat_output_threshold} in {conversation.policy.loop_guard_window}
            </p>
          )}
        </section>

        <section className="management-panel" aria-labelledby="participants-title">
          <h2 className="section-title" id="participants-title">
            Participants
          </h2>
          {canManage ? (
            <form className="inline-form" onSubmit={handleParticipants}>
              {data.agents.map((agent) => (
                <label className="checkbox-label" key={agent.id}>
                  <input
                    name="agent_id"
                    type="checkbox"
                    value={agent.id}
                    defaultChecked={participantIds.has(agent.id)}
                  />
                  {agent.display_name} ({agent.agent_key})
                </label>
              ))}
              <button className="primary-button" type="submit" disabled={isBusy}>
                Save participants
              </button>
            </form>
          ) : null}
          <div className="resource-list">
            {data.participants.map((participant) => {
              const agent = data.agents.find((item) => item.id === participant.agent_id);
              return (
                <article className="resource-row" key={participant.id}>
                  <div>
                    <h3>{agent?.display_name ?? participant.agent_id}</h3>
                    <p>Turn order {participant.turn_order}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="management-panel" aria-labelledby="seed-title">
          <h2 className="section-title" id="seed-title">
            Operator seed
          </h2>
          {canManage ? (
            <form className="inline-form" onSubmit={handleSeed}>
              <textarea className="text-input" name="input_text" rows={6} placeholder="Seed text" />
              <button className="primary-button" type="submit" disabled={isBusy}>
                Seed conversation
              </button>
            </form>
          ) : (
            <p>Read-only transcript access.</p>
          )}
        </section>
      </div>

      <div className="management-columns">
        <section className="management-panel" aria-labelledby="writer-config-title">
          <h2 className="section-title" id="writer-config-title">
            Writer config
          </h2>
          {canManage ? (
            <form className="inline-form" onSubmit={handleWriterConfig}>
              <input
                aria-label="Writer provider profile id"
                className="text-input"
                name="provider_profile_id"
                defaultValue={conversation.writer_config.provider_profile_id ?? ""}
                placeholder="Provider profile id (optional)"
              />
              <label className="checkbox-label">
                <input
                  defaultChecked={conversation.writer_config.auto_generate_on_complete}
                  name="auto_generate_on_complete"
                  type="checkbox"
                  value="true"
                />
                Auto generate on complete
              </label>
              <label className="checkbox-label">
                <input
                  defaultChecked={conversation.writer_config.generate_summary}
                  name="generate_summary"
                  type="checkbox"
                  value="true"
                />
                Generate summary
              </label>
              <label className="checkbox-label">
                <input
                  defaultChecked={conversation.writer_config.generate_chapter}
                  name="generate_chapter"
                  type="checkbox"
                  value="true"
                />
                Generate chapter
              </label>
              <button className="primary-button" type="submit" disabled={isBusy}>
                Save writer config
              </button>
            </form>
          ) : (
            <p>
              auto={String(conversation.writer_config.auto_generate_on_complete)} / summary=
              {String(conversation.writer_config.generate_summary)} / chapter=
              {String(conversation.writer_config.generate_chapter)}
            </p>
          )}
        </section>

        <section className="management-panel" aria-labelledby="conversation-narrative-title">
          <h2 className="section-title" id="conversation-narrative-title">
            Conversation narrative
          </h2>
          {canManage ? (
            <div className="button-row">
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => handleGenerateNarrative("summary_and_chapter")}
              >
                Generate summary + chapter
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => handleGenerateNarrative("summary_only")}
              >
                Generate summary
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={isBusy}
                onClick={() => handleGenerateNarrative("chapter_only")}
              >
                Generate chapter
              </button>
            </div>
          ) : null}
          <NarrativeArtifactList artifacts={narrativeArtifacts} />
        </section>
      </div>

      {canManage ? (
        <section className="management-panel" aria-labelledby="conversation-diagnostics-title">
          <h2 className="section-title" id="conversation-diagnostics-title">
            Conversation diagnostics
          </h2>
          <DiagnosticList diagnostics={data.diagnostics} />
        </section>
      ) : null}

      <section className="management-panel" aria-labelledby="transcript-title">
        <h2 className="section-title" id="transcript-title">
          Transcript
        </h2>
        <div className="resource-list">
          {data.turns.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No turns yet</h3>
                <p>Seed or advance the conversation to begin.</p>
              </div>
            </article>
          ) : (
            data.turns.map((turn) => {
              const agent = data.agents.find((item) => item.id === turn.speaker_agent_id);
              return (
                <article className="resource-row" key={turn.id}>
                  <div>
                  <h3>
                      #{turn.turn_index} {agent?.display_name ?? turn.speaker_kind}
                    </h3>
                    <p>Status: {turn.status}</p>
                    <p>{turn.output_text ?? turn.input_text}</p>
                    {turn.error_text !== null ? <p>{turn.error_text}</p> : null}
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

function policyFromForm(form: FormData): ConversationPolicy {
  return {
    error_policy: formString(form, "error_policy") as ConversationPolicy["error_policy"],
    max_consecutive_failed_turns: Number(formString(form, "max_consecutive_failed_turns")),
    loop_guard_window: Number(formString(form, "loop_guard_window")),
    repeat_output_threshold: Number(formString(form, "repeat_output_threshold")),
  };
}

function writerConfigFromForm(form: FormData): ConversationWriterConfig {
  return {
    provider_profile_id: optionalFormString(form, "provider_profile_id"),
    auto_generate_on_complete: form.get("auto_generate_on_complete") === "true",
    generate_summary: form.get("generate_summary") === "true",
    generate_chapter: form.get("generate_chapter") === "true",
  };
}

function DiagnosticList({ diagnostics }: { diagnostics: RuntimeDiagnostic[] }) {
  if (diagnostics.length === 0) {
    return <p>No diagnostics recorded.</p>;
  }

  return (
    <div className="resource-list">
      {diagnostics.map((diagnostic) => (
        <article className="resource-row" key={diagnostic.id}>
          <div>
            <h3>
              {diagnostic.severity} - {diagnostic.event_type}
            </h3>
            <p>{diagnostic.message}</p>
            <p>{diagnostic.occurred_at}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function NarrativeArtifactList({ artifacts }: { artifacts: NarrativeArtifact[] }) {
  if (artifacts.length === 0) {
    return <p>No conversation narrative artifacts yet.</p>;
  }

  return (
    <div className="resource-list">
      {artifacts.map((artifact) => (
        <article className="resource-row" key={artifact.id}>
          <div>
            <h3>{artifact.title}</h3>
            <p>{artifact.artifact_kind}</p>
            <p>{artifact.content}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
