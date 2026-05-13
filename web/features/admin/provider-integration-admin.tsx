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
  createProviderIntegration,
  deleteProviderIntegration,
  providerAdapterOptions,
  providerKindOptions,
  providerStatusOptions,
  providerVisibilityOptions,
  runProviderHealthCheck,
  runProviderSmokeTest,
  updateProviderIntegration,
} from "@/lib/worlds/provider-integrations";
import type {
  ProviderAdapterKind,
  ProviderCapabilityInput,
  ProviderIntegration,
  ProviderIntegrationStatus,
  ProviderKind,
  ProviderScopeKind,
  ProviderVisibility,
} from "@/lib/worlds/provider-integrations";
import type { ProviderIntegrationAdminData } from "@/lib/worlds/server";

type ProviderIntegrationAdminProps = {
  worldId: string;
  data: ProviderIntegrationAdminData;
};

export function ProviderIntegrationAdmin({ worldId, data }: ProviderIntegrationAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [selectedProviderId, setSelectedProviderId] = useState(data.providers[0]?.id ?? null);
  const selectedProvider = useMemo(
    () => data.providers.find((provider) => provider.id === selectedProviderId) ?? null,
    [data.providers, selectedProviderId],
  );
  const selectedCapabilities =
    selectedProvider === null ? [] : data.capabilitiesByProviderId[selectedProvider.id] ?? [];
  const selectedHealthChecks =
    selectedProvider === null ? [] : data.healthChecksByProviderId[selectedProvider.id] ?? [];

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
    await runAction(async () => {
      const provider = await createProviderIntegration(worldId, {
        scope_kind: formString(form, "scope_kind") as ProviderScopeKind,
        provider_kind: formString(form, "provider_kind") as ProviderKind,
        adapter_kind: formString(form, "adapter_kind") as ProviderAdapterKind,
        provider_key: formString(form, "provider_key"),
        display_name: formString(form, "display_name"),
        base_url: optionalFormString(form, "base_url"),
        auth_ref: optionalFormString(form, "auth_ref"),
        config_json: jsonObject(formString(form, "config_json")),
        default_params_json: jsonObject(formString(form, "default_params_json")),
        status: formString(form, "status") as ProviderIntegrationStatus,
        visibility: formString(form, "visibility") as ProviderVisibility,
        capabilities: parseCapabilities(formString(form, "capabilities")),
      });
      setSelectedProviderId(provider.id);
      formElement.reset();
    }, "Provider integration created.");
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>, providerId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateProviderIntegration(worldId, providerId, {
          display_name: formString(form, "display_name"),
          base_url: optionalFormString(form, "base_url"),
          auth_ref: optionalFormString(form, "auth_ref"),
          config_json: jsonObject(formString(form, "config_json")),
          default_params_json: jsonObject(formString(form, "default_params_json")),
          status: formString(form, "status") as ProviderIntegrationStatus,
          visibility: formString(form, "visibility") as ProviderVisibility,
          capabilities: parseCapabilities(formString(form, "capabilities")),
        }),
      "Provider integration saved.",
    );
  }

  const activeCount = data.providers.filter((provider) => provider.status === "active").length;
  const restrictedCount = data.providers.filter((provider) => restrictedVisibility(provider)).length;
  const authRefCount = data.providers.filter((provider) => provider.auth_ref_configured).length;

  return (
    <section className="management-section">
      {notice !== null ? <AdminNotice>{notice}</AdminNotice> : null}

      {!data.canManageSelectedWorld ? (
        <AdminNotice tone="error">Provider integrations require world admin access.</AdminNotice>
      ) : null}

      <AdminSection
        title="Provider integration overview"
        description="World-scoped provider registry records. Secrets stay behind auth_ref references and backend execution boundaries."
      >
        <div className="dashboard-grid">
          <AdminMetric label="Providers" value={data.providers.length} />
          <AdminMetric label="Active" value={activeCount} tone={activeCount > 0 ? "ok" : "neutral"} />
          <AdminMetric label="Auth refs" value={authRefCount} />
          <AdminMetric
            label="Restricted"
            value={restrictedCount}
            tone={restrictedCount > 0 ? "warning" : "neutral"}
          />
        </div>
      </AdminSection>

      <AdminSection
        title="Create provider integration"
        description="Dispatch uses adapter_kind from the provider kernel. Do not place API keys in JSON fields."
      >
        <form className="management-form" onSubmit={handleCreate}>
          <select className="text-input" name="scope_kind" defaultValue="world">
            <option value="world">world</option>
            {data.isPlatformAdmin ? <option value="global">global</option> : null}
          </select>
          <select className="text-input" name="provider_kind" defaultValue="image_generation">
            {providerKindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="adapter_kind" defaultValue="fake">
            {providerAdapterOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <input className="text-input" name="provider_key" placeholder="fake-image" />
          <input className="text-input" name="display_name" placeholder="Display name" />
          <input className="text-input" name="base_url" placeholder="https://provider.example" />
          <input className="text-input" name="auth_ref" placeholder="env:OPENAI_API_KEY" />
          <select className="text-input" name="status" defaultValue="active">
            {providerStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="visibility" defaultValue="world_admin">
            {providerVisibilityOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <textarea className="text-input" name="config_json" defaultValue="{}" rows={3} />
          <textarea className="text-input" name="default_params_json" defaultValue="{}" rows={3} />
          <textarea
            className="text-input"
            name="capabilities"
            rows={4}
            defaultValue={'[{"capability_key":"image.generate","capability_json":{}}]'}
          />
          <button className="primary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Create provider integration
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Provider integrations">
        <div className="resource-list">
          {data.providers.length === 0 ? (
            <AdminState title="No provider integrations">
              Create a fake provider first, then add real provider references when env secrets are configured.
            </AdminState>
          ) : (
            data.providers.map((provider) => (
              <ProviderRow
                key={provider.id}
                provider={provider}
                isSelected={provider.id === selectedProvider?.id}
                capabilityCount={data.capabilitiesByProviderId[provider.id]?.length ?? 0}
                latestHealth={data.healthChecksByProviderId[provider.id]?.[0]?.status ?? "unknown"}
                onSelect={() => setSelectedProviderId(provider.id)}
              />
            ))
          )}
        </div>
      </AdminSection>

      {selectedProvider === null ? null : (
        <ProviderDetail
          provider={selectedProvider}
          capabilities={selectedCapabilities}
          healthChecks={selectedHealthChecks}
          isBusy={isBusy}
          onUpdate={(event) => handleUpdate(event, selectedProvider.id)}
          onHealthCheck={() =>
            runAction(
              () => runProviderHealthCheck(worldId, selectedProvider.id),
              "Provider health check completed.",
            )
          }
          onSmokeTest={() =>
            runAction(
              () =>
                runProviderSmokeTest(worldId, selectedProvider.id, {
                  input_text: "Noveland provider smoke test",
                  input_json: {},
                  request_json: {},
                }),
              "Provider smoke test completed.",
            )
          }
          onDelete={() =>
            runAction(
              () => deleteProviderIntegration(worldId, selectedProvider.id),
              "Provider integration deleted.",
            )
          }
        />
      )}
    </section>
  );
}

function ProviderRow({
  provider,
  isSelected,
  capabilityCount,
  latestHealth,
  onSelect,
}: {
  provider: ProviderIntegration;
  isSelected: boolean;
  capabilityCount: number;
  latestHealth: string;
  onSelect: () => void;
}) {
  return (
    <article className="resource-row" data-selected={isSelected ? "true" : "false"}>
      <div>
        <h3>{provider.display_name}</h3>
        <p>
          {provider.provider_key} - {provider.provider_kind} - {provider.adapter_kind}
        </p>
        <p>
          {provider.scope_kind} / {provider.visibility} / {provider.status} / health {latestHealth}
        </p>
        <p>
          Capabilities: {capabilityCount}. Auth ref:{" "}
          {provider.auth_ref_configured ? provider.auth_ref ?? "configured" : "not configured"}
        </p>
      </div>
      <button className="secondary-button" type="button" onClick={onSelect}>
        {isSelected ? "Selected" : "Inspect"}
      </button>
    </article>
  );
}

function ProviderDetail({
  provider,
  capabilities,
  healthChecks,
  isBusy,
  onUpdate,
  onHealthCheck,
  onSmokeTest,
  onDelete,
}: {
  provider: ProviderIntegration;
  capabilities: ProviderCapabilityInput[];
  healthChecks: Array<{
    id: string;
    status: string;
    latency_ms: number | null;
    checked_at: string;
    error_text: string | null;
    metadata_json: Record<string, unknown>;
  }>;
  isBusy: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
  onHealthCheck: () => void;
  onSmokeTest: () => void;
  onDelete: () => void;
}) {
  return (
    <AdminSection
      title="Provider detail"
      description="Safe provider metadata and actions. Resolved secrets are never displayed."
    >
      <AdminDescriptionList
        items={[
          { label: "Provider", value: provider.provider_key },
          { label: "Kind", value: provider.provider_kind },
          { label: "Adapter", value: provider.adapter_kind },
          { label: "Scope", value: provider.scope_kind },
          { label: "Visibility", value: provider.visibility },
          { label: "Auth ref", value: provider.auth_ref_configured ? provider.auth_ref ?? "configured" : "not configured" },
        ]}
      />
      {restrictedVisibility(provider) ? (
        <AdminNotice tone="warning">
          This provider uses restricted visibility. Non-platform users only see it when backend ACLs allow access.
        </AdminNotice>
      ) : null}
      <form className="inline-form" onSubmit={onUpdate}>
        <input className="text-input" name="display_name" defaultValue={provider.display_name} />
        <input className="text-input" name="base_url" defaultValue={provider.base_url ?? ""} />
        <input className="text-input" name="auth_ref" defaultValue={provider.auth_ref ?? ""} />
        <select className="text-input" name="status" defaultValue={provider.status}>
          {providerStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select className="text-input" name="visibility" defaultValue={provider.visibility}>
          {providerVisibilityOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <textarea
          className="text-input"
          name="config_json"
          rows={4}
          defaultValue={JSON.stringify(provider.config_json, null, 2)}
        />
        <textarea
          className="text-input"
          name="default_params_json"
          rows={4}
          defaultValue={JSON.stringify(provider.default_params_json, null, 2)}
        />
        <textarea
          className="text-input"
          name="capabilities"
          rows={4}
          defaultValue={JSON.stringify(capabilities, null, 2)}
        />
        <AdminActionBar>
          <button className="primary-button" type="submit" disabled={isBusy}>
            Save provider
          </button>
          <button className="secondary-button" type="button" disabled={isBusy} onClick={onHealthCheck}>
            Run health check
          </button>
          <button className="secondary-button" type="button" disabled={isBusy} onClick={onSmokeTest}>
            Smoke test
          </button>
          <button className="secondary-button" type="button" disabled={isBusy} onClick={onDelete}>
            Delete provider
          </button>
        </AdminActionBar>
      </form>
      <AdminTable
        caption="Provider capabilities"
        rows={capabilities}
        getRowKey={(capability) => capability.capability_key}
        columns={[
          { key: "key", header: "Capability", render: (capability) => capability.capability_key },
          { key: "shape", header: "Shape", render: (capability) => safeJsonSummary(capability.capability_json) },
        ]}
        emptyTitle="No capabilities"
        emptyMessage="Add capability records so routing can match provider_kind and adapter_kind safely."
      />
      <AdminTable
        caption="Provider health checks"
        rows={healthChecks}
        getRowKey={(check) => check.id}
        columns={[
          { key: "status", header: "Status", render: (check) => check.status },
          { key: "latency", header: "Latency", render: (check) => check.latency_ms ?? "-" },
          { key: "checked", header: "Checked", render: (check) => check.checked_at },
          { key: "metadata", header: "Safe metadata", render: (check) => safeJsonSummary(check.metadata_json) },
          { key: "error", header: "Error", render: (check) => check.error_text ?? "-" },
        ]}
        emptyTitle="No health checks"
        emptyMessage="Run a health check or smoke test to record safe provider status."
      />
    </AdminSection>
  );
}

function parseCapabilities(value: string): ProviderCapabilityInput[] {
  const parsed = JSON.parse(value || "[]") as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("Capabilities must be a JSON array.");
  }
  return parsed.map((item) => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      throw new Error("Each capability must be an object.");
    }
    const record = item as Record<string, unknown>;
    if (typeof record.capability_key !== "string" || record.capability_key.trim() === "") {
      throw new Error("Each capability requires capability_key.");
    }
    return {
      capability_key: record.capability_key,
      capability_json:
        record.capability_json !== null &&
        typeof record.capability_json === "object" &&
        !Array.isArray(record.capability_json)
          ? (record.capability_json as Record<string, unknown>)
          : {},
    };
  });
}

function restrictedVisibility(provider: ProviderIntegration): boolean {
  return provider.visibility === "developer_only" || provider.visibility === "hidden";
}

function safeJsonSummary(value: Record<string, unknown>): string {
  const keys = Object.keys(value);
  if (keys.length === 0) {
    return "{}";
  }
  return keys.slice(0, 6).join(", ");
}
