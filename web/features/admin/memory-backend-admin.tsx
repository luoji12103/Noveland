"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createMemoryBackendProfile,
  deleteMemoryBackendProfile,
  runMemoryBackendProfileEvalSmoke,
  updateMemoryBackendProfile,
} from "@/lib/worlds/client";
import type { MemoryBackendAdminData } from "@/lib/worlds/server";
import type { MemoryEvalResult } from "@/lib/worlds/types";
import { formString, jsonObject, messageForError } from "@/features/workspace/form-utils";

type MemoryBackendAdminProps = {
  data: MemoryBackendAdminData;
};

export function MemoryBackendAdmin({ data }: MemoryBackendAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [evalResultsByProfileId, setEvalResultsByProfileId] = useState<Record<string, MemoryEvalResult>>(
    {},
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

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createMemoryBackendProfile({
          profile_key: formString(form, "profile_key"),
          name: formString(form, "name"),
          backend_kind: formString(form, "backend_kind") as "mem0_oss" | "local_pgvector",
          vector_store_config: jsonObject(formString(form, "vector_store_config")),
          llm_config: jsonObject(formString(form, "llm_config")),
          embedder_config: jsonObject(formString(form, "embedder_config")),
          reranker_config: jsonObject(formString(form, "reranker_config")),
          secret_refs: jsonObject(formString(form, "secret_refs")) as Record<string, string>,
          is_enabled: form.get("is_enabled") === "on",
        });
        formElement.reset();
      },
      "Memory backend profile created.",
    );
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>, profileId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateMemoryBackendProfile(profileId, {
          name: formString(form, "name"),
          vector_store_config: jsonObject(formString(form, "vector_store_config")),
          llm_config: jsonObject(formString(form, "llm_config")),
          embedder_config: jsonObject(formString(form, "embedder_config")),
          reranker_config: jsonObject(formString(form, "reranker_config")),
          secret_refs: jsonObject(formString(form, "secret_refs")) as Record<string, string>,
          is_enabled: form.get("is_enabled") === "on",
        }),
      "Memory backend profile saved.",
    );
  }

  async function handleEval(profileId: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      const result = await runMemoryBackendProfileEvalSmoke(profileId);
      setEvalResultsByProfileId((current) => ({ ...current, [profileId]: result }));
      setNotice("Memory backend eval smoke completed.");
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="management-panel" aria-labelledby="create-memory-profile-title">
        <h2 className="section-title" id="create-memory-profile-title">
          Create memory backend profile
        </h2>
        <form className="management-form" onSubmit={handleCreate}>
          <input className="text-input" name="profile_key" placeholder="profile-key" />
          <input className="text-input" name="name" placeholder="Profile name" />
          <select className="text-input" name="backend_kind" defaultValue="mem0_oss">
            <option value="mem0_oss">mem0_oss</option>
            <option value="local_pgvector">local_pgvector</option>
          </select>
          <textarea className="text-input" name="vector_store_config" rows={3} defaultValue="{}" />
          <textarea className="text-input" name="llm_config" rows={3} defaultValue="{}" />
          <textarea className="text-input" name="embedder_config" rows={3} defaultValue="{}" />
          <textarea className="text-input" name="reranker_config" rows={3} defaultValue="{}" />
          <textarea className="text-input" name="secret_refs" rows={3} defaultValue="{}" />
          <label className="checkbox-label">
            <input defaultChecked name="is_enabled" type="checkbox" />
            Enabled
          </label>
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create memory backend profile
          </button>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="memory-profiles-title">
        <h2 className="section-title" id="memory-profiles-title">
          Memory backend profiles
        </h2>
        <div className="resource-list">
          {data.profiles.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No memory backend profiles yet</h3>
                <p>Configure Mem0 OSS or local pgvector profiles here. Secrets stay in env refs.</p>
              </div>
            </article>
          ) : (
            data.profiles.map((profile) => (
              <article className="resource-row" key={profile.id}>
                <div>
                  <h3>{profile.name}</h3>
                  <p>
                    {profile.profile_key} - {profile.backend_kind} -{" "}
                    {profile.is_enabled ? "Enabled" : "Disabled"}
                  </p>
                  <p>
                    Health: {data.profileHealth[profile.id]?.status ?? "unknown"} / write logs{" "}
                    {data.profileLogs[profile.id]?.write_logs.length ?? 0} / retrieval logs{" "}
                    {data.profileLogs[profile.id]?.retrieval_logs.length ?? 0}
                  </p>
                  <form className="inline-form" onSubmit={(event) => handleUpdate(event, profile.id)}>
                    <input className="text-input" name="name" defaultValue={profile.name} />
                    <textarea
                      className="text-input"
                      name="vector_store_config"
                      rows={3}
                      defaultValue={JSON.stringify(profile.vector_store_config, null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="llm_config"
                      rows={3}
                      defaultValue={JSON.stringify(profile.llm_config, null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="embedder_config"
                      rows={3}
                      defaultValue={JSON.stringify(profile.embedder_config, null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="reranker_config"
                      rows={3}
                      defaultValue={JSON.stringify(profile.reranker_config, null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="secret_refs"
                      rows={3}
                      defaultValue={JSON.stringify(profile.secret_refs, null, 2)}
                    />
                    <label className="checkbox-label">
                      <input defaultChecked={profile.is_enabled} name="is_enabled" type="checkbox" />
                      Enabled
                    </label>
                    <div className="button-row">
                      <button className="primary-button" type="submit" disabled={isBusy}>
                        Save profile
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isBusy}
                        onClick={() => void handleEval(profile.id)}
                      >
                        Run eval smoke
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isBusy}
                        onClick={() =>
                          runAction(
                            () => deleteMemoryBackendProfile(profile.id),
                            "Memory backend profile deleted.",
                          )
                        }
                      >
                        Delete profile
                      </button>
                    </div>
                  </form>
                  <p>
                    Last eval:{" "}
                    {evalResultsByProfileId[profile.id] === undefined
                      ? "not run in this session"
                      : `${evalResultsByProfileId[profile.id].hit_case_count}/${evalResultsByProfileId[profile.id].case_count} hits, avg latency ${evalResultsByProfileId[profile.id].average_latency_ms ?? 0}ms`}
                  </p>
                  <pre>
                    {JSON.stringify(
                      {
                        health: data.profileHealth[profile.id] ?? null,
                        logs: data.profileLogs[profile.id] ?? { write_logs: [], retrieval_logs: [] },
                      },
                      null,
                      2,
                    )}
                  </pre>
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </section>
  );
}
