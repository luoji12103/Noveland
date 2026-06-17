"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  AdminActionBar,
  AdminDescriptionList,
  AdminMetric,
  AdminNotice,
  AdminSection,
  AdminState,
  AdminTable,
} from "@/features/admin/admin-foundation";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";
import {
  createInvocationTag,
  deleteInvocationTag,
  getInvocation,
  getPromptSnapshot,
  invocationKindOptions,
  invocationProviderKindOptions,
  invocationRedactionStatusOptions,
  invocationRetentionPolicyOptions,
  invocationStatusOptions,
  invocationVisibilityOptions,
  listInvocationTags,
  listInvocations,
  redactInvocation,
  redactionModeOptions,
} from "@/lib/worlds/invocations";
import type {
  InvocationFilters,
  InvocationKind,
  InvocationProviderKind,
  InvocationRecord,
  InvocationRedactionStatus,
  InvocationRetentionPolicy,
  InvocationStatus,
  InvocationTag,
  InvocationVisibility,
  PromptSnapshot,
  RedactionMode,
} from "@/lib/worlds/invocations";
import type { InvocationLedgerAdminData } from "@/lib/worlds/server";

type InvocationLedgerAdminProps = {
  worldId: string;
  data: InvocationLedgerAdminData;
};

export function InvocationLedgerAdmin({ worldId, data }: InvocationLedgerAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [invocations, setInvocations] = useState(data.invocations);
  const [selectedInvocation, setSelectedInvocation] = useState(data.selectedInvocation);
  const [tagsByInvocationId, setTagsByInvocationId] = useState(data.tagsByInvocationId);
  const [promptSnapshot, setPromptSnapshot] = useState(data.promptSnapshot);
  const selectedTags =
    selectedInvocation === null ? [] : tagsByInvocationId[selectedInvocation.id] ?? [];
  const statusCounts = useMemo(() => countBy(invocations, "status"), [invocations]);
  const sensitiveCount = invocations.filter((invocation) => invocation.contains_sensitive_context).length;
  const restrictedCount = invocations.filter((invocation) => restrictedVisibility(invocation.visibility)).length;
  const redactable = selectedInvocation !== null && selectedInvocation.redaction_status !== "hidden";

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

  async function handleFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const nextInvocations = await listInvocations(worldId, filtersFromForm(form, data.isPlatformAdmin));
      setInvocations(nextInvocations);
      const nextSelected = nextInvocations[0] ?? null;
      setSelectedInvocation(nextSelected);
      setPromptSnapshot(nextSelected === null ? null : await optionalPromptSnapshot(worldId, nextSelected.id));
      setTagsByInvocationId(nextSelected === null ? {} : {
        [nextSelected.id]: await listInvocationTags(worldId, nextSelected.id),
      });
    }, "Invocation filters applied.");
  }

  async function handleSelect(invocationId: string) {
    await runAction(async () => {
      const [record, tags, snapshot] = await Promise.all([
        getInvocation(worldId, invocationId),
        listInvocationTags(worldId, invocationId),
        optionalPromptSnapshot(worldId, invocationId),
      ]);
      setSelectedInvocation(record);
      setPromptSnapshot(snapshot);
      setTagsByInvocationId((current) => ({ ...current, [invocationId]: tags }));
    }, "Invocation loaded.");
  }

  async function handleCreateTag(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedInvocation === null) {
      setNotice("Select an invocation before creating a tag.");
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      const tag = await createInvocationTag(worldId, selectedInvocation.id, {
        worldline_id: optionalFormString(form, "worldline_id"),
        tag_type: formString(form, "tag_type"),
        tag_key: formString(form, "tag_key"),
        tag_value: formString(form, "tag_value"),
      });
      setTagsByInvocationId((current) => ({
        ...current,
        [selectedInvocation.id]: [...(current[selectedInvocation.id] ?? []), tag],
      }));
      formElement.reset();
    }, "Invocation tag created.");
  }

  async function handleDeleteTag(tagId: string) {
    if (selectedInvocation === null) {
      setNotice("Select an invocation before deleting a tag.");
      return;
    }
    await runAction(async () => {
      await deleteInvocationTag(worldId, selectedInvocation.id, tagId);
      setTagsByInvocationId((current) => ({
        ...current,
        [selectedInvocation.id]: (current[selectedInvocation.id] ?? []).filter((tag) => tag.id !== tagId),
      }));
    }, "Invocation tag deleted.");
  }

  async function handleRedact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedInvocation === null) {
      setNotice("Select an invocation before redacting.");
      return;
    }
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const record = await redactInvocation(worldId, selectedInvocation.id, {
        redaction_status: formString(form, "redaction_status") as InvocationRedactionStatus,
        reason: formString(form, "reason"),
        mode: formString(form, "mode") as RedactionMode,
      });
      setSelectedInvocation(record);
      setInvocations((current) =>
        current.map((invocation) => (invocation.id === record.id ? record : invocation)),
      );
      setPromptSnapshot(await optionalPromptSnapshot(worldId, record.id));
    }, "Invocation redacted.");
  }

  return (
    <section className="management-section">
      {notice !== null ? <AdminNotice>{notice}</AdminNotice> : null}

      {!data.canManageSelectedWorld ? (
        <AdminNotice tone="error">Invocation ledger access requires world admin access.</AdminNotice>
      ) : null}

      <AdminSection
        title="Invocation ledger overview"
        description="Ledger records are audit evidence. Prompt snapshots stay behind world-admin access and explicit redaction controls."
      >
        <div className="dashboard-grid">
          <AdminMetric label="Invocations" value={invocations.length} />
          <AdminMetric label="Succeeded" value={statusCounts.succeeded ?? 0} tone="ok" />
          <AdminMetric
            label="Failed"
            value={statusCounts.failed ?? 0}
            tone={(statusCounts.failed ?? 0) > 0 ? "error" : "neutral"}
          />
          <AdminMetric
            label="Sensitive context"
            value={sensitiveCount}
            tone={sensitiveCount > 0 ? "warning" : "neutral"}
          />
          <AdminMetric
            label="Restricted"
            value={restrictedCount}
            tone={restrictedCount > 0 ? "warning" : "neutral"}
          />
        </div>
      </AdminSection>

      <AdminSection
        title="Search invocations"
        description="Filters call the backend ledger search API. Raw prompt/output fields are not added to reader or member routes."
      >
        <form className="management-form" onSubmit={handleFilter}>
          <select className="text-input" name="worldline_id" defaultValue="">
            <option value="">all worldlines</option>
            {data.worldlines.map((worldline) => (
              <option key={worldline.id} value={worldline.id}>
                {worldline.name}
              </option>
            ))}
          </select>
          <select className="text-input" name="invocation_kind" defaultValue="">
            <option value="">all invocation kinds</option>
            {invocationKindOptions.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="provider_kind" defaultValue="">
            <option value="">all provider kinds</option>
            {invocationProviderKindOptions.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="status" defaultValue="">
            <option value="">all statuses</option>
            {invocationStatusOptions.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="visibility" defaultValue="">
            <option value="">all visibility</option>
            {visibleInvocationVisibilityOptions(data.isPlatformAdmin).map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="redaction_status" defaultValue="">
            <option value="">all redaction states</option>
            {invocationRedactionStatusOptions.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="retention_policy" defaultValue="">
            <option value="">all retention policies</option>
            {invocationRetentionPolicyOptions.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="contains_sensitive_context" defaultValue="">
            <option value="">any sensitive flag</option>
            <option value="true">sensitive context</option>
            <option value="false">not sensitive</option>
          </select>
          <input className="text-input" name="contains_text" placeholder="safe text search" />
          <input className="text-input" name="tag" placeholder="tag_type:tag_key:tag_value" />
          <button className="primary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Apply invocation filters
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Invocation records">
        <div className="resource-list">
          {invocations.length === 0 ? (
            <AdminState title="No invocation records">
              Provider, media, speech, visual, and runtime paths write ledger evidence when calls execute.
            </AdminState>
          ) : (
            invocations.map((invocation) => (
              <InvocationRow
                key={invocation.id}
                invocation={invocation}
                tags={tagsByInvocationId[invocation.id] ?? []}
                isSelected={invocation.id === selectedInvocation?.id}
                onSelect={() => handleSelect(invocation.id)}
              />
            ))
          )}
        </div>
      </AdminSection>

      {selectedInvocation === null ? null : (
        <InvocationDetail
          invocation={selectedInvocation}
          tags={selectedTags}
          promptSnapshot={promptSnapshot}
          isBusy={isBusy}
          redactable={redactable}
          onCreateTag={handleCreateTag}
          onDeleteTag={handleDeleteTag}
          onRedact={handleRedact}
        />
      )}
    </section>
  );
}

function InvocationRow({
  invocation,
  tags,
  isSelected,
  onSelect,
}: {
  invocation: InvocationRecord;
  tags: InvocationTag[];
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <article className="resource-row" data-selected={isSelected ? "true" : "false"}>
      <div>
        <h3>{shortId(invocation.id)}</h3>
        <p>
          {invocation.invocation_kind} - {invocation.provider_kind} - {invocation.status}
        </p>
        <p>
          {invocation.visibility} / {invocation.redaction_status} / {invocation.retention_policy}
        </p>
        <p>
          Trace {shortId(invocation.trace_id)}. Tags: {tags.length}. Cost: {invocation.estimated_cost ?? "-"}.
        </p>
      </div>
      <button className="secondary-button" type="button" onClick={onSelect}>
        {isSelected ? "Selected" : "Inspect"}
      </button>
    </article>
  );
}

function InvocationDetail({
  invocation,
  tags,
  promptSnapshot,
  isBusy,
  redactable,
  onCreateTag,
  onDeleteTag,
  onRedact,
}: {
  invocation: InvocationRecord;
  tags: InvocationTag[];
  promptSnapshot: PromptSnapshot | null;
  isBusy: boolean;
  redactable: boolean;
  onCreateTag: (event: FormEvent<HTMLFormElement>) => void;
  onDeleteTag: (tagId: string) => void;
  onRedact: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <>
      <AdminSection
        title="Invocation detail"
        description="Prompt evidence is shown only inside this admin workspace route and uses sanitized summaries for JSON payloads."
      >
        <AdminDescriptionList
          items={[
            { label: "Invocation", value: invocation.id },
            { label: "Worldline", value: invocation.worldline_id },
            { label: "Trace", value: invocation.trace_id },
            { label: "Parent", value: invocation.parent_invocation_id ?? "-" },
            { label: "Kind", value: invocation.invocation_kind },
            { label: "Provider", value: invocation.provider_kind },
            { label: "Provider profile", value: invocation.provider_profile_id ?? "-" },
            { label: "Model", value: invocation.model_name ?? "-" },
            { label: "Status", value: invocation.status },
            { label: "Visibility", value: invocation.visibility },
            { label: "Redaction", value: invocation.redaction_status },
            { label: "Retention", value: invocation.retention_policy },
            { label: "Purge after", value: invocation.purge_after ?? "-" },
            { label: "Sensitive context", value: invocation.contains_sensitive_context ? "yes" : "no" },
            { label: "Latency", value: invocation.latency_ms ?? "-" },
            { label: "Estimated cost", value: invocation.estimated_cost ?? "-" },
            { label: "Agent", value: invocation.agent_id ?? "-" },
            { label: "Conversation", value: invocation.conversation_id ?? "-" },
            { label: "Turn", value: invocation.turn_id ?? "-" },
            { label: "Media job", value: invocation.media_job_id ?? "-" },
            { label: "Media asset", value: invocation.media_asset_id ?? "-" },
            { label: "Memory job", value: invocation.memory_write_job_id ?? "-" },
          ]}
        />

        {invocation.contains_sensitive_context ? (
          <AdminNotice tone="warning">
            This invocation is marked as sensitive context. Keep evidence inside admin-only workflows.
          </AdminNotice>
        ) : null}

        <AdminTable
          caption="Invocation tags"
          rows={tags}
          getRowKey={(tag) => tag.id}
          columns={[
            { key: "type", header: "Type", render: (tag) => tag.tag_type },
            { key: "key", header: "Key", render: (tag) => tag.tag_key },
            { key: "value", header: "Value", render: (tag) => tag.tag_value },
            {
              key: "actions",
              header: "Actions",
              render: (tag) => (
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() => onDeleteTag(tag.id)}
                >
                  Delete
                </button>
              ),
            },
          ]}
          emptyTitle="No tags"
          emptyMessage="Add tags to group ledger records for audits and regression triage."
        />

        <form className="inline-form" onSubmit={onCreateTag}>
          <input
            className="text-input"
            name="worldline_id"
            defaultValue={invocation.worldline_id}
            placeholder="worldline id"
          />
          <input className="text-input" name="tag_type" placeholder="audit" />
          <input className="text-input" name="tag_key" placeholder="phase" />
          <input className="text-input" name="tag_value" placeholder="v0.4" />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create invocation tag
          </button>
        </form>

        <form className="inline-form" onSubmit={onRedact}>
          <select className="text-input" name="redaction_status" defaultValue="redacted">
            {invocationRedactionStatusOptions.filter((value) => value !== "raw").map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <select className="text-input" name="mode" defaultValue="clear_raw_payloads">
            {redactionModeOptions.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <input className="text-input" name="reason" placeholder="redaction reason" />
          <button className="primary-button" type="submit" disabled={isBusy || !redactable}>
            Redact invocation
          </button>
        </form>
      </AdminSection>
      <EvidenceGrid invocation={invocation} promptSnapshot={promptSnapshot} />
    </>
  );
}

function EvidenceGrid({
  invocation,
  promptSnapshot,
}: {
  invocation: InvocationRecord;
  promptSnapshot: PromptSnapshot | null;
}) {
  const invocationEvidence = [
    ["Input text", invocation.input_text],
    ["Output text", invocation.output_text],
    ["Input JSON", invocation.input_json],
    ["Output JSON", invocation.output_json],
    ["Request params", invocation.request_params_json],
    ["Response metadata", invocation.response_metadata_json],
    ["Usage", invocation.usage_json],
    ["Error", invocation.error_text],
  ] as const;

  return (
    <>
      <section className="evidence-section" aria-labelledby="invocation-evidence-title">
        <div className="admin-section-header">
          <div>
            <h2 className="section-title" id="invocation-evidence-title">Invocation evidence</h2>
          </div>
        </div>
        <div className="evidence-grid">
          {invocationEvidence.map(([label, value]) => (
            <EvidenceBlock key={label} label={label} value={value} />
          ))}
        </div>
      </section>

      <section className="evidence-section" aria-labelledby="prompt-snapshot-title">
        <div className="admin-section-header">
          <div>
            <h2 className="section-title" id="prompt-snapshot-title">Prompt snapshot</h2>
            <p className="admin-section-copy">
              Checksums prove lineage even when raw payloads are redacted or hidden.
            </p>
          </div>
        </div>
        {promptSnapshot === null ? (
          <AdminState title="No prompt snapshot">
            This invocation has no accessible prompt snapshot or the snapshot is hidden by backend ACLs.
          </AdminState>
        ) : (
          <>
            <AdminDescriptionList
              items={[
                { label: "Snapshot", value: promptSnapshot.id },
                { label: "Template", value: promptSnapshot.template_key ?? "-" },
                { label: "Template version", value: promptSnapshot.template_version ?? "-" },
                { label: "Visibility", value: promptSnapshot.visibility },
                { label: "Redaction", value: promptSnapshot.redaction_status },
                { label: "Sensitive context", value: promptSnapshot.contains_sensitive_context ? "yes" : "no" },
                { label: "Prompt checksum", value: promptSnapshot.prompt_checksum_sha256 },
                { label: "Request checksum", value: promptSnapshot.request_checksum_sha256 ?? "-" },
                { label: "Response checksum", value: promptSnapshot.response_checksum_sha256 ?? "-" },
                { label: "Output checksum", value: promptSnapshot.output_checksum_sha256 ?? "-" },
              ]}
            />
            <div className="evidence-grid">
              <EvidenceBlock label="Raw prompt" value={promptSnapshot.raw_prompt_text} />
              <EvidenceBlock label="Messages" value={promptSnapshot.raw_messages_json} />
              <EvidenceBlock label="Raw request" value={promptSnapshot.raw_request_json} />
              <EvidenceBlock label="Raw response" value={promptSnapshot.raw_response_json} />
              <EvidenceBlock label="Raw output" value={promptSnapshot.raw_output_text} />
              <EvidenceBlock label="Normalized output" value={promptSnapshot.normalized_output_json} />
              <EvidenceBlock label="Prompt context" value={promptSnapshot.prompt_context_snapshot_json} />
              <EvidenceBlock label="Tool definitions" value={promptSnapshot.tool_definitions_json} />
              <EvidenceBlock label="Context pack refs" value={promptSnapshot.context_pack_refs_json} />
              <EvidenceBlock label="Input asset refs" value={promptSnapshot.input_asset_refs_json} />
            </div>
          </>
        )}
      </section>
    </>
  );
}

function EvidenceBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <article className="admin-state" data-tone="empty">
      <div>
        <h3>{label}</h3>
        <pre className="code-block">{safeEvidence(value)}</pre>
      </div>
    </article>
  );
}

function filtersFromForm(form: FormData, isPlatformAdmin: boolean): InvocationFilters {
  const containsSensitive = optionalFormString(form, "contains_sensitive_context");
  const tag = optionalFormString(form, "tag");
  return {
    worldline_id: optionalSelect(form, "worldline_id"),
    invocation_kind: optionalSelect(form, "invocation_kind") as InvocationKind | undefined,
    provider_kind: optionalSelect(form, "provider_kind") as InvocationProviderKind | undefined,
    status: optionalSelect(form, "status") as InvocationStatus | undefined,
    visibility: optionalSelect(form, "visibility") as InvocationVisibility | undefined,
    redaction_status: optionalSelect(form, "redaction_status") as InvocationRedactionStatus | undefined,
    retention_policy: optionalSelect(form, "retention_policy") as InvocationRetentionPolicy | undefined,
    contains_sensitive_context: containsSensitive === null ? undefined : containsSensitive === "true",
    contains_text: optionalFormString(form, "contains_text") ?? undefined,
    tag: tag === null ? undefined : [tag],
    limit: 100,
    include_hidden: isPlatformAdmin,
  };
}

async function optionalPromptSnapshot(worldId: string, invocationId: string): Promise<PromptSnapshot | null> {
  try {
    return await getPromptSnapshot(worldId, invocationId);
  } catch {
    return null;
  }
}

function optionalSelect(form: FormData, key: string): string | undefined {
  return optionalFormString(form, key) ?? undefined;
}

function visibleInvocationVisibilityOptions(isPlatformAdmin: boolean): InvocationVisibility[] {
  return isPlatformAdmin
    ? invocationVisibilityOptions
    : invocationVisibilityOptions.filter((value) => value !== "developer_only" && value !== "hidden");
}

function restrictedVisibility(visibility: InvocationVisibility): boolean {
  return visibility === "developer_only" || visibility === "hidden";
}

function countBy<K extends keyof InvocationRecord>(
  invocations: InvocationRecord[],
  key: K,
): Record<string, number> {
  return invocations.reduce<Record<string, number>>((counts, invocation) => {
    const value = String(invocation[key]);
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

function safeEvidence(value: unknown): string {
  const sanitized = sanitizeEvidence(value);
  if (typeof sanitized === "string") {
    return sanitized;
  }
  return JSON.stringify(sanitized, null, 2);
}

function sanitizeEvidence(value: unknown): unknown {
  if (typeof value === "string") {
    return sensitiveValue(value) ? "[redacted]" : truncate(value, 500);
  }
  if (Array.isArray(value)) {
    return value.slice(0, 8).map((item) => sanitizeEvidence(item));
  }
  if (value !== null && typeof value === "object") {
    const output: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>).slice(0, 24)) {
      if (sensitiveKey(key)) {
        output[`redacted_${Object.keys(output).length + 1}`] = "[redacted]";
      } else {
        output[key] = sanitizeEvidence(item);
      }
    }
    return output;
  }
  return value ?? "-";
}

const SENSITIVE_EVIDENCE_KEY_MARKERS = [
  "apikey",
  "token",
  "bearertoken",
  "authorization",
  "secret",
  "clientsecret",
  "accesskey",
  "password",
  "privatekey",
  "storageuri",
  "previewuri",
  "thumbnailuri",
  "objectstoragepath",
  "objectpath",
  "filesystempath",
  "filepath",
  "path",
  "rawbytes",
  "bytes",
  "base64",
  "rawprompt",
  "rawoutput",
  "promptsnapshot",
  "promptsnapshotid",
];

function sensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/[^a-z0-9]+/g, "");
  return SENSITIVE_EVIDENCE_KEY_MARKERS.some((marker) => normalized.includes(marker));
}

function sensitiveValue(value: string): boolean {
  return (
    /media:\/\/|base64|\/var\/|\/tmp\/|[A-Za-z]:\\|sk-[A-Za-z0-9]/.test(value)
    || isBase64Like(value)
  );
}

function isBase64Like(value: string): boolean {
  const normalized = value.trim();
  return (
    normalized.length >= 8
    && normalized.length % 4 === 0
    && /^[A-Za-z0-9+/]+={0,2}$/.test(normalized)
    && !/^[a-f0-9]{32,}$/i.test(normalized)
  );
}

function truncate(value: string, limit: number): string {
  return value.length <= limit ? value : `${value.slice(0, limit)}...`;
}

function shortId(value: string | null): string {
  if (value === null) {
    return "-";
  }
  return value.length <= 12 ? value : value.slice(0, 12);
}
