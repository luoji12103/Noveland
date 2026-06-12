"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createMemoryBackendProfile,
  deleteMemoryBackendProfile,
  retryMemoryWriteJob,
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
          vector_store_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "vector_store_config"))),
          llm_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "llm_config"))),
          embedder_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "embedder_config"))),
          reranker_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "reranker_config"))),
          secret_refs: sanitizeMemorySecretRefsForDisplay(
            jsonObject(formString(form, "secret_refs")) as Record<string, string>,
          ),
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
          vector_store_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "vector_store_config"))),
          llm_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "llm_config"))),
          embedder_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "embedder_config"))),
          reranker_config: sanitizeMemoryJsonForDisplay(jsonObject(formString(form, "reranker_config"))),
          secret_refs: sanitizeMemorySecretRefsForDisplay(
            jsonObject(formString(form, "secret_refs")) as Record<string, string>,
          ),
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

  async function handleRetryJob(jobId: string) {
    await runAction(
      () => retryMemoryWriteJob(jobId),
      "Memory write job queued for retry.",
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="management-panel" aria-labelledby="memory-backfill-title">
        <h2 className="section-title" id="memory-backfill-title">
          Memory backfill dry-run
        </h2>
        {data.backfillDryRun === null ? (
          <p>Backfill planning is unavailable.</p>
        ) : (
          <>
            <div className="dashboard-grid">
              <div className="metric">
                <p className="metric-label">Candidates</p>
                <p className="metric-value">{data.backfillDryRun.candidate_count}</p>
              </div>
              <div className="metric">
                <p className="metric-label">Already queued</p>
                <p className="metric-value">{data.backfillDryRun.skipped_existing_count}</p>
              </div>
              <div className="metric">
                <p className="metric-label">No profile</p>
                <p className="metric-value">{data.backfillDryRun.skipped_no_profile_count}</p>
              </div>
              <div className="metric">
                <p className="metric-label">Disabled profile</p>
                <p className="metric-value">
                  {data.backfillDryRun.skipped_disabled_profile_count}
                </p>
              </div>
            </div>
            <p className="management-notice">
              Planning only. This dry-run does not enqueue memory write jobs.
            </p>
            <div className="resource-list">
              {data.backfillDryRun.source_summaries.map((summary) => (
                <article className="resource-row" key={summary.source_kind}>
                  <div>
                    <h3>{summary.source_kind}</h3>
                    <p>
                      candidates {summary.candidate_count} / existing{" "}
                      {summary.skipped_existing_count} / no profile{" "}
                      {summary.skipped_no_profile_count} / disabled{" "}
                      {summary.skipped_disabled_profile_count}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </section>

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
                  <p>
                    Jobs: {data.profileJobs[profile.id]?.jobs.length ?? 0} / failed{" "}
                    {data.profileJobs[profile.id]?.jobs.filter((job) => job.status === "failed").length ?? 0}
                  </p>
                  <form className="inline-form" onSubmit={(event) => handleUpdate(event, profile.id)}>
                    <input className="text-input" name="name" defaultValue={profile.name} />
                    <textarea
                      className="text-input"
                      name="vector_store_config"
                      rows={3}
                      defaultValue={JSON.stringify(sanitizeMemoryJsonForDisplay(profile.vector_store_config), null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="llm_config"
                      rows={3}
                      defaultValue={JSON.stringify(sanitizeMemoryJsonForDisplay(profile.llm_config), null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="embedder_config"
                      rows={3}
                      defaultValue={JSON.stringify(sanitizeMemoryJsonForDisplay(profile.embedder_config), null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="reranker_config"
                      rows={3}
                      defaultValue={JSON.stringify(sanitizeMemoryJsonForDisplay(profile.reranker_config), null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="secret_refs"
                      rows={3}
                      defaultValue={JSON.stringify(sanitizeMemorySecretRefsForDisplay(profile.secret_refs), null, 2)}
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
                  <div className="resource-list" aria-label={`${profile.name} memory jobs`}>
                    {(data.profileJobs[profile.id]?.jobs ?? []).length === 0 ? (
                      <article className="resource-row">
                        <div>
                          <h4>No memory write jobs</h4>
                          <p>Runtime and conversation writes will appear here after they enqueue memory work.</p>
                        </div>
                      </article>
                    ) : (
                      data.profileJobs[profile.id]?.jobs.map((job) => (
                        <article className="resource-row" key={job.id}>
                          <div>
                            <h4>
                              {job.source_kind} - {job.status}
                            </h4>
                            <p>
                              Attempts {job.attempt_count} / next {new Date(job.next_attempt_at).toLocaleString()}
                            </p>
                            <p>
                              Retry: {job.is_retryable ? "retryable" : "not retryable"} / age{" "}
                              {job.age_seconds}s / last log{" "}
                              {job.last_log_success === null
                                ? "none"
                                : job.last_log_success
                                  ? "success"
                                  : "failed"}
                            </p>
                            <p>
                              World {job.world_id} / agent {job.agent_id}
                            </p>
                            {job.last_error === null ? null : <p>Error: {job.last_error}</p>}
                            {job.terminal_reason === null ? null : (
                              <p>Terminal reason: {job.terminal_reason}</p>
                            )}
                          </div>
                          {job.status === "failed" ? (
                            <button
                              className="secondary-button"
                              type="button"
                              disabled={isBusy || !job.is_retryable}
                              onClick={() => void handleRetryJob(job.id)}
                            >
                              Retry job
                            </button>
                          ) : null}
                        </article>
                      ))
                    )}
                  </div>
                  <pre>
                    {JSON.stringify(
                      sanitizeMemoryJsonForDisplay({
                        health: data.profileHealth[profile.id] ?? null,
                        logs: data.profileLogs[profile.id] ?? { write_logs: [], retrieval_logs: [] },
                        jobs: data.profileJobs[profile.id] ?? { jobs: [] },
                      }),
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

function sanitizeMemoryJsonForDisplay(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !sensitiveMemoryJsonKey(key))
      .map(([key, entry]) => [key, sanitizeMemoryJsonValue(entry)]),
  );
}

function sanitizeMemoryJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeMemoryJsonValue(entry));
  }
  if (value !== null && typeof value === "object") {
    return sanitizeMemoryJsonForDisplay(value as Record<string, unknown>);
  }
  if (typeof value === "string" && looksSensitiveMemoryString(value)) {
    return "[redacted]";
  }
  return value;
}

function sanitizeMemorySecretRefsForDisplay(value: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(value).filter(([, ref]) => typeof ref === "string" && !looksSensitiveMemoryString(ref)),
  );
}

const EXACT_SENSITIVE_MEMORY_JSON_KEYS = new Set([
  "apikey",
  "authorization",
  "base64",
  "bearertoken",
  "bytes",
  "password",
  "secret",
  "token",
]);

const SENSITIVE_MEMORY_JSON_KEY_MARKERS = [
  "accesstoken",
  "bearertoken",
  "clientsecret",
  "filesystempath",
  "filepath",
  "objectpath",
  "objectstoragepath",
  "privatekey",
  "promptsnapshot",
  "promptsnapshotid",
  "rawbytes",
  "rawoutput",
  "rawprompt",
  "refreshtoken",
  "secretkey",
  "storagepath",
  "storageuri",
  "storageurl",
];

function sensitiveMemoryJsonKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/[^a-z0-9]+/g, "");
  return (
    EXACT_SENSITIVE_MEMORY_JSON_KEYS.has(normalized) ||
    SENSITIVE_MEMORY_JSON_KEY_MARKERS.some((marker) => normalized.includes(marker))
  );
}

function looksSensitiveMemoryString(value: string): boolean {
  return /media:\/\/|base64|\/var\/|\/tmp\/|sk-[A-Za-z0-9_-]+|Bearer\s+\S+/i.test(value) || /[A-Za-z]:/.test(value) && value.includes("\\");
}
