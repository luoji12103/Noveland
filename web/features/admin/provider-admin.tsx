"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createProviderProfile,
  disableProviderProfile,
  testProviderProfile,
  updateProviderProfile,
} from "@/lib/worlds/client";
import type { ProviderProfile } from "@/lib/worlds/types";
import {
  formString,
  jsonObject,
  messageForError,
  numberFormValue,
  optionalNumberFormValue,
} from "@/features/workspace/form-utils";

type ProviderAdminProps = {
  profiles: ProviderProfile[];
};

export function ProviderAdmin({ profiles }: ProviderAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(null);
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
          base_url: formString(form, "base_url"),
          model_name: formString(form, "model_name"),
          api_key_ref: formString(form, "api_key_ref"),
          capabilities: jsonObject(formString(form, "capabilities")),
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
          base_url: formString(form, "base_url"),
          model_name: formString(form, "model_name"),
          api_key_ref: formString(form, "api_key_ref"),
          capabilities: jsonObject(formString(form, "capabilities")),
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
          <input className="text-input" name="base_url" placeholder="https://api.example.test/v1" />
          <input className="text-input" name="model_name" placeholder="Model name" />
          <input className="text-input" name="api_key_ref" placeholder="api-key-ref" />
          <input className="text-input" name="timeout_seconds" placeholder="20" />
          <input className="text-input" name="retry_attempts" placeholder="1" />
          <input className="text-input" name="rate_limit_per_minute" placeholder="Rate limit" />
          <textarea className="text-input" name="capabilities" placeholder="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Create provider profile
          </button>
        </form>
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
                  <p>
                    {profile.profile_key} - {profile.provider_type} -{" "}
                    {profile.is_enabled ? "Enabled" : "Disabled"}
                  </p>
                  <p>
                    Test: {profile.last_test_status ?? "not run"}
                    {profile.last_test_error !== null ? ` - ${profile.last_test_error}` : ""}
                  </p>
                  <form
                    className="inline-form"
                    onSubmit={(event) => handleUpdateProfile(event, profile.id)}
                  >
                    <input className="text-input" name="name" defaultValue={profile.name} />
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
                    <textarea
                      className="text-input"
                      name="capabilities"
                      rows={3}
                      defaultValue={JSON.stringify(profile.capabilities, null, 2)}
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
    </section>
  );
}
