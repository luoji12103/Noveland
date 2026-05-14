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
import { mediaObjectDownloadPath } from "@/lib/worlds/media";
import {
  createAgentVoiceBinding,
  createStyleMapping,
  createVoiceProfile,
  deleteAgentVoiceBinding,
  deleteStyleMapping,
  deleteVoiceProfile,
  listAgentVoiceBindings,
  listTranscripts,
  listVoiceProfiles,
  runSTT,
  runTTS,
  speechVisibilityOptions,
  updateStyleMapping,
  updateVoiceProfile,
  voiceBindingRoleOptions,
  voiceConsentStatusOptions,
  voiceKindOptions,
  voiceProfileOwnerKindOptions,
  voiceProfileStatusOptions,
} from "@/lib/worlds/speech";
import type {
  AgentVoiceProfileBinding,
  SpeechStyleMapping,
  SpeechTranscript,
  SpeechVisibility,
  STTResult,
  TTSResult,
  VoiceConsentStatus,
  VoiceKind,
  VoiceProfile,
  VoiceProfileOwnerKind,
  VoiceProfileStatus,
} from "@/lib/worlds/speech";
import type { MediaAsset } from "@/lib/worlds/media";
import type { ProviderIntegration } from "@/lib/worlds/provider-integrations";
import type { SpeechAdminData } from "@/lib/worlds/server";

type SpeechAdminProps = {
  worldId: string;
  data: SpeechAdminData;
};

export function SpeechAdmin({ worldId, data }: SpeechAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [selectedWorldlineId, setSelectedWorldlineId] = useState(data.selectedWorldlineId ?? "");
  const [voiceProfiles, setVoiceProfiles] = useState(data.voiceProfiles);
  const [bindingsByAgentId, setBindingsByAgentId] = useState(data.bindingsByAgentId);
  const [styleMappings, setStyleMappings] = useState(data.styleMappings);
  const [transcripts, setTranscripts] = useState(data.transcripts);
  const [selectedVoiceProfileId, setSelectedVoiceProfileId] = useState(data.voiceProfiles[0]?.id ?? null);
  const [ttsResult, setTtsResult] = useState<TTSResult | null>(null);
  const [sttResult, setSttResult] = useState<STTResult | null>(null);
  const selectedVoiceProfile = useMemo(
    () => voiceProfiles.find((profile) => profile.id === selectedVoiceProfileId) ?? null,
    [voiceProfiles, selectedVoiceProfileId],
  );
  const allBindings = Object.values(bindingsByAgentId).flat();
  const ttsProviders = data.providers.filter((provider) => provider.provider_kind === "text_to_speech");
  const sttProviders = data.providers.filter((provider) => provider.provider_kind === "speech_to_text");
  const voiceProviders = data.providers.filter((provider) =>
    ["text_to_speech", "voice_cloning"].includes(provider.provider_kind),
  );
  const audioAssets = data.audioAssets.filter(
    (asset) => selectedWorldlineId === "" || asset.worldline_id === selectedWorldlineId,
  );
  const voiceReferenceAssets = audioAssets.filter((asset) =>
    ["voice_file", "voice_sample", "transcript_audio", "speech_audio"].includes(asset.asset_role),
  );
  const restrictedCount = voiceProfiles.filter((profile) => restrictedVisibility(profile.visibility)).length
    + transcripts.filter((transcript) => restrictedVisibility(transcript.visibility)).length;

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

  async function handleLoadWorldline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const worldlineId = formString(form, "worldline_id");
    await runAction(async () => {
      const nextProfiles = await listVoiceProfiles(worldId, optionalWorldlineFilter(worldlineId));
      const nextTranscripts = await listTranscripts(worldId, optionalWorldlineFilter(worldlineId));
      const nextBindings = await loadBindings(worldId, data.agents, worldlineId);
      setSelectedWorldlineId(worldlineId);
      setVoiceProfiles(nextProfiles);
      setTranscripts(nextTranscripts);
      setBindingsByAgentId(nextBindings);
      setSelectedVoiceProfileId(nextProfiles[0]?.id ?? null);
      setTtsResult(null);
      setSttResult(null);
    }, "Speech records loaded for worldline.");
  }

  async function handleCreateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      const profile = await createVoiceProfile(worldId, {
        worldline_id: optionalFormString(form, "worldline_id"),
        profile_key: formString(form, "profile_key"),
        display_name: formString(form, "display_name"),
        description: optionalFormString(form, "description"),
        status: formString(form, "status") as VoiceProfileStatus,
        visibility: formString(form, "visibility") as SpeechVisibility,
        owner_kind: formString(form, "owner_kind") as VoiceProfileOwnerKind,
        owner_agent_id: optionalFormString(form, "owner_agent_id"),
        provider_integration_id: optionalFormString(form, "provider_integration_id"),
        provider_voice_id: optionalFormString(form, "provider_voice_id"),
        default_language: optionalFormString(form, "default_language"),
        supported_languages: csvList(formString(form, "supported_languages")),
        voice_kind: formString(form, "voice_kind") as VoiceKind,
        reference_asset_id: optionalFormString(form, "reference_asset_id"),
        consent_status: formString(form, "consent_status") as VoiceConsentStatus,
        usage_policy_json: sanitizeJsonForDisplay(jsonObject(formString(form, "usage_policy_json"))),
        metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
      });
      setSelectedVoiceProfileId(profile.id);
      formElement.reset();
    }, "Voice profile created.");
  }

  async function handleUpdateProfile(event: FormEvent<HTMLFormElement>, profileId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateVoiceProfile(worldId, profileId, {
          display_name: formString(form, "display_name"),
          description: optionalFormString(form, "description"),
          status: formString(form, "status") as VoiceProfileStatus,
          visibility: formString(form, "visibility") as SpeechVisibility,
          provider_integration_id: optionalFormString(form, "provider_integration_id"),
          provider_voice_id: optionalFormString(form, "provider_voice_id"),
          default_language: optionalFormString(form, "default_language"),
          supported_languages: csvList(formString(form, "supported_languages")),
          reference_asset_id: optionalFormString(form, "reference_asset_id"),
          consent_status: formString(form, "consent_status") as VoiceConsentStatus,
          usage_policy_json: sanitizeJsonForDisplay(jsonObject(formString(form, "usage_policy_json"))),
          metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
        }),
      "Voice profile saved.",
    );
  }

  async function handleCreateBinding(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const agentId = formString(form, "agent_id");
    await runAction(async () => {
      await createAgentVoiceBinding(worldId, agentId, {
        worldline_id: optionalFormString(form, "worldline_id"),
        voice_profile_id: formString(form, "voice_profile_id"),
        binding_role: formString(form, "binding_role") as AgentVoiceProfileBinding["binding_role"],
        priority: numberField(form, "priority", 100),
        is_default: checkbox(form, "is_default"),
        style_overrides_json: sanitizeJsonForDisplay(jsonObject(formString(form, "style_overrides_json"))),
      });
      formElement.reset();
    }, "Agent voice binding created.");
  }

  async function handleCreateStyleMapping(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      await createStyleMapping(worldId, {
        mapping_key: formString(form, "mapping_key"),
        provider_kind: formString(form, "provider_kind"),
        emotion_key: formString(form, "emotion_key"),
        style_json: sanitizeJsonForDisplay(jsonObject(formString(form, "style_json"))),
      });
      formElement.reset();
    }, "Speech style mapping created.");
  }

  async function handleUpdateStyleMapping(event: FormEvent<HTMLFormElement>, mappingId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateStyleMapping(worldId, mappingId, {
          style_json: sanitizeJsonForDisplay(jsonObject(formString(form, "style_json"))),
        }),
      "Speech style mapping saved.",
    );
  }

  async function handleTranscriptFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setTranscripts(
        await listTranscripts(worldId, {
          worldline_id: optionalFormString(form, "worldline_id") ?? undefined,
          source_asset_id: optionalFormString(form, "source_asset_id") ?? undefined,
        }),
      );
    }, "Transcript filters applied.");
  }

  async function handleTTS(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setTtsResult(
        await runTTS(worldId, {
          worldline_id: optionalFormString(form, "worldline_id"),
          provider_id: formString(form, "provider_id"),
          voice_profile_id: optionalFormString(form, "voice_profile_id"),
          agent_id: optionalFormString(form, "agent_id"),
          allow_provider_default_voice: checkbox(form, "allow_provider_default_voice"),
          text: formString(form, "text"),
          language: optionalFormString(form, "language"),
          emotion: optionalFormString(form, "emotion"),
          intensity: optionalNumber(form, "intensity"),
          style_overrides_json: sanitizeJsonForDisplay(jsonObject(formString(form, "style_overrides_json"))),
          output_format: formString(form, "output_format"),
        }),
      );
    }, "TTS test completed.");
  }

  async function handleSTT(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setSttResult(
        await runSTT(worldId, {
          worldline_id: optionalFormString(form, "worldline_id"),
          provider_id: formString(form, "provider_id"),
          source_asset_id: formString(form, "source_asset_id"),
          language: optionalFormString(form, "language"),
          diarization: checkbox(form, "diarization"),
          timestamps: checkbox(form, "timestamps"),
          speaker_actor_ref: optionalFormString(form, "speaker_actor_ref"),
        }),
      );
    }, "STT test completed.");
  }

  return (
    <section className="management-section">
      {notice !== null ? <AdminNotice>{notice}</AdminNotice> : null}

      {!data.canManageSelectedWorld ? (
        <AdminNotice tone="error">Speech administration requires world admin access.</AdminNotice>
      ) : null}

      <AdminSection
        title="Speech overview"
        description="Voice profiles, bindings, transcripts, and test calls stay behind admin APIs."
      >
        <div className="dashboard-grid">
          <AdminMetric label="Voice profiles" value={voiceProfiles.length} />
          <AdminMetric label="Bindings" value={allBindings.length} />
          <AdminMetric label="Style mappings" value={styleMappings.length} />
          <AdminMetric label="Transcripts" value={transcripts.length} />
          <AdminMetric
            label="Restricted"
            value={restrictedCount}
            tone={restrictedCount > 0 ? "warning" : "neutral"}
          />
        </div>
      </AdminSection>

      <AdminSection
        title="Worldline scope"
        description="Speech records may be worldline-scoped. Use the selected worldline for filtered admin operations."
      >
        {data.worldlines.length === 0 ? (
          <AdminState title="No worldlines">Create or load a worldline before testing speech flows.</AdminState>
        ) : (
          <form className="inline-form" onSubmit={handleLoadWorldline}>
            <select
              className="text-input"
              name="worldline_id"
              value={selectedWorldlineId}
              onChange={(event) => setSelectedWorldlineId(event.target.value)}
            >
              {data.worldlines.map((worldline) => (
                <option key={worldline.id} value={worldline.id}>
                  {worldline.name} ({worldline.worldline_key})
                </option>
              ))}
            </select>
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Load speech records
            </button>
          </form>
        )}
      </AdminSection>

      <AdminSection title="Create voice profile">
        <form className="management-form" onSubmit={handleCreateProfile}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <input className="text-input" name="profile_key" placeholder="profile key" />
          <input className="text-input" name="display_name" placeholder="Display name" />
          <input className="text-input" name="description" placeholder="Description" />
          <select className="text-input" name="owner_kind" defaultValue="world">
            {voiceProfileOwnerKindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <AgentSelect agents={data.agents} name="owner_agent_id" optional />
          <ProviderSelect providers={voiceProviders} name="provider_integration_id" optional />
          <input className="text-input" name="provider_voice_id" placeholder="provider voice id" />
          <input className="text-input" name="default_language" placeholder="language" defaultValue="ja" />
          <input className="text-input" name="supported_languages" placeholder="supported languages" defaultValue="ja,en" />
          <select className="text-input" name="voice_kind" defaultValue="preset">
            {voiceKindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <AssetSelect assets={voiceReferenceAssets} name="reference_asset_id" fallbackLabel="reference asset id" optional />
          <select className="text-input" name="consent_status" defaultValue="not_required">
            {voiceConsentStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select className="text-input" name="status" defaultValue="active">
            {voiceProfileStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <VisibilitySelect isPlatformAdmin={data.isPlatformAdmin} />
          <textarea className="text-input" name="usage_policy_json" defaultValue="{}" rows={3} />
          <textarea className="text-input" name="metadata_json" defaultValue="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Create voice profile
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Voice profiles">
        <div className="resource-list">
          {voiceProfiles.length === 0 ? (
            <AdminState title="No voice profiles">
              Create a profile or bind an agent to a provider default voice for explicit TTS tests.
            </AdminState>
          ) : (
            voiceProfiles.map((profile) => (
              <VoiceProfileRow
                key={profile.id}
                profile={profile}
                bindingCount={allBindings.filter((binding) => binding.voice_profile_id === profile.id).length}
                isSelected={profile.id === selectedVoiceProfileId}
                onSelect={() => setSelectedVoiceProfileId(profile.id)}
              />
            ))
          )}
        </div>
      </AdminSection>

      {selectedVoiceProfile === null ? null : (
        <VoiceProfileDetail
          profile={selectedVoiceProfile}
          providers={voiceProviders}
          agents={data.agents}
          assets={voiceReferenceAssets}
          isBusy={isBusy}
          isPlatformAdmin={data.isPlatformAdmin}
          onUpdate={(event) => handleUpdateProfile(event, selectedVoiceProfile.id)}
          onDelete={() =>
            runAction(
              () => deleteVoiceProfile(worldId, selectedVoiceProfile.id),
              "Voice profile deleted.",
            )
          }
        />
      )}

      <AdminSection title="Agent voice bindings">
        <form className="management-form" onSubmit={handleCreateBinding}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <AgentSelect agents={data.agents} name="agent_id" />
          <VoiceProfileSelect profiles={voiceProfiles} name="voice_profile_id" />
          <select className="text-input" name="binding_role" defaultValue="default">
            {voiceBindingRoleOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <input className="text-input" name="priority" type="number" defaultValue="100" min="0" />
          <label className="checkbox-row">
            <input name="is_default" type="checkbox" /> default
          </label>
          <textarea className="text-input" name="style_overrides_json" defaultValue="{}" rows={3} />
          <button className="secondary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Bind voice profile
          </button>
        </form>
        <AdminTable
          caption="Agent voice bindings"
          rows={allBindings}
          getRowKey={(binding) => binding.id}
          columns={[
            { key: "agent", header: "Agent", render: (binding) => agentLabel(data, binding.agent_id) },
            { key: "profile", header: "Profile", render: (binding) => profileLabel(voiceProfiles, binding.voice_profile_id) },
            { key: "role", header: "Role", render: (binding) => binding.binding_role },
            { key: "default", header: "Default", render: (binding) => (binding.is_default ? "yes" : "no") },
            { key: "style", header: "Style keys", render: (binding) => safeJsonSummary(binding.style_overrides_json) },
            {
              key: "action",
              header: "Action",
              render: (binding) => (
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isBusy}
                  onClick={() =>
                    runAction(
                      () => deleteAgentVoiceBinding(worldId, binding.agent_id, binding.id),
                      "Agent voice binding deleted.",
                    )
                  }
                >
                  Delete
                </button>
              ),
            },
          ]}
          emptyTitle="No agent voice bindings"
          emptyMessage="Bind an agent to a voice profile before relying on agent-default TTS."
        />
      </AdminSection>

      <AdminSection title="Speech style mappings">
        <form className="management-form" onSubmit={handleCreateStyleMapping}>
          <input className="text-input" name="mapping_key" placeholder="mapping key" />
          <input className="text-input" name="provider_kind" placeholder="provider kind" defaultValue="openai" />
          <input className="text-input" name="emotion_key" placeholder="emotion" defaultValue="neutral" />
          <textarea className="text-input" name="style_json" defaultValue='{"voice":"alloy"}' rows={3} />
          <button className="secondary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Create style mapping
          </button>
        </form>
        <AdminTable
          caption="Speech style mappings"
          rows={styleMappings}
          getRowKey={(mapping) => mapping.id}
          columns={[
            { key: "key", header: "Key", render: (mapping) => mapping.mapping_key },
            { key: "provider", header: "Provider", render: (mapping) => mapping.provider_kind },
            { key: "emotion", header: "Emotion", render: (mapping) => mapping.emotion_key },
            { key: "style", header: "Style keys", render: (mapping) => safeJsonSummary(mapping.style_json) },
            {
              key: "actions",
              header: "Actions",
              render: (mapping) => (
                <StyleMappingActions
                  mapping={mapping}
                  isBusy={isBusy}
                  onUpdate={(event) => handleUpdateStyleMapping(event, mapping.id)}
                  onDelete={() =>
                    runAction(
                      () => deleteStyleMapping(worldId, mapping.id),
                      "Speech style mapping deleted.",
                    )
                  }
                />
              ),
            },
          ]}
          emptyTitle="No style mappings"
          emptyMessage="Style mappings translate emotion tags into provider-specific speech parameters."
        />
      </AdminSection>

      <AdminSection
        title="Transcript browser"
        description="STT writes transcripts only. It does not mutate turn text or enqueue memory writes."
      >
        <form className="inline-form" onSubmit={handleTranscriptFilter}>
          <input className="text-input" name="worldline_id" defaultValue={selectedWorldlineId} placeholder="worldline id" />
          <AssetSelect assets={audioAssets} name="source_asset_id" fallbackLabel="source asset id" optional />
          <button className="secondary-button" type="submit" disabled={isBusy}>
            Apply transcript filters
          </button>
        </form>
        <AdminTable
          caption="Speech transcripts"
          rows={transcripts}
          getRowKey={(transcript) => transcript.id}
          columns={[
            { key: "asset", header: "Source", render: (transcript) => shortId(transcript.source_asset_id) },
            { key: "language", header: "Language", render: (transcript) => transcript.language ?? "-" },
            { key: "status", header: "Status", render: (transcript) => `${transcript.status} / ${transcript.visibility}` },
            { key: "text", header: "Transcript", render: (transcript) => truncate(transcript.transcript_text, 120) },
            { key: "invocation", header: "Invocation", render: (transcript) => transcript.model_invocation_id === null ? "-" : shortId(transcript.model_invocation_id) },
          ]}
          emptyTitle="No transcripts"
          emptyMessage="Run an explicit STT test or backend transcription flow to create transcripts."
        />
      </AdminSection>

      <AdminSection title="TTS test action">
        <form className="management-form" onSubmit={handleTTS}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <ProviderSelect providers={ttsProviders} name="provider_id" />
          <VoiceProfileSelect profiles={voiceProfiles} name="voice_profile_id" optional />
          <AgentSelect agents={data.agents} name="agent_id" optional />
          <label className="checkbox-row">
            <input name="allow_provider_default_voice" type="checkbox" /> allow provider default voice
          </label>
          <textarea className="text-input" name="text" defaultValue="Admin speech smoke test." rows={3} />
          <input className="text-input" name="language" placeholder="language" defaultValue="ja" />
          <input className="text-input" name="emotion" placeholder="emotion" defaultValue="neutral" />
          <input className="text-input" name="intensity" type="number" min="0" max="2" step="0.1" />
          <input className="text-input" name="output_format" defaultValue="wav" />
          <textarea className="text-input" name="style_overrides_json" defaultValue="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Run TTS test
          </button>
        </form>
        <TTSResultView worldId={worldId} result={ttsResult} />
      </AdminSection>

      <AdminSection title="STT test action">
        <form className="management-form" onSubmit={handleSTT}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <ProviderSelect providers={sttProviders} name="provider_id" />
          <AssetSelect assets={audioAssets} name="source_asset_id" fallbackLabel="source audio asset id" />
          <input className="text-input" name="language" placeholder="language" />
          <input className="text-input" name="speaker_actor_ref" placeholder="speaker actor ref" />
          <label className="checkbox-row">
            <input name="diarization" type="checkbox" /> diarization
          </label>
          <label className="checkbox-row">
            <input name="timestamps" type="checkbox" /> timestamps
          </label>
          <button className="primary-button" type="submit" disabled={isBusy || !data.canManageSelectedWorld}>
            Run STT test
          </button>
        </form>
        <STTResultView result={sttResult} />
      </AdminSection>
    </section>
  );
}

function VoiceProfileRow({
  profile,
  bindingCount,
  isSelected,
  onSelect,
}: {
  profile: VoiceProfile;
  bindingCount: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <article className="resource-row" data-selected={isSelected ? "true" : "false"}>
      <div>
        <h3>{profile.display_name}</h3>
        <p>
          {profile.profile_key} - {profile.voice_kind} - {profile.status} - {profile.visibility}
        </p>
        <p>
          Worldline {profile.worldline_id === null ? "global" : shortId(profile.worldline_id)} / bindings {bindingCount} /
          provider voice {profile.provider_voice_id ?? "none"}
        </p>
      </div>
      <button className="secondary-button" type="button" onClick={onSelect}>
        {isSelected ? "Selected" : "Inspect"}
      </button>
    </article>
  );
}

function VoiceProfileDetail({
  profile,
  providers,
  agents,
  assets,
  isBusy,
  isPlatformAdmin,
  onUpdate,
  onDelete,
}: {
  profile: VoiceProfile;
  providers: ProviderIntegration[];
  agents: SpeechAdminData["agents"];
  assets: MediaAsset[];
  isBusy: boolean;
  isPlatformAdmin: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
}) {
  return (
    <AdminSection
      title="Voice profile detail"
      description="Voice profiles reference providers and media assets by ID. Provider secrets remain behind auth_ref."
      actions={
        <button className="secondary-button" type="button" disabled={isBusy} onClick={onDelete}>
          Delete voice profile
        </button>
      }
    >
      <AdminDescriptionList
        items={[
          { label: "Profile", value: profile.id },
          { label: "Worldline", value: profile.worldline_id ?? "global" },
          { label: "Provider", value: profile.provider_integration_id ?? "-" },
          { label: "Reference asset", value: profile.reference_asset_id ?? "-" },
          { label: "Usage keys", value: safeJsonSummary(profile.usage_policy_json) },
          { label: "Metadata keys", value: safeJsonSummary(profile.metadata_json) },
        ]}
      />
      {restrictedVisibility(profile.visibility) ? (
        <AdminNotice tone="warning">
          This voice profile uses restricted visibility. Backend ACLs decide whether it is returned.
        </AdminNotice>
      ) : null}
      <form className="inline-form" onSubmit={onUpdate}>
        <input className="text-input" name="display_name" defaultValue={profile.display_name} />
        <input className="text-input" name="description" defaultValue={profile.description ?? ""} />
        <ProviderSelect providers={providers} name="provider_integration_id" defaultValue={profile.provider_integration_id ?? ""} optional />
        <input className="text-input" name="provider_voice_id" defaultValue={profile.provider_voice_id ?? ""} />
        <input className="text-input" name="default_language" defaultValue={profile.default_language ?? ""} />
        <input className="text-input" name="supported_languages" defaultValue={profile.supported_languages.join(",")} />
        <AssetSelect assets={assets} name="reference_asset_id" fallbackLabel="reference asset id" defaultValue={profile.reference_asset_id ?? ""} optional />
        <select className="text-input" name="consent_status" defaultValue={profile.consent_status}>
          {voiceConsentStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select className="text-input" name="status" defaultValue={profile.status}>
          {voiceProfileStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <VisibilitySelect isPlatformAdmin={isPlatformAdmin} defaultValue={profile.visibility} />
        <textarea
          className="text-input"
          name="usage_policy_json"
          rows={3}
          defaultValue={JSON.stringify(sanitizeJsonForDisplay(profile.usage_policy_json), null, 2)}
        />
        <textarea
          className="text-input"
          name="metadata_json"
          rows={3}
          defaultValue={JSON.stringify(sanitizeJsonForDisplay(profile.metadata_json), null, 2)}
        />
        <button className="primary-button" type="submit" disabled={isBusy}>
          Save voice profile
        </button>
      </form>
      <p className="status-detail">Owner agent: {profile.owner_agent_id === null ? "-" : agentLabel({ agents } as SpeechAdminData, profile.owner_agent_id)}</p>
    </AdminSection>
  );
}

function StyleMappingActions({
  mapping,
  isBusy,
  onUpdate,
  onDelete,
}: {
  mapping: SpeechStyleMapping;
  isBusy: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
}) {
  return (
    <form className="inline-form" onSubmit={onUpdate}>
      <textarea
        className="text-input"
        name="style_json"
        rows={2}
        defaultValue={JSON.stringify(sanitizeJsonForDisplay(mapping.style_json), null, 2)}
      />
      <AdminActionBar>
        <button className="secondary-button" type="submit" disabled={isBusy}>
          Save style
        </button>
        <button className="secondary-button" type="button" disabled={isBusy} onClick={onDelete}>
          Delete
        </button>
      </AdminActionBar>
    </form>
  );
}

function TTSResultView({ worldId, result }: { worldId: string; result: TTSResult | null }) {
  if (result === null) {
    return null;
  }
  return (
    <AdminDescriptionList
      items={[
        { label: "Output asset", value: result.output_asset.id },
        { label: "Media job", value: `${result.media_job.id} (${result.media_job.status})` },
        { label: "Invocation", value: result.model_invocation_id },
        { label: "Checksum", value: result.output_asset.checksum_sha256 ?? "pending" },
        {
          label: "Downloads",
          value:
            result.output_objects.length === 0
              ? "none"
              : result.output_objects.map((object) => (
                  <a key={object.id} className="secondary-button" href={mediaObjectDownloadPath(worldId, object.id)}>
                    {shortId(object.id)}
                  </a>
                )),
        },
      ]}
    />
  );
}

function STTResultView({ result }: { result: STTResult | null }) {
  if (result === null) {
    return null;
  }
  return (
    <AdminDescriptionList
      items={[
        { label: "Transcript", value: result.transcript.id },
        { label: "Transcript text", value: truncate(result.transcript.transcript_text, 180) },
        { label: "Media job", value: `${result.media_job.id} (${result.media_job.status})` },
        { label: "Invocation", value: result.model_invocation_id },
        { label: "Memory write", value: "not automatic" },
      ]}
    />
  );
}

function ProviderSelect({
  providers,
  name,
  defaultValue,
  optional = false,
}: {
  providers: ProviderIntegration[];
  name: string;
  defaultValue?: string;
  optional?: boolean;
}) {
  if (providers.length === 0) {
    return <input className="text-input" name={name} placeholder="provider id" defaultValue={defaultValue ?? ""} />;
  }
  return (
    <select className="text-input" name={name} defaultValue={defaultValue ?? (optional ? "" : providers[0].id)}>
      {optional ? <option value="">provider optional</option> : null}
      {providers.map((provider) => (
        <option key={provider.id} value={provider.id}>
          {provider.display_name} ({provider.provider_kind})
        </option>
      ))}
    </select>
  );
}

function AgentSelect({
  agents,
  name,
  optional = false,
}: {
  agents: SpeechAdminData["agents"];
  name: string;
  optional?: boolean;
}) {
  if (agents.length === 0) {
    return <input className="text-input" name={name} placeholder="agent id" />;
  }
  return (
    <select className="text-input" name={name} defaultValue={optional ? "" : agents[0].id}>
      {optional ? <option value="">agent optional</option> : null}
      {agents.map((agent) => (
        <option key={agent.id} value={agent.id}>
          {agent.display_name} ({agent.agent_key})
        </option>
      ))}
    </select>
  );
}

function VoiceProfileSelect({
  profiles,
  name,
  optional = false,
}: {
  profiles: VoiceProfile[];
  name: string;
  optional?: boolean;
}) {
  if (profiles.length === 0) {
    return <input className="text-input" name={name} placeholder="voice profile id" />;
  }
  return (
    <select className="text-input" name={name} defaultValue={optional ? "" : profiles[0].id}>
      {optional ? <option value="">voice profile optional</option> : null}
      {profiles.map((profile) => (
        <option key={profile.id} value={profile.id}>
          {profile.display_name} ({profile.profile_key})
        </option>
      ))}
    </select>
  );
}

function AssetSelect({
  assets,
  name,
  fallbackLabel,
  defaultValue,
  optional = false,
}: {
  assets: MediaAsset[];
  name: string;
  fallbackLabel: string;
  defaultValue?: string;
  optional?: boolean;
}) {
  if (assets.length === 0) {
    return <input className="text-input" name={name} placeholder={fallbackLabel} defaultValue={defaultValue ?? ""} />;
  }
  return (
    <select className="text-input" name={name} defaultValue={defaultValue ?? (optional ? "" : assets[0].id)}>
      {optional ? <option value="">asset optional</option> : null}
      {assets.map((asset) => (
        <option key={asset.id} value={asset.id}>
          {asset.title ?? asset.asset_role} ({shortId(asset.id)})
        </option>
      ))}
    </select>
  );
}

function VisibilitySelect({
  isPlatformAdmin,
  defaultValue = "world_admin",
}: {
  isPlatformAdmin: boolean;
  defaultValue?: SpeechVisibility;
}) {
  const options = isPlatformAdmin
    ? speechVisibilityOptions
    : speechVisibilityOptions.filter((value) => !restrictedVisibility(value));
  return (
    <select className="text-input" name="visibility" defaultValue={defaultValue}>
      {options.map((value) => (
        <option key={value} value={value}>
          {value}
        </option>
      ))}
    </select>
  );
}

function HiddenWorldlineInput({ value }: { value: string }) {
  return <input name="worldline_id" type="hidden" value={value} readOnly />;
}

async function loadBindings(
  worldId: string,
  agents: SpeechAdminData["agents"],
  worldlineId: string,
) {
  const entries = await Promise.all(
    agents.map(async (agent) => [
      agent.id,
      await listAgentVoiceBindings(worldId, agent.id, optionalWorldlineFilter(worldlineId)),
    ] as const),
  );
  return Object.fromEntries(entries);
}

function optionalWorldlineFilter(worldlineId: string): { worldline_id?: string } {
  return worldlineId === "" ? {} : { worldline_id: worldlineId };
}

function agentLabel(data: Pick<SpeechAdminData, "agents">, agentId: string): string {
  const agent = data.agents.find((item) => item.id === agentId);
  return agent === undefined ? shortId(agentId) : `${agent.display_name} (${agent.agent_key})`;
}

function profileLabel(profiles: VoiceProfile[], profileId: string): string {
  const profile = profiles.find((item) => item.id === profileId);
  return profile === undefined ? shortId(profileId) : `${profile.display_name} (${profile.profile_key})`;
}

function csvList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function numberField(form: FormData, key: string, fallback: number): number {
  const value = optionalFormString(form, key);
  if (value === null) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function optionalNumber(form: FormData, key: string): number | null {
  const value = optionalFormString(form, key);
  if (value === null) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function checkbox(form: FormData, key: string): boolean {
  return form.get(key) === "on";
}

function restrictedVisibility(value: SpeechVisibility): boolean {
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

function truncate(value: string, length: number): string {
  return value.length <= length ? value : `${value.slice(0, length - 3)}...`;
}

function shortId(value: string): string {
  return value.length <= 12 ? value : `${value.slice(0, 8)}...${value.slice(-4)}`;
}
