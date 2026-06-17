"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { PluginConfigFields } from "@/features/plugins/plugin-config-fields";
import {
  createProviderProfile,
  disableProviderProfile,
  testProviderProfile,
  updateProviderProfile,
} from "@/lib/worlds/client";
import type { ProviderAdminData } from "@/lib/worlds/server";
import type { PluginBinding, PluginCatalogEntry, ProviderProfile } from "@/lib/worlds/types";
import {
  formString,
  jsonObject,
  messageForError,
  numberFormValue,
  optionalNumberFormValue,
  optionalFormString,
} from "@/features/workspace/form-utils";

type ProviderAdminProps = {
  data: ProviderAdminData;
};

export function ProviderAdmin({ data }: ProviderAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const profiles = data.profiles;
  const healthByProfileId = new Map(data.providerHealth.map((health) => [health.id, health]));
  const modelProviderPlugins = data.modelProviderPlugins;

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

  async function handleCreateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createProviderProfile({
          profile_key: formString(form, "profile_key"),
          name: formString(form, "name"),
          provider_type: formString(form, "provider_type") as
            | "openai_compatible"
            | "anthropic_compatible",
          plugin_identifier: optionalFormString(form, "plugin_identifier"),
          plugin_config: providerAdminJsonObject(formString(form, "plugin_config")),
          base_url: formString(form, "base_url"),
          model_name: formString(form, "model_name"),
          api_key_ref: formString(form, "api_key_ref"),
          capabilities: providerAdminJsonObject(formString(form, "capabilities")),
          timeout_seconds: numberFormValue(form, "timeout_seconds", 20),
          retry_attempts: numberFormValue(form, "retry_attempts", 1),
          rate_limit_per_minute: optionalNumberFormValue(form, "rate_limit_per_minute"),
        });
        formElement.reset();
      },
      "Provider profile created.",
    );
  }

  async function handleUpdateProfile(event: FormEvent<HTMLFormElement>, profileId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateProviderProfile(profileId, {
          name: formString(form, "name"),
          plugin_identifier: optionalFormString(form, "plugin_identifier"),
          plugin_config: providerAdminJsonObject(formString(form, "plugin_config")),
          base_url: formString(form, "base_url"),
          model_name: formString(form, "model_name"),
          api_key_ref: formString(form, "api_key_ref"),
          capabilities: providerAdminJsonObject(formString(form, "capabilities")),
          timeout_seconds: numberFormValue(form, "timeout_seconds", 20),
          retry_attempts: numberFormValue(form, "retry_attempts", 1),
          rate_limit_per_minute: optionalNumberFormValue(form, "rate_limit_per_minute"),
          is_enabled: form.get("is_enabled") === "on",
        }),
      "Provider profile saved.",
    );
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="management-panel" aria-labelledby="create-provider-title">
        <h2 className="section-title" id="create-provider-title">
          Create provider profile
        </h2>
        <form className="management-form" onSubmit={handleCreateProfile}>
          <input className="text-input" name="profile_key" placeholder="profile-key" />
          <input className="text-input" name="name" placeholder="Profile name" />
          <select className="text-input" name="provider_type" defaultValue="openai_compatible">
            <option value="openai_compatible">openai_compatible</option>
            <option value="anthropic_compatible">anthropic_compatible</option>
          </select>
          <select
            aria-label="Provider plugin"
            className="text-input"
            name="plugin_identifier"
            defaultValue=""
          >
            <option value="">Select provider plugin</option>
            {modelProviderPlugins.map((plugin) => (
              <option key={plugin.identifier} value={plugin.identifier}>
                {plugin.identifier}
              </option>
            ))}
          </select>
          <input className="text-input" name="base_url" placeholder="https://api.example.test/v1" />
          <input className="text-input" name="model_name" placeholder="Model name" />
          <input className="text-input" name="api_key_ref" placeholder="api-key-ref" />
          <input className="text-input" name="timeout_seconds" placeholder="20" />
          <input className="text-input" name="retry_attempts" placeholder="1" />
          <input className="text-input" name="rate_limit_per_minute" placeholder="Rate limit" />
          <PluginConfigFields
            plugins={modelProviderPlugins}
            selectedIdentifier={modelProviderPlugins[0]?.identifier ?? ""}
            config={{}}
            textareaId="provider-create-plugin-config"
            textareaName="plugin_config"
          />
          <textarea className="text-input" name="capabilities" placeholder="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create provider profile
          </button>
        </form>
        <PluginHint plugins={modelProviderPlugins} />
      </section>

      <section className="management-panel" aria-labelledby="providers-title">
        <h2 className="section-title" id="providers-title">
          Provider profiles
        </h2>
        <div className="resource-list">
          {profiles.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No provider profiles yet</h3>
                <p>Create a non-secret provider profile and map its key in the runtime env.</p>
              </div>
            </article>
          ) : (
            profiles.map((profile) => (
              <article className="resource-row" key={profile.id}>
                <div>
                  <h3>{profile.name}</h3>
                  <ProviderHealthSummary health={healthByProfileId.get(profile.id)} />
                  <p>
                    {profile.profile_key} - {profile.provider_type} -{" "}
                    {profile.is_enabled ? "Enabled" : "Disabled"}
                  </p>
                  <p>Plugin: {profile.plugin_identifier}</p>
                  <p>
                    Test: {profile.last_test_status ?? "not run"}
                    {profile.last_test_error !== null ? ` - ${profile.last_test_error}` : ""}
                  </p>
                  <form
                    className="inline-form"
                    onSubmit={(event) => handleUpdateProfile(event, profile.id)}
                  >
                    <input className="text-input" name="name" defaultValue={profile.name} />
                    <select
                      aria-label={`Provider plugin ${profile.name}`}
                      className="text-input"
                      name="plugin_identifier"
                      defaultValue={profile.plugin_identifier}
                    >
                      {modelProviderPlugins.map((plugin) => (
                        <option key={plugin.identifier} value={plugin.identifier}>
                          {plugin.identifier}
                        </option>
                      ))}
                    </select>
                    <input className="text-input" name="base_url" defaultValue={profile.base_url} />
                    <input
                      className="text-input"
                      name="model_name"
                      defaultValue={profile.model_name}
                    />
                    <input
                      className="text-input"
                      name="api_key_ref"
                      defaultValue={profile.api_key_ref}
                    />
                    <input
                      className="text-input"
                      name="timeout_seconds"
                      defaultValue={profile.timeout_seconds}
                    />
                    <input
                      className="text-input"
                      name="retry_attempts"
                      defaultValue={profile.retry_attempts}
                    />
                    <input
                      className="text-input"
                      name="rate_limit_per_minute"
                      defaultValue={profile.rate_limit_per_minute ?? ""}
                    />
                    <PluginConfigFields
                      plugins={modelProviderPlugins}
                      selectedIdentifier={profile.plugin_identifier}
                      config={sanitizeProviderAdminJsonObject(profile.plugin_config)}
                      textareaId={`provider-${profile.id}-plugin-config`}
                      textareaName="plugin_config"
                    />
                    <textarea
                      className="text-input"
                      name="capabilities"
                      rows={3}
                      defaultValue={providerAdminJsonString(profile.capabilities)}
                    />
                    <label className="checkbox-label">
                      <input name="is_enabled" type="checkbox" defaultChecked={profile.is_enabled} />
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
                        onClick={() =>
                          runAction(() => testProviderProfile(profile.id), "Provider test passed.")
                        }
                      >
                        Test provider
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isBusy}
                        onClick={() =>
                          runAction(
                            () => disableProviderProfile(profile.id),
                            "Provider disabled.",
                          )
                        }
                      >
                        Disable provider
                      </button>
                    </div>
                  </form>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <PluginBindingIssues bindings={data.pluginBindings} diagnostics={data.pluginDiagnostics} />
    </section>
  );
}

function providerAdminJsonString(value: Record<string, unknown>): string {
  return JSON.stringify(sanitizeProviderAdminJsonObject(value), null, 2);
}

function providerAdminJsonObject(rawValue: string): Record<string, unknown> {
  return sanitizeProviderAdminJsonObject(jsonObject(rawValue));
}

function sanitizeProviderAdminJsonObject(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !sensitiveProviderAdminJsonKey(key))
      .map(([key, entry]) => [key, sanitizeProviderAdminJsonValue(entry)]),
  );
}

function sanitizeProviderAdminJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeProviderAdminJsonValue(entry));
  }
  if (value !== null && typeof value === "object") {
    return sanitizeProviderAdminJsonObject(value as Record<string, unknown>);
  }
  if (typeof value === "string" && looksSensitiveProviderAdminString(value)) {
    return "[redacted]";
  }
  return value;
}

const EXACT_SENSITIVE_PROVIDER_ADMIN_JSON_KEYS = new Set([
  "apikey",
  "authorization",
  "base64",
  "bearertoken",
  "bytes",
  "password",
  "secret",
  "token",
]);

const SENSITIVE_PROVIDER_ADMIN_JSON_KEY_MARKERS = [
  "accesstoken",
  "bearertoken",
  "clientsecret",
  "filesystempath",
  "filepath",
  "localmodelpath",
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

const SENSITIVE_PROVIDER_ADMIN_TEXT_MARKERS = [
  "accesstoken",
  "apikey",
  "authorization",
  "base64",
  "bearertoken",
  "bytes",
  "clientsecret",
  "filesystempath",
  "filepath",
  "localmodelpath",
  "objectpath",
  "objectstoragepath",
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

function sensitiveProviderAdminJsonKey(key: string): boolean {
  const normalized = normalizeProviderAdminMarker(key);
  return (
    EXACT_SENSITIVE_PROVIDER_ADMIN_JSON_KEYS.has(normalized) ||
    SENSITIVE_PROVIDER_ADMIN_JSON_KEY_MARKERS.some((marker) => normalized.includes(marker))
  );
}

function looksSensitiveProviderAdminString(value: string): boolean {
  const normalized = normalizeProviderAdminMarker(value);
  return (
    SENSITIVE_PROVIDER_ADMIN_TEXT_MARKERS.some((marker) => normalized.includes(marker)) ||
    /media:\/\/|\/var\/|\/tmp\/|\/models\/|[A-Za-z]:\\|sk-[A-Za-z0-9_-]+|Bearer\s+\S+/i.test(value) ||
    containsBase64LikeProviderAdminToken(value)
  );
}

function containsBase64LikeProviderAdminToken(value: string): boolean {
  return value
    .split(/\s+/)
    .some((part) => {
      const normalized = part.replace(/[^A-Za-z0-9+/=]/g, "");
      return (
        normalized.length >= 24 &&
        normalized.length % 4 === 0 &&
        /^[A-Za-z0-9+/]+={0,2}$/.test(normalized) &&
        !/^[a-f0-9]{32,}$/i.test(normalized)
      );
    });
}

function normalizeProviderAdminMarker(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function ProviderHealthSummary({
  health,
}: {
  health: ProviderAdminData["providerHealth"][number] | undefined;
}) {
  if (health === undefined) {
    return <p className="management-notice" data-tone="warning">Health is unknown. Run a provider test before relying on this profile.</p>;
  }
  const tone = providerHealthTone(health.health);
  return (
    <div className="dashboard-grid" aria-label={`${health.name} provider status`}>
      <div className="metric" data-tone={tone}>
        <p className="metric-label">Health</p>
        <p className="metric-value">{health.health}</p>
        <p className="status-detail">{providerHealthAction(health.health)}</p>
      </div>
      <div className="metric" data-tone={health.secret_ref_status === "configured" ? "ok" : "warning"}>
        <p className="metric-label">Secret ref</p>
        <p className="metric-value">{health.secret_ref_status}</p>
        <p className="status-detail">Reference: {health.api_key_ref}</p>
        {health.secret_ref_message !== null ? <p>{health.secret_ref_message}</p> : null}
      </div>
      <div className="metric">
        <p className="metric-label">Recent diagnostics</p>
        <p className="metric-value">{health.recent_diagnostic_count}</p>
      </div>
      <div className="metric" data-tone={health.recent_error_count > 0 ? "error" : "neutral"}>
        <p className="metric-label">Recent errors</p>
        <p className="metric-value">{health.recent_error_count}</p>
        <p className="status-detail">
          {health.recent_error_count > 0 ? "Review diagnostics before normal use." : "No recent provider errors."}
        </p>
      </div>
    </div>
  );
}

function providerHealthTone(
  health: ProviderAdminData["providerHealth"][number]["health"],
): "neutral" | "ok" | "warning" | "error" {
  if (health === "ok") {
    return "ok";
  }
  if (health === "configuration_error" || health === "disabled") {
    return "error";
  }
  if (health === "degraded") {
    return "warning";
  }
  return "neutral";
}

function providerHealthAction(health: ProviderAdminData["providerHealth"][number]["health"]): string {
  if (health === "ok") {
    return "Ready for configured capability checks.";
  }
  if (health === "degraded") {
    return "Use degraded mode or manual fallback policy before spend.";
  }
  if (health === "configuration_error") {
    return "Fix configuration before provider execution.";
  }
  if (health === "disabled") {
    return "Enable only after quota and auth checks are ready.";
  }
  return "Run a provider test to establish readiness.";
}

function PluginBindingIssues({
  bindings,
  diagnostics,
}: {
  bindings: PluginBinding[];
  diagnostics: ProviderAdminData["pluginDiagnostics"];
}) {
  const issueBindings = bindings.filter((binding) => binding.validation_status !== "ok");
  return (
    <section className="management-panel" aria-labelledby="plugin-bindings-title">
      <h2 className="section-title" id="plugin-bindings-title">
        Plugin bindings
      </h2>
      <p>
        {bindings.length} bindings inspected - {issueBindings.length} issues
      </p>
      <p>{diagnostics.length} recent plugin diagnostics</p>
      <div className="resource-list">
        {issueBindings.length === 0 ? (
          <article className="resource-row">
            <div>
              <h3>No plugin binding issues</h3>
              <p>Persisted plugin refs match the registry and expected categories.</p>
            </div>
          </article>
        ) : (
          issueBindings.map((binding) => (
            <article className="resource-row" key={`${binding.owner_kind}-${binding.owner_id}`}>
              <div>
                <h3>{binding.owner_key}</h3>
                <p>
                  {binding.owner_kind} - {binding.category} - {binding.plugin_identifier}
                </p>
                <p>
                  {binding.validation_status}
                  {binding.issue_message === null ? "" : ` - ${binding.issue_message}`}
                </p>
              </div>
            </article>
          ))
        )}
      </div>
      {diagnostics.length > 0 ? (
        <div className="resource-list">
          {diagnostics.map((diagnostic) => (
            <article className="resource-row" key={diagnostic.id}>
              <div>
                <h3>{diagnostic.event_type}</h3>
                <p>
                  {diagnostic.severity} - {diagnostic.message}
                </p>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function PluginHint({ plugins }: { plugins: PluginCatalogEntry[] }) {
  if (plugins.length === 0) {
    return <p>No provider plugins available.</p>;
  }

  return (
    <div className="resource-list">
      {plugins.map((plugin) => (
        <article className="resource-row" key={plugin.identifier}>
          <div>
            <h3>{plugin.identifier}</h3>
            <p>{plugin.capabilities.join(", ") || "No capabilities declared."}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
