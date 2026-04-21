"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createConversation } from "@/lib/worlds/client";
import type { ConversationListData } from "@/lib/worlds/server";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type ConversationListProps = {
  worldId: string;
  data: ConversationListData;
};

export function ConversationList({ worldId, data }: ConversationListProps) {
  const router = useRouter();
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
      });
      formElement.reset();
      router.push(`/worlds/${worldId}/conversations/${session.id}`);
      router.refresh();
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
