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
import { formString, jsonObject, messageForError, optionalFormString } from "@/features/workspace/form-utils";
import {
  cancelMediaJob,
  listMediaAssets,
  listMediaJobs,
  listMediaReferences,
  mediaAssetKindOptions,
  mediaAssetRoleOptions,
  mediaJobKindOptions,
  mediaJobStatusOptions,
  mediaObjectDownloadPath,
  mediaStatusOptions,
  mediaVisibilityOptions,
  retryMediaJob,
  updateMediaAsset,
  uploadMediaAsset,
} from "@/lib/worlds/media";
import type {
  MediaAsset,
  MediaAssetKind,
  MediaAssetRole,
  MediaAssetStatus,
  MediaJob,
  MediaJobKind,
  MediaJobStatus,
  MediaObject,
  MediaReference,
  MediaVisibility,
} from "@/lib/worlds/media";
import type { MediaAdminData } from "@/lib/worlds/server";

type MediaAdminProps = {
  worldId: string;
  data: MediaAdminData;
};

export function MediaAdmin({ worldId, data }: MediaAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [assets, setAssets] = useState(data.assets);
  const [jobs, setJobs] = useState(data.jobs);
  const [references, setReferences] = useState(data.references);
  const [selectedAssetId, setSelectedAssetId] = useState(data.assets[0]?.id ?? null);
  const selectedAsset = useMemo(
    () => assets.find((asset) => asset.id === selectedAssetId) ?? null,
    [assets, selectedAssetId],
  );
  const selectedObjects = selectedAsset === null ? [] : data.objectsByAssetId[selectedAsset.id] ?? [];
  const selectedReferences =
    selectedAsset === null ? null : data.referencesByAssetId[selectedAsset.id] ?? null;

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

  async function handleAssetFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const nextAssets = await listMediaAssets(worldId, {
        worldline_id: optionalFormString(form, "worldline_id") ?? undefined,
        asset_kind: optionalSelect(form, "asset_kind") as MediaAssetKind | undefined,
        asset_role: optionalSelect(form, "asset_role") as MediaAssetRole | undefined,
        status: optionalSelect(form, "status") as MediaAssetStatus | undefined,
        visibility: optionalSelect(form, "visibility") as MediaVisibility | undefined,
        contains_text: optionalFormString(form, "contains_text") ?? undefined,
        limit: 100,
      });
      setAssets(nextAssets);
      setSelectedAssetId(nextAssets[0]?.id ?? null);
    }, "Media asset filters applied.");
  }

  async function handleJobFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setJobs(
        await listMediaJobs(worldId, {
          worldline_id: optionalFormString(form, "worldline_id") ?? undefined,
          job_kind: optionalSelect(form, "job_kind") as MediaJobKind | undefined,
          status: optionalSelect(form, "status") as MediaJobStatus | undefined,
          provider_kind: optionalFormString(form, "provider_kind") ?? undefined,
          limit: 100,
        }),
      );
    }, "Media job filters applied.");
  }

  async function handleReferenceFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setReferences(
        await listMediaReferences(worldId, {
          worldline_id: optionalFormString(form, "worldline_id") ?? undefined,
          asset_id: optionalFormString(form, "asset_id") ?? undefined,
          limit: 100,
        }),
      );
    }, "Media reference filters applied.");
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const fileInput = formElement.elements.namedItem("file");
    const file = fileInput instanceof HTMLInputElement ? fileInput.files?.[0] ?? null : null;
    if (file === null || file.size === 0) {
      setNotice("Choose a media file to upload.");
      return;
    }
    await runAction(async () => {
      const response = await uploadMediaAsset(worldId, {
        file,
        worldline_id: optionalFormString(form, "worldline_id"),
        asset_kind: formString(form, "asset_kind") as MediaAssetKind,
        asset_role: formString(form, "asset_role") as MediaAssetRole,
        visibility: formString(form, "visibility") as MediaVisibility,
        title: optionalFormString(form, "title"),
        description: optionalFormString(form, "description"),
        metadata: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
      });
      setSelectedAssetId(response.asset.id);
      formElement.reset();
    }, "Media asset uploaded.");
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>, assetId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateMediaAsset(worldId, assetId, {
          title: optionalFormString(form, "title"),
          description: optionalFormString(form, "description"),
          status: formString(form, "status") as MediaAssetStatus,
          visibility: formString(form, "visibility") as MediaVisibility,
          metadata: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
        }),
      "Media asset saved.",
    );
  }

  const availableCount = assets.filter((asset) => asset.status === "available").length;
  const restrictedCount = assets.filter((asset) => restrictedVisibility(asset.visibility)).length;
  const activeJobCount = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
  const objectCount = Object.values(data.objectsByAssetId).reduce((total, objects) => total + objects.length, 0);

  return (
    <section className="management-section">
      {notice !== null ? <AdminNotice>{notice}</AdminNotice> : null}

      {!data.canManageSelectedWorld ? (
        <AdminNotice tone="error">Media administration requires world admin access.</AdminNotice>
      ) : null}

      <AdminSection
        title="Media asset overview"
        description="Media records stay in the media kernel. The console shows identifiers and checksums, not internal object paths."
      >
        <div className="dashboard-grid">
          <AdminMetric label="Assets" value={assets.length} />
          <AdminMetric label="Available" value={availableCount} tone={availableCount > 0 ? "ok" : "neutral"} />
          <AdminMetric label="Objects loaded" value={objectCount} />
          <AdminMetric label="Active jobs" value={activeJobCount} tone={activeJobCount > 0 ? "warning" : "neutral"} />
          <AdminMetric label="Restricted" value={restrictedCount} tone={restrictedCount > 0 ? "warning" : "neutral"} />
        </div>
      </AdminSection>

      <AdminSection
        title="Upload media asset"
        description="Uploads use the backend media API with CSRF. Binary content is not placed in JSON state."
      >
        <form className="management-form" onSubmit={handleUpload}>
          <input className="text-input" name="worldline_id" placeholder="worldline id" />
          <select className="text-input" name="asset_kind" defaultValue="image">
            {mediaAssetKindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="asset_role" defaultValue="reference_image">
            {mediaAssetRoleOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="visibility" defaultValue="world_admin">
            {mediaVisibilityOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <input className="text-input" name="title" placeholder="Title" />
          <input className="text-input" name="description" placeholder="Description" />
          <textarea className="text-input" name="metadata_json" defaultValue="{}" rows={3} />
          <input className="text-input" name="file" type="file" aria-label="Upload file" />
          <button className="primary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Upload media asset
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Asset filters">
        <form className="inline-form" onSubmit={handleAssetFilter}>
          <input className="text-input" name="worldline_id" placeholder="worldline id" />
          <select className="text-input" name="asset_kind" defaultValue="">
            <option value="">any kind</option>
            {mediaAssetKindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="asset_role" defaultValue="">
            <option value="">any role</option>
            {mediaAssetRoleOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="status" defaultValue="">
            <option value="">any status</option>
            {mediaStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="visibility" defaultValue="">
            <option value="">any visibility</option>
            {mediaVisibilityOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <input className="text-input" name="contains_text" placeholder="metadata search" />
          <button className="secondary-button" type="submit" disabled={isBusy}>
            Apply asset filters
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Media assets">
        <div className="resource-list">
          {assets.length === 0 ? (
            <AdminState title="No media assets">
              Upload a reference asset or run a provider flow that writes through the media kernel.
            </AdminState>
          ) : (
            assets.map((asset) => (
              <AssetRow
                key={asset.id}
                asset={asset}
                objectCount={data.objectsByAssetId[asset.id]?.length ?? 0}
                isSelected={asset.id === selectedAsset?.id}
                onSelect={() => setSelectedAssetId(asset.id)}
              />
            ))
          )}
        </div>
      </AdminSection>

      {selectedAsset === null ? null : (
        <AssetDetail
          worldId={worldId}
          asset={selectedAsset}
          objects={selectedObjects}
          references={references.filter((reference) => reference.asset_id === selectedAsset.id)}
          referenceSummary={selectedReferences}
          isBusy={isBusy}
          onUpdate={(event) => handleUpdate(event, selectedAsset.id)}
        />
      )}

      <AdminSection title="Media jobs" description="Queued and completed media work. Request payloads are summarized by key only.">
        <form className="inline-form" onSubmit={handleJobFilter}>
          <input className="text-input" name="worldline_id" placeholder="worldline id" />
          <select className="text-input" name="job_kind" defaultValue="">
            <option value="">any job kind</option>
            {mediaJobKindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="status" defaultValue="">
            <option value="">any status</option>
            {mediaJobStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <input className="text-input" name="provider_kind" placeholder="provider kind" />
          <button className="secondary-button" type="submit" disabled={isBusy}>
            Apply job filters
          </button>
        </form>
        <AdminTable
          caption="Media jobs"
          rows={jobs}
          getRowKey={(job) => job.id}
          columns={[
            { key: "kind", header: "Kind", render: (job) => job.job_kind },
            { key: "status", header: "Status", render: (job) => job.status },
            { key: "priority", header: "Priority", render: (job) => job.priority },
            { key: "provider", header: "Provider", render: (job) => job.provider_kind ?? "-" },
            { key: "request", header: "Request keys", render: (job) => safeJsonSummary(job.request_json) },
            {
              key: "actions",
              header: "Actions",
              render: (job) => (
                <JobActions
                  job={job}
                  isBusy={isBusy}
                  onCancel={() => runAction(() => cancelMediaJob(worldId, job.id), "Media job cancelled.")}
                  onRetry={() => runAction(() => retryMediaJob(worldId, job.id), "Media job retry queued.")}
                />
              ),
            },
          ]}
          emptyTitle="No media jobs"
          emptyMessage="Provider and upload flows create media jobs when work is queued or executed."
        />
      </AdminSection>

      <AdminSection title="Reference browser">
        <form className="inline-form" onSubmit={handleReferenceFilter}>
          <input className="text-input" name="worldline_id" placeholder="worldline id" />
          <input className="text-input" name="asset_id" placeholder="asset id" />
          <button className="secondary-button" type="submit" disabled={isBusy}>
            Apply reference filters
          </button>
        </form>
        <AdminTable
          caption="Media references"
          rows={references}
          getRowKey={(reference) => reference.id}
          columns={[
            { key: "asset", header: "Asset", render: (reference) => shortId(reference.asset_id) },
            { key: "kind", header: "Ref kind", render: (reference) => reference.ref_kind },
            { key: "role", header: "Role", render: (reference) => reference.ref_role },
            { key: "ref", header: "Ref id", render: (reference) => shortId(reference.ref_id) },
            { key: "order", header: "Order", render: (reference) => reference.display_order },
          ]}
          emptyTitle="No media references"
          emptyMessage="Attach media to turns, agents, scenes, jobs, or invocations through backend media APIs."
        />
      </AdminSection>
    </section>
  );
}

function AssetRow({
  asset,
  objectCount,
  isSelected,
  onSelect,
}: {
  asset: MediaAsset;
  objectCount: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <article className="resource-row" data-selected={isSelected ? "true" : "false"}>
      <div>
        <h3>{asset.title ?? asset.asset_role}</h3>
        <p>
          {asset.asset_kind} - {asset.asset_role} - {asset.status} - {asset.visibility}
        </p>
        <p>
          Worldline {shortId(asset.worldline_id)} / objects {objectCount} / checksum{" "}
          {asset.checksum_sha256 === null ? "pending" : shortChecksum(asset.checksum_sha256)}
        </p>
      </div>
      <button className="secondary-button" type="button" onClick={onSelect}>
        {isSelected ? "Selected" : "Inspect"}
      </button>
    </article>
  );
}

function AssetDetail({
  worldId,
  asset,
  objects,
  references,
  referenceSummary,
  isBusy,
  onUpdate,
}: {
  worldId: string;
  asset: MediaAsset;
  objects: MediaObject[];
  references: MediaReference[];
  referenceSummary: MediaAdminData["referencesByAssetId"][string];
  isBusy: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <AdminSection
      title="Asset detail"
      description="Safe media metadata and object actions. Internal object storage references are intentionally not displayed."
    >
      <AdminDescriptionList
        items={[
          { label: "Asset", value: asset.id },
          { label: "Worldline", value: asset.worldline_id },
          { label: "Kind", value: asset.asset_kind },
          { label: "Role", value: asset.asset_role },
          { label: "Source", value: asset.source_kind },
          { label: "Status", value: asset.status },
          { label: "Visibility", value: asset.visibility },
          { label: "MIME", value: asset.mime_type ?? "-" },
          { label: "Size", value: formatBytes(asset.size_bytes) },
          { label: "Dimensions", value: formatDimensions(asset) },
          { label: "Checksum", value: asset.checksum_sha256 ?? "pending" },
          { label: "Metadata keys", value: safeJsonSummary(asset.metadata) },
        ]}
      />
      {restrictedVisibility(asset.visibility) ? (
        <AdminNotice tone="warning">
          This asset uses restricted visibility. Backend ACLs decide whether it is returned.
        </AdminNotice>
      ) : null}
      <form className="inline-form" onSubmit={onUpdate}>
        <input className="text-input" name="title" defaultValue={asset.title ?? ""} />
        <input className="text-input" name="description" defaultValue={asset.description ?? ""} />
        <select className="text-input" name="status" defaultValue={asset.status}>
          {mediaStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select className="text-input" name="visibility" defaultValue={asset.visibility}>
          {mediaVisibilityOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <textarea
          className="text-input"
          name="metadata_json"
          rows={4}
          defaultValue={JSON.stringify(sanitizeJsonForDisplay(asset.metadata), null, 2)}
        />
        <button className="primary-button" type="submit" disabled={isBusy}>
          Save media asset
        </button>
      </form>
      <AdminTable
        caption="Media objects"
        rows={objects}
        getRowKey={(object) => object.id}
        columns={[
          { key: "role", header: "Role", render: (object) => object.object_role },
          { key: "file", header: "Filename", render: (object) => object.filename ?? "-" },
          { key: "mime", header: "MIME", render: (object) => object.mime_type },
          { key: "size", header: "Size", render: (object) => formatBytes(object.size_bytes) },
          { key: "checksum", header: "Checksum", render: (object) => shortChecksum(object.checksum_sha256) },
          {
            key: "download",
            header: "Download",
            render: (object) => (
              <a className="secondary-button" href={mediaObjectDownloadPath(worldId, object.id)}>
                Download
              </a>
            ),
          },
        ]}
        emptyTitle="No media objects"
        emptyMessage="Available media assets should have at least one object record."
      />
      <AdminDescriptionList
        items={[
          { label: "Context count", value: referenceSummary?.contexts.length ?? 0 },
          { label: "Tag count", value: referenceSummary?.tag_count ?? 0 },
          { label: "Collection count", value: referenceSummary?.collection_count ?? 0 },
          { label: "Input count", value: referenceSummary?.input_count ?? 0 },
          { label: "Output count", value: referenceSummary?.output_count ?? 0 },
        ]}
      />
      <AdminTable
        caption="Selected asset references"
        rows={references}
        getRowKey={(reference) => reference.id}
        columns={[
          { key: "kind", header: "Ref kind", render: (reference) => reference.ref_kind },
          { key: "role", header: "Role", render: (reference) => reference.ref_role },
          { key: "ref", header: "Ref id", render: (reference) => shortId(reference.ref_id) },
        ]}
        emptyTitle="No references"
        emptyMessage="This asset is not linked to a turn, agent, scene, job, or invocation in the loaded records."
      />
    </AdminSection>
  );
}

function JobActions({
  job,
  isBusy,
  onCancel,
  onRetry,
}: {
  job: MediaJob;
  isBusy: boolean;
  onCancel: () => void;
  onRetry: () => void;
}) {
  const isTerminal = job.status === "succeeded" || job.status === "failed" || job.status === "cancelled";
  return (
    <AdminActionBar>
      <button className="secondary-button" type="button" disabled={isBusy || isTerminal} onClick={onCancel}>
        Cancel
      </button>
      <button className="secondary-button" type="button" disabled={isBusy || job.status !== "failed"} onClick={onRetry}>
        Retry
      </button>
    </AdminActionBar>
  );
}

function optionalSelect(form: FormData, key: string): string | undefined {
  const value = formString(form, key);
  return value === "" ? undefined : value;
}

function restrictedVisibility(value: MediaVisibility): boolean {
  return value === "developer_only" || value === "hidden";
}

function safeJsonSummary(value: Record<string, unknown>): string {
  const keys = Object.keys(value).filter((key) => !sensitiveJsonKey(key));
  if (keys.length === 0) {
    return "{}";
  }
  return keys.slice(0, 6).join(", ");
}

function sensitiveJsonKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return [
    "storage",
    "uri",
    "path",
    "base64",
    "bytes",
    "prompt",
    "output",
    "secret",
    "token",
    "authorization",
  ].some((piece) => normalized.includes(piece));
}

function sanitizeJsonForDisplay(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !sensitiveJsonKey(key))
      .map(([key, entry]) => [key, sanitizeJsonValue(entry)]),
  );
}

function sanitizeJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeJsonValue(entry));
  }
  if (value !== null && typeof value === "object") {
    return sanitizeJsonForDisplay(value as Record<string, unknown>);
  }
  if (typeof value === "string" && looksSensitiveString(value)) {
    return "[redacted]";
  }
  return value;
}

function looksSensitiveString(value: string): boolean {
  return /media:\/\/|base64|\/var\/|\/tmp\/|[A-Za-z]:\\/.test(value);
}

function shortId(value: string): string {
  return value.length <= 12 ? value : `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function shortChecksum(value: string): string {
  return value.length <= 16 ? value : `${value.slice(0, 12)}...`;
}

function formatBytes(value: number | null): string {
  if (value === null) {
    return "-";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDimensions(asset: MediaAsset): string {
  if (asset.width !== null && asset.height !== null) {
    return `${asset.width}x${asset.height}`;
  }
  if (asset.duration_ms !== null) {
    return `${asset.duration_ms} ms`;
  }
  return "-";
}
