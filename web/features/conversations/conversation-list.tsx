"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { createConversation } from "@/lib/worlds/client";
import type { ConversationListData } from "@/lib/worlds/server";
import type { ConversationPolicy, ConversationWriterConfig } from "@/lib/worlds/types";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type ConversationListProps = {
  worldId: string;
  data: ConversationListData;
};

export function ConversationList({ worldId, data }: ConversationListProps) {
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);

  async function handleCreateConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setIsBusy(true);
    setNotice(null);
    try {
      const session = await createConversation(worldId, {
        session_key: formString(form, "session_key"),
        title: formString(form, "title"),
        scope_type: formString(form, "scope_type") as "scene" | "world",
        mode: formString(form, "mode") as "manual_chain" | "auto_dialogue",
        scene_id: optionalFormString(form, "scene_id"),
        objective: formString(form, "objective"),
        opening_prompt: formString(form, "opening_prompt"),
        max_turns: Number(formString(form, "max_turns") || "12"),
        policy: policyFromForm(form),
        writer_config: writerConfigFromForm(form),
      });
      formElement.reset();
      window.location.assign(`/worlds/${worldId}/conversations/${session.id}`);
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}
      {data.canManageSelectedWorld ? (
        <section className="management-panel" aria-labelledby="create-conversation-title">
          <h2 className="section-title" id="create-conversation-title">
            Create conversation
          </h2>
          <form className="management-form" onSubmit={handleCreateConversation}>
            <input className="text-input" name="session_key" placeholder="session-key" />
            <input className="text-input" name="title" placeholder="Conversation title" />
            <select className="text-input" name="scope_type" defaultValue="world">
              <option value="world">world</option>
              <option value="scene">scene</option>
            </select>
            <select className="text-input" name="scene_id" defaultValue="">
              <option value="">No scene</option>
              {data.scenes.map((scene) => (
                <option key={scene.id} value={scene.id}>
                  {scene.name}
                </option>
              ))}
            </select>
            <select className="text-input" name="mode" defaultValue="manual_chain">
              <option value="manual_chain">manual_chain</option>
              <option value="auto_dialogue">auto_dialogue</option>
            </select>
            <input className="text-input" name="max_turns" placeholder="12" />
            <input className="text-input" name="objective" placeholder="Objective" />
            <input className="text-input" name="opening_prompt" placeholder="Opening prompt" />
            <input
              className="text-input"
              name="writer_provider_profile_id"
              placeholder="Writer provider profile id (optional)"
            />
            <label className="checkbox-label">
              <input name="writer_auto_generate_on_complete" type="checkbox" value="true" />
              Auto generate on complete
            </label>
            <label className="checkbox-label">
              <input
                defaultChecked
                name="writer_generate_summary"
                type="checkbox"
                value="true"
              />
              Generate summary
            </label>
            <label className="checkbox-label">
              <input
                defaultChecked
                name="writer_generate_chapter"
                type="checkbox"
                value="true"
              />
              Generate chapter
            </label>
            <select
              aria-label="Error policy"
              className="text-input"
              name="error_policy"
              defaultValue="retry_once_then_fail"
            >
              <option value="retry_once_then_fail">retry_once_then_fail</option>
              <option value="retry_once_then_skip">retry_once_then_skip</option>
              <option value="fail_session">fail_session</option>
              <option value="skip_turn">skip_turn</option>
            </select>
            <input
              aria-label="Max consecutive failed turns"
              className="text-input"
              name="max_consecutive_failed_turns"
              defaultValue="2"
            />
            <input
              aria-label="Loop guard window"
              className="text-input"
              name="loop_guard_window"
              defaultValue="4"
            />
            <input
              aria-label="Repeat output threshold"
              className="text-input"
              name="repeat_output_threshold"
              defaultValue="3"
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create conversation
            </button>
          </form>
        </section>
      ) : null}

      <section className="management-panel" aria-labelledby="conversations-title">
        <h2 className="section-title" id="conversations-title">
          Conversations
        </h2>
        <div className="resource-list">
          {data.conversations.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No conversations yet</h3>
                <p>Create a manual chain or auto dialogue session.</p>
              </div>
            </article>
          ) : (
            data.conversations.map((conversation) => (
              <article className="resource-row" key={conversation.id}>
                <div>
                  <h3>{conversation.title}</h3>
                  <p>
                    {conversation.session_key} - {conversation.mode} - {conversation.status}
                  </p>
                  {conversation.terminal_reason !== null ? (
                    <p>Terminal reason: {conversation.terminal_reason}</p>
                  ) : null}
                  <p>
                    {conversation.scope_type}
                    {conversation.scene_id !== null ? ` scene ${conversation.scene_id}` : ""}
                  </p>
                </div>
                <div className="button-row">
                  <Link
                    className="secondary-button"
                    href={`/worlds/${worldId}/conversations/${conversation.id}`}
                  >
                    Open transcript
                  </Link>
                </div>
              </article>
            ))
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
    provider_profile_id: optionalFormString(form, "writer_provider_profile_id"),
    auto_generate_on_complete: form.get("writer_auto_generate_on_complete") === "true",
    generate_summary: form.get("writer_generate_summary") === "true",
    generate_chapter: form.get("writer_generate_chapter") === "true",
  };
}
