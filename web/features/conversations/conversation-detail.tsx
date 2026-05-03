"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import {
  createConversationLiveSocket,
  mergeById,
  nextRequestId,
  subscribeToEventStream,
} from "@/lib/realtime";
import type {
  ConversationLiveMessage,
  ConversationStreamEnvelope,
} from "@/lib/realtime";
import type { ConversationDetailData } from "@/lib/worlds/server";
import type {
  ConversationMemoryConfig,
  ConversationNarrativeArtifactSet,
  ConversationPolicy,
  ConversationSession,
  ConversationTurn,
  ConversationWriterConfig,
  NarrativeArtifact,
  RuntimeDiagnostic,
} from "@/lib/worlds/types";
import {
  formString,
  jsonObject,
  messageForError,
  optionalFormString,
} from "@/features/workspace/form-utils";

type ConversationDetailProps = {
  worldId: string;
  conversationId: string;
  data: ConversationDetailData;
};

export function ConversationDetail({ worldId, conversationId, data }: ConversationDetailProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [conversationState, setConversationState] = useState(data.conversation);
  const [participants, setParticipants] = useState(data.participants);
  const [turns, setTurns] = useState(data.turns);
  const [diagnostics, setDiagnostics] = useState(data.diagnostics);
  const [narrativeArtifacts, setNarrativeArtifacts] = useState(data.narrativeArtifacts);
  const [liveReady, setLiveReady] = useState(false);
  const conversation = conversationState;
  const socketRef = useRef<WebSocket | null>(null);

  const handleLiveMessage = useCallback((message: ConversationLiveMessage) => {
    if (message.type === "error") {
      const liveMessage = message.payload.message;
      setNotice(typeof liveMessage === "string" ? liveMessage : "Live conversation command failed.");
      setIsBusy(false);
      return;
    }
    if (message.type === "ack") {
      setNotice("Conversation control command accepted.");
      setIsBusy(false);
      return;
    }
    if (message.type === "session_snapshot") {
      const session = message.payload.session as ConversationSession | undefined;
      const nextParticipants = message.payload.participants as typeof participants | undefined;
      const nextTurns = message.payload.turns as ConversationTurn[] | undefined;
      const nextDiagnostics = message.payload.diagnostics as RuntimeDiagnostic[] | undefined;
      if (session !== undefined) {
        setConversationState(session);
      }
      if (nextParticipants !== undefined) {
        setParticipants(nextParticipants);
      }
      if (nextTurns !== undefined) {
        setTurns(nextTurns);
      }
      if (nextDiagnostics !== undefined) {
        setDiagnostics(nextDiagnostics);
      }
      return;
    }
    if (message.type === "turn_appended") {
      const turn = message.payload as ConversationTurn;
      setTurns((current) => mergeTurns(current, [turn]));
      return;
    }
    if (message.type === "status_changed") {
      setConversationState(message.payload as ConversationSession);
    }
  }, []);

  useEffect(() => {
    setConversationState(data.conversation);
    setParticipants(data.participants);
    setTurns(data.turns);
    setDiagnostics(data.diagnostics);
    setNarrativeArtifacts(data.narrativeArtifacts);
  }, [data.conversation, data.diagnostics, data.narrativeArtifacts, data.participants, data.turns]);

  useEffect(() => {
    return subscribeToEventStream<ConversationStreamEnvelope["payload"]>(
      `/api/worlds/${worldId}/conversations/${conversationId}/stream`,
      (envelope) => {
        if (envelope.payload.session !== undefined) {
          setConversationState(envelope.payload.session);
        }
        if (envelope.payload.turns.length > 0) {
          setTurns((current) => mergeTurns(current, envelope.payload.turns));
        }
        if (envelope.payload.diagnostics.length > 0) {
          setDiagnostics((current) => mergeDiagnostics(current, envelope.payload.diagnostics));
        }
      },
    );
  }, [conversationId, worldId]);

  useEffect(() => {
    if (!data.canManageSelectedWorld) {
      return;
    }
    const socket = createConversationLiveSocket(worldId, conversationId, {
      onOpen: () => setLiveReady(true),
      onClose: () => setLiveReady(false),
      onError: () => setLiveReady(false),
      onMessage: handleLiveMessage,
    });
    socketRef.current = socket;
    return () => {
      socket.close();
      socketRef.current = null;
      setLiveReady(false);
    };
  }, [conversationId, data.canManageSelectedWorld, handleLiveMessage, worldId]);

  const participantIds = useMemo(
    () => new Set(participants.map((participant) => participant.agent_id)),
    [participants],
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

  function sendLiveCommand(
    command: "advance" | "start" | "pause" | "resume" | "seed",
    payload: Record<string, unknown> = {},
  ) {
    if (socketRef.current === null || socketRef.current.readyState !== WebSocket.OPEN) {
      throw new Error("Conversation live control is not connected.");
    }
    setIsBusy(true);
    setNotice(null);
    socketRef.current.send(
      JSON.stringify({
        command,
        request_id: nextRequestId(),
        payload,
      }),
    );
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
    const inputText = formString(form, "input_text");
    if (liveReady) {
      sendLiveCommand("seed", { input_text: inputText });
      formElement.reset();
      return;
    }
    await runAction(async () => {
      const turn = await seedConversation(worldId, conversationId, {
        input_text: inputText,
      });
      setTurns((current) => mergeTurns(current, [turn]));
      formElement.reset();
    }, "Conversation seeded.");
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

  async function handleMemoryConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateConversation(worldId, conversationId, {
          memory_config: memoryConfigFromForm(form),
        }),
      "Memory config updated.",
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
                liveReady
                  ? sendLiveCommand("advance")
                  : runAction(async () => {
                      const result = await advanceConversation(worldId, conversationId);
                      setConversationState(result.session);
                      setTurns((current) => mergeTurns(current, [result.turn]));
                    }, "Turn advanced.")
              }
            >
              Advance one turn
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                liveReady
                  ? sendLiveCommand("start")
                  : runAction(async () => {
                      setConversationState(await startConversation(worldId, conversationId));
                    }, "Conversation started.")
              }
            >
              Start auto dialogue
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                liveReady
                  ? sendLiveCommand("pause")
                  : runAction(async () => {
                      setConversationState(await pauseConversation(worldId, conversationId));
                    }, "Conversation paused.")
              }
            >
              Pause
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                liveReady
                  ? sendLiveCommand("resume")
                  : runAction(async () => {
                      setConversationState(await resumeConversation(worldId, conversationId));
                    }, "Conversation resumed.")
              }
            >
              Resume
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={isBusy}
              onClick={() =>
                runAction(async () => {
                  setConversationState(await stopConversation(worldId, conversationId));
                }, "Conversation stopped.")
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
            {participants.map((participant) => {
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
        <section className="management-panel" aria-labelledby="memory-config-title">
          <h2 className="section-title" id="memory-config-title">
            Memory config
          </h2>
          {canManage ? (
            <form className="inline-form" onSubmit={handleMemoryConfig}>
              <label className="checkbox-label">
                <input
                  defaultChecked={conversation.memory_config.write_turn_memory}
                  name="write_turn_memory"
                  type="checkbox"
                  value="true"
                />
                Write turn memory
              </label>
              <label className="checkbox-label">
                <input
                  defaultChecked={conversation.memory_config.retrieve_memory}
                  name="retrieve_memory"
                  type="checkbox"
                  value="true"
                />
                Retrieve memory
              </label>
              <input
                aria-label="Conversation memory max context items"
                className="text-input"
                name="max_context_items"
                defaultValue={String(conversation.memory_config.max_context_items)}
              />
              <input
                aria-label="Conversation memory query window"
                className="text-input"
                name="query_window"
                defaultValue={String(conversation.memory_config.query_window)}
              />
              <button className="primary-button" type="submit" disabled={isBusy}>
                Save memory config
              </button>
            </form>
          ) : (
            <p>
              write={String(conversation.memory_config.write_turn_memory)} / retrieve=
              {String(conversation.memory_config.retrieve_memory)} / max=
              {conversation.memory_config.max_context_items} / window=
              {conversation.memory_config.query_window}
            </p>
          )}
        </section>

        <section className="management-panel" aria-labelledby="writer-config-title">
          <h2 className="section-title" id="writer-config-title">
            Writer config
          </h2>
          {canManage ? (
            <form className="inline-form" onSubmit={handleWriterConfig}>
              <select
                aria-label="Writer plugin"
                className="text-input"
                name="writer_plugin_identifier"
                defaultValue={conversation.writer_config.writer_plugin_identifier}
              >
                {data.narrativeWriterPlugins.map((plugin) => (
                  <option key={plugin.identifier} value={plugin.identifier}>
                    {plugin.identifier}
                  </option>
                ))}
              </select>
              <input
                aria-label="Writer provider profile id"
                className="text-input"
                name="provider_profile_id"
                defaultValue={conversation.writer_config.provider_profile_id ?? ""}
                placeholder="Provider profile id (optional)"
              />
              <textarea
                aria-label="Writer plugin config"
                className="text-input"
                name="writer_plugin_config"
                rows={3}
                defaultValue={JSON.stringify(conversation.writer_config.writer_plugin_config, null, 2)}
                placeholder="{}"
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
              plugin={conversation.writer_config.writer_plugin_identifier} / auto=
              {String(conversation.writer_config.auto_generate_on_complete)} / summary=
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
          {data.diagnosticsSummary !== null ? (
            <div className="status-grid">
              <article>
                <p className="metric-label">Summary</p>
                <p>{data.diagnosticsSummary.operator_message}</p>
              </article>
              <article>
                <p className="metric-label">Last turn</p>
                <p>{data.diagnosticsSummary.last_turn_status ?? "none"}</p>
              </article>
              <article>
                <p className="metric-label">Provider issues</p>
                <p>{data.diagnosticsSummary.provider_diagnostic_count}</p>
              </article>
              <article>
                <p className="metric-label">Memory issues</p>
                <p>{data.diagnosticsSummary.memory_diagnostic_count}</p>
              </article>
            </div>
          ) : null}
          <DiagnosticList diagnostics={diagnostics} />
        </section>
      ) : null}

      <section className="management-panel" aria-labelledby="transcript-title">
        <h2 className="section-title" id="transcript-title">
          Transcript
        </h2>
        <div className="resource-list">
          {turns.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No turns yet</h3>
                <p>Seed or advance the conversation to begin.</p>
              </div>
            </article>
          ) : (
            turns.map((turn) => {
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

function mergeTurns(current: ConversationTurn[], incoming: ConversationTurn[]): ConversationTurn[] {
  return mergeById(current, incoming).sort((left, right) => left.turn_index - right.turn_index);
}

function mergeDiagnostics(
  current: RuntimeDiagnostic[],
  incoming: RuntimeDiagnostic[],
): RuntimeDiagnostic[] {
  return mergeById(current, incoming).sort((left, right) =>
    right.occurred_at.localeCompare(left.occurred_at),
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
    writer_plugin_identifier: formString(form, "writer_plugin_identifier"),
    writer_plugin_config: jsonObject(formString(form, "writer_plugin_config")),
    auto_generate_on_complete: form.get("auto_generate_on_complete") === "true",
    generate_summary: form.get("generate_summary") === "true",
    generate_chapter: form.get("generate_chapter") === "true",
  };
}

function memoryConfigFromForm(form: FormData): ConversationMemoryConfig {
  return {
    write_turn_memory: form.get("write_turn_memory") === "true",
    retrieve_memory: form.get("retrieve_memory") === "true",
    max_context_items: Number(formString(form, "max_context_items")),
    query_window: Number(formString(form, "query_window")),
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
