"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createAgentPreset,
  deactivateAgentPreset,
  updateAgentPreset,
} from "@/lib/worlds/client";
import type { AgentPreset } from "@/lib/worlds/types";
import { formString, jsonObject, messageForError, optionalFormString } from "@/features/workspace/form-utils";

type PresetAdminProps = {
  presets: AgentPreset[];
  loadError: string | null;
};

export function PresetAdmin({ presets, loadError }: PresetAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(loadError);
  const [isBusy, setIsBusy] = useState(false);

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
          behavior_policy: jsonObject(formString(form, "behavior_policy")),
          calendar_blueprint: JSON.parse(
            formString(form, "calendar_blueprint") || "[]",
          ) as AgentPreset["calendar_blueprint"],
          advanced_config: jsonObject(formString(form, "advanced_config")),
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
          behavior_policy: jsonObject(formString(form, "behavior_policy")),
          calendar_blueprint: JSON.parse(
            formString(form, "calendar_blueprint") || "[]",
          ) as AgentPreset["calendar_blueprint"],
          advanced_config: jsonObject(formString(form, "advanced_config")),
          is_active: form.get("is_active") === "on",
        }),
      "Preset saved.",
    );
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
                      defaultValue={JSON.stringify(preset.behavior_policy, null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="calendar_blueprint"
                      rows={4}
                      defaultValue={JSON.stringify(preset.calendar_blueprint, null, 2)}
                    />
                    <textarea
                      className="text-input"
                      name="advanced_config"
                      rows={4}
                      defaultValue={JSON.stringify(preset.advanced_config, null, 2)}
                    />
                    <label className="checkbox-label">
                      <input name="is_active" type="checkbox" defaultChecked={preset.is_active} />
                      Active
                    </label>
                    <div className="button-row">
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
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </section>
  );
}
