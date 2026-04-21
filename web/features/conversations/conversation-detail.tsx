"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  advanceConversation,
  pauseConversation,
  replaceConversationParticipants,
  resumeConversation,
  seedConversation,
  startConversation,
} from "@/lib/worlds/client";
import type { ConversationDetailData } from "@/lib/worlds/server";
import { formString, messageForError } from "@/features/workspace/form-utils";

type ConversationDetailProps = {
  worldId: string;
  conversationId: string;
  data: ConversationDetailData;
};

export function ConversationDetail({ worldId, conversationId, data }: ConversationDetailProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
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
          </div>
        ) : null}
      </section>

      <div className="management-columns">
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
