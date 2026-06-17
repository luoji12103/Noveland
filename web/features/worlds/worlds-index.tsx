"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { createWorld } from "@/lib/worlds/client";
import type { World } from "@/lib/worlds/types";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type WorldsIndexProps = {
  worlds: World[];
  canCreateWorld: boolean;
};

export function WorldsIndex({ worlds, canCreateWorld }: WorldsIndexProps) {
  const [notice, setNotice] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function handleCreateWorld(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const slug = formString(form, "slug");
    const name = formString(form, "name");
    if (slug === "" || name === "") {
      setNotice("World slug and name are required.");
      return;
    }
    setIsBusy(true);
    setNotice(null);
    try {
      const world = await createWorld({
        slug,
        name,
        description: optionalFormString(form, "description"),
      });
      formElement.reset();
      window.location.assign(`/worlds/${encodeURIComponent(world.id)}`);
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      {canCreateWorld ? (
        <section className="management-panel" aria-labelledby="create-world-title">
          <h2 className="section-title" id="create-world-title">
            Create world
          </h2>
          <form className="management-form" onSubmit={handleCreateWorld}>
            <input className="text-input" name="slug" placeholder="world-slug" />
            <input className="text-input" name="name" placeholder="World name" />
            <input className="text-input" name="description" placeholder="Description" />
            <button className="primary-button" type="submit" disabled={isBusy}>
              Create world
            </button>
          </form>
        </section>
      ) : null}

      <section className="management-panel" aria-labelledby="worlds-title">
        <h2 className="section-title" id="worlds-title">
          Worlds
        </h2>
        <div className="resource-list">
          {worlds.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No worlds yet</h3>
                <p>Create a world to start building scenes, agents, and conversations.</p>
              </div>
            </article>
          ) : (
            worlds.map((world) => (
              <article className="resource-row" key={world.id}>
                <div>
                  <h3>{world.name}</h3>
                  <p>
                    {world.slug} - {world.is_active ? "Active" : "Inactive"}
                  </p>
                  <p>{world.description ?? "No description."}</p>
                </div>
                <div className="button-row">
                  <Link className="secondary-button" href={`/worlds/${encodeURIComponent(world.id)}`}>
                    Open workspace
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
