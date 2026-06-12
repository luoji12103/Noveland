"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createAgentPreset,
  deactivateAgentPreset,
  getAgentPresetUpdatePreview,
  updateAgentPreset,
} from "@/lib/worlds/client";
import type { AgentPreset, AgentPresetUpdatePreview } from "@/lib/worlds/types";
import { formString, jsonObject, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type PresetAdminProps = {
  presets: AgentPreset[];
  loadError: string | null;
};

export function PresetAdmin({ presets, loadError }: PresetAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [preview, setPreview] = useState<AgentPresetUpdatePreview | null>(null);

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

  async function handleCreatePreset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(
      async () => {
        await createAgentPreset({
          preset_key: formString(form, "preset_key"),
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          default_kind: formString(form, "default_kind") as "role_agent" | "narrative_agent",
          default_provider_profile_key: optionalFormString(form, "default_provider_profile_key"),
          persona_text: formString(form, "persona_text"),
          behavior_policy: presetJsonObject(formString(form, "behavior_policy")),
          calendar_blueprint: presetCalendarBlueprint(formString(form, "calendar_blueprint")),
          advanced_config: presetJsonObject(formString(form, "advanced_config")),
        });
        formElement.reset();
      },
      "Preset created.",
    );
  }

  async function handleUpdatePreset(event: FormEvent<HTMLFormElement>, presetId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateAgentPreset(presetId, {
          preset_key: formString(form, "preset_key"),
          name: formString(form, "name"),
          description: optionalFormString(form, "description"),
          default_kind: formString(form, "default_kind") as "role_agent" | "narrative_agent",
          default_provider_profile_key: optionalFormString(form, "default_provider_profile_key"),
          persona_text: formString(form, "persona_text"),
          behavior_policy: presetJsonObject(formString(form, "behavior_policy")),
          calendar_blueprint: presetCalendarBlueprint(formString(form, "calendar_blueprint")),
          advanced_config: presetJsonObject(formString(form, "advanced_config")),
          is_active: form.get("is_active") === "on",
        }),
      "Preset saved.",
    );
  }

  async function handlePreviewPreset(presetId: string) {
    await runAction(async () => {
      setPreview(await getAgentPresetUpdatePreview(presetId));
    }, "Preset update preview loaded.");
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="management-panel" aria-labelledby="create-preset-title">
        <h2 className="section-title" id="create-preset-title">
          Create preset
        </h2>
        <form className="management-form" onSubmit={handleCreatePreset}>
          <input className="text-input" name="preset_key" placeholder="preset-key" />
          <input className="text-input" name="name" placeholder="Preset name" />
          <input className="text-input" name="description" placeholder="Description" />
          <select className="text-input" name="default_kind" defaultValue="role_agent">
            <option value="role_agent">role_agent</option>
            <option value="narrative_agent">narrative_agent</option>
          </select>
          <input
            className="text-input"
            name="default_provider_profile_key"
            placeholder="profile-key"
          />
          <textarea className="text-input" name="persona_text" rows={4} placeholder="Persona" />
          <textarea className="text-input" name="behavior_policy" rows={3} defaultValue="{}" />
          <textarea className="text-input" name="calendar_blueprint" rows={4} defaultValue="[]" />
          <textarea className="text-input" name="advanced_config" rows={4} defaultValue="{}" />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create preset
          </button>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="presets-title">
        <h2 className="section-title" id="presets-title">
          Agent presets
        </h2>
        <div className="resource-list">
          {presets.length === 0 ? (
            <article className="resource-row">
              <div>
                <h3>No presets yet</h3>
                <p>Create platform-managed presets for agent builders and world composition imports.</p>
              </div>
            </article>
          ) : (
            presets.map((preset) => (
              <article className="resource-row" key={preset.id}>
                <div>
                  <h3>{preset.name}</h3>
                  <p>
                    {preset.preset_key} - {preset.default_kind} - version {preset.version} -{" "}
                    {preset.is_active ? "Active" : "Inactive"}
                  </p>
                  <p>
                    Provider key: {preset.default_provider_profile_key ?? "none"} | Calendar entries: {preset.calendar_blueprint.length}
                  </p>
                  <form className="inline-form" onSubmit={(event) => handleUpdatePreset(event, preset.id)}>
                    <input className="text-input" name="preset_key" defaultValue={preset.preset_key} />
                    <input className="text-input" name="name" defaultValue={preset.name} />
                    <input
                      className="text-input"
                      name="description"
                      defaultValue={preset.description ?? ""}
                    />
                    <select className="text-input" name="default_kind" defaultValue={preset.default_kind}>
                      <option value="role_agent">role_agent</option>
                      <option value="narrative_agent">narrative_agent</option>
                    </select>
                    <input
                      className="text-input"
                      name="default_provider_profile_key"
                      defaultValue={preset.default_provider_profile_key ?? ""}
                    />
                    <textarea
                      className="text-input"
                      name="persona_text"
                      rows={4}
                      defaultValue={preset.persona_text}
                    />
                    <textarea
                      className="text-input"
                      name="behavior_policy"
                      rows={3}
                      defaultValue={presetJsonString(preset.behavior_policy)}
                    />
                    <textarea
                      className="text-input"
                      name="calendar_blueprint"
                      rows={4}
                      defaultValue={presetJsonString(preset.calendar_blueprint)}
                    />
                    <textarea
                      className="text-input"
                      name="advanced_config"
                      rows={4}
                      defaultValue={presetJsonString(preset.advanced_config)}
                    />
                    <label className="checkbox-label">
                      <input name="is_active" type="checkbox" defaultChecked={preset.is_active} />
                      Active
                    </label>
                    <div className="button-row">
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isBusy}
                        onClick={() => handlePreviewPreset(preset.id)}
                      >
                        Preview updates
                      </button>
                      <button className="primary-button" type="submit" disabled={isBusy}>
                        Save preset
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isBusy}
                        onClick={() =>
                          runAction(() => deactivateAgentPreset(preset.id), "Preset disabled.")
                        }
                      >
                        Disable preset
                      </button>
                    </div>
                  </form>
                  {preview?.preset_id === preset.id ? <PresetUpdatePreview preview={preview} /> : null}
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </section>
  );
}


function presetJsonString(value: unknown): string {
  return JSON.stringify(sanitizePresetJsonValue(value), null, 2);
}

function presetJsonObject(rawValue: string): Record<string, unknown> {
  return sanitizePresetJsonObject(jsonObject(rawValue));
}

function presetCalendarBlueprint(rawValue: string): AgentPreset["calendar_blueprint"] {
  return sanitizePresetJsonValue(JSON.parse(rawValue || "[]")) as AgentPreset["calendar_blueprint"];
}

function sanitizePresetJsonObject(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !sensitivePresetJsonKey(key))
      .map(([key, entry]) => [key, sanitizePresetJsonValue(entry)]),
  );
}

function sanitizePresetJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizePresetJsonValue(entry));
  }
  if (value !== null && typeof value === "object") {
    return sanitizePresetJsonObject(value as Record<string, unknown>);
  }
  if (typeof value === "string" && looksSensitivePresetString(value)) {
    return "[redacted]";
  }
  return value;
}

const EXACT_SENSITIVE_PRESET_JSON_KEYS = new Set([
  "apikey",
  "authorization",
  "base64",
  "bearertoken",
  "bytes",
  "password",
  "secret",
  "token",
]);

const SENSITIVE_PRESET_JSON_KEY_MARKERS = [
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

const SENSITIVE_PRESET_TEXT_MARKERS = [
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

function sensitivePresetJsonKey(key: string): boolean {
  const normalized = normalizePresetMarker(key);
  return (
    EXACT_SENSITIVE_PRESET_JSON_KEYS.has(normalized) ||
    SENSITIVE_PRESET_JSON_KEY_MARKERS.some((marker) => normalized.includes(marker))
  );
}

function looksSensitivePresetString(value: string): boolean {
  const normalized = normalizePresetMarker(value);
  return (
    SENSITIVE_PRESET_TEXT_MARKERS.some((marker) => normalized.includes(marker)) ||
    /media:\/\/|\/var\/|\/tmp\/|\/models\/|[A-Za-z]:\\|sk-[A-Za-z0-9_-]+|Bearer\s+\S+/i.test(value) ||
    containsBase64LikePresetToken(value)
  );
}

function containsBase64LikePresetToken(value: string): boolean {
  return value
    .split(/\s+/)
    .some((part) => {
      const normalized = part.replace(/[^A-Za-z0-9+/=]/g, "");
      return (
        normalized.length >= 16 &&
        normalized.length % 4 === 0 &&
        /^[A-Za-z0-9+/]+={0,2}$/.test(normalized) &&
        !/^[a-f0-9]{32,}$/i.test(normalized)
      );
    });
}

function normalizePresetMarker(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function PresetUpdatePreview({ preview }: { preview: AgentPresetUpdatePreview }) {
  return (
    <section aria-labelledby={`preset-preview-${preview.preset_id}`}>
      <h4 id={`preset-preview-${preview.preset_id}`}>Preset update preview</h4>
      <p>
        version {preview.current_version} - {preview.stale_agent_count} stale,{" "}
        {preview.current_agent_count} current, {preview.unversioned_agent_count} unversioned
      </p>
      <div className="resource-list">
        {preview.agents.length === 0 ? (
          <article className="resource-row">
            <div>
              <h3>No materialized agents</h3>
              <p>This preset has not been used to create agents yet.</p>
            </div>
          </article>
        ) : (
          preview.agents.map((agent) => (
            <article className="resource-row" key={agent.agent_id}>
              <div>
                <h3>{agent.display_name}</h3>
                <p>
                  {agent.agent_key} - {agent.status} - source version{" "}
                  {agent.source_preset_version ?? "none"}
                </p>
                <p>
                  Changed fields:{" "}
                  {agent.changed_fields.length === 0 ? "none" : agent.changed_fields.join(", ")}
                </p>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
