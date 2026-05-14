import { adminRequest } from "@/lib/admin/api-client";
import type { MediaAsset, MediaJob, MediaObject } from "@/lib/worlds/media";

export type VoiceProfileStatus = "active" | "disabled" | "deleted";
export type SpeechVisibility = "private" | "world_admin" | "world_member" | "developer_only" | "hidden";
export type VoiceProfileOwnerKind = "world" | "agent" | "user" | "provider" | "other";
export type VoiceKind = "preset" | "cloned" | "designed" | "imported" | "generated" | "external_provider" | "other";
export type VoiceConsentStatus =
  | "not_required"
  | "user_owned_or_authorized"
  | "admin_authorized"
  | "pending_review"
  | "restricted"
  | "unknown";
export type VoiceBindingRole =
  | "default"
  | "narration"
  | "inner_voice"
  | "phone_call"
  | "disguise"
  | "alternate"
  | "other";
export type SpeechTranscriptStatus = "available" | "failed" | "deleted";

export type VoiceProfile = {
  id: string;
  world_id: string;
  worldline_id: string | null;
  profile_key: string;
  display_name: string;
  description: string | null;
  status: VoiceProfileStatus;
  visibility: SpeechVisibility;
  owner_kind: VoiceProfileOwnerKind;
  owner_agent_id: string | null;
  provider_integration_id: string | null;
  provider_voice_id: string | null;
  default_language: string | null;
  supported_languages: string[];
  voice_kind: VoiceKind;
  reference_asset_id: string | null;
  consent_status: VoiceConsentStatus;
  usage_policy_json: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AgentVoiceProfileBinding = {
  id: string;
  world_id: string;
  worldline_id: string | null;
  agent_id: string;
  voice_profile_id: string;
  binding_role: VoiceBindingRole;
  priority: number;
  is_default: boolean;
  style_overrides_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SpeechStyleMapping = {
  id: string;
  world_id: string;
  mapping_key: string;
  provider_kind: string;
  emotion_key: string;
  style_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SpeechTranscript = {
  id: string;
  world_id: string;
  worldline_id: string;
  source_asset_id: string;
  media_job_id: string | null;
  model_invocation_id: string | null;
  conversation_id: string | null;
  turn_id: string | null;
  speaker_actor_ref: string | null;
  language: string | null;
  transcript_text: string;
  segments_json: Array<Record<string, unknown>> | null;
  confidence_json: Record<string, unknown> | null;
  status: SpeechTranscriptStatus;
  visibility: SpeechVisibility;
  created_at: string;
  updated_at: string;
};

export type InvocationRef = {
  id: string;
  status: string;
  latency_ms?: number | null;
  request_params_json?: Record<string, unknown>;
  response_metadata_json?: Record<string, unknown>;
};

export type VoiceProfileInput = {
  worldline_id?: string | null;
  profile_key: string;
  display_name: string;
  description?: string | null;
  status: VoiceProfileStatus;
  visibility: SpeechVisibility;
  owner_kind: VoiceProfileOwnerKind;
  owner_agent_id?: string | null;
  provider_integration_id?: string | null;
  provider_voice_id?: string | null;
  default_language?: string | null;
  supported_languages: string[];
  voice_kind: VoiceKind;
  reference_asset_id?: string | null;
  consent_status: VoiceConsentStatus;
  usage_policy_json: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
};

export type VoiceProfileUpdateInput = Partial<
  Pick<
    VoiceProfileInput,
    | "display_name"
    | "description"
    | "status"
    | "visibility"
    | "provider_integration_id"
    | "provider_voice_id"
    | "default_language"
    | "supported_languages"
    | "reference_asset_id"
    | "consent_status"
    | "usage_policy_json"
    | "metadata_json"
  >
>;

export type AgentVoiceProfileBindingInput = {
  worldline_id?: string | null;
  voice_profile_id: string;
  binding_role: VoiceBindingRole;
  priority: number;
  is_default: boolean;
  style_overrides_json: Record<string, unknown>;
};

export type SpeechStyleMappingInput = {
  mapping_key: string;
  provider_kind: string;
  emotion_key: string;
  style_json: Record<string, unknown>;
};

export type SpeechStyleMappingUpdateInput = {
  style_json: Record<string, unknown>;
};

export type TTSInput = {
  worldline_id?: string | null;
  provider_id: string;
  voice_profile_id?: string | null;
  agent_id?: string | null;
  allow_provider_default_voice?: boolean;
  text: string;
  language?: string | null;
  emotion?: string | null;
  intensity?: number | null;
  style_overrides_json: Record<string, unknown>;
  output_format: string;
  conversation_id?: string | null;
  turn_id?: string | null;
  media_job_id?: string | null;
};

export type TTSResult = {
  media_job: MediaJob;
  output_asset: MediaAsset;
  output_objects: MediaObject[];
  model_invocation: InvocationRef;
  model_invocation_id: string;
};

export type STTInput = {
  worldline_id?: string | null;
  provider_id: string;
  source_asset_id: string;
  language?: string | null;
  diarization: boolean;
  timestamps: boolean;
  conversation_id?: string | null;
  turn_id?: string | null;
  speaker_actor_ref?: string | null;
};

export type STTResult = {
  media_job: MediaJob;
  transcript: SpeechTranscript;
  model_invocation: InvocationRef;
  model_invocation_id: string;
};

export type VoiceProfileFilters = {
  worldline_id?: string;
};

export type TranscriptFilters = {
  worldline_id?: string;
  source_asset_id?: string;
};

export type StyleMappingFilters = {
  provider_kind?: string;
  emotion_key?: string;
};

export const voiceProfileStatusOptions: VoiceProfileStatus[] = ["active", "disabled", "deleted"];
export const speechVisibilityOptions: SpeechVisibility[] = [
  "private",
  "world_admin",
  "world_member",
  "developer_only",
  "hidden",
];
export const voiceProfileOwnerKindOptions: VoiceProfileOwnerKind[] = [
  "world",
  "agent",
  "user",
  "provider",
  "other",
];
export const voiceKindOptions: VoiceKind[] = [
  "preset",
  "cloned",
  "designed",
  "imported",
  "generated",
  "external_provider",
  "other",
];
export const voiceConsentStatusOptions: VoiceConsentStatus[] = [
  "not_required",
  "user_owned_or_authorized",
  "admin_authorized",
  "pending_review",
  "restricted",
  "unknown",
];
export const voiceBindingRoleOptions: VoiceBindingRole[] = [
  "default",
  "narration",
  "inner_voice",
  "phone_call",
  "disguise",
  "alternate",
  "other",
];

export function listVoiceProfiles(
  worldId: string,
  filters: VoiceProfileFilters = {},
): Promise<VoiceProfile[]> {
  return adminRequest<VoiceProfile[]>(
    `/api/worlds/${worldId}/speech/voice-profiles${query(filters)}`,
    { method: "GET" },
  );
}

export function createVoiceProfile(worldId: string, input: VoiceProfileInput): Promise<VoiceProfile> {
  return adminRequest<VoiceProfile>(`/api/worlds/${worldId}/speech/voice-profiles`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateVoiceProfile(
  worldId: string,
  voiceProfileId: string,
  input: VoiceProfileUpdateInput,
): Promise<VoiceProfile> {
  return adminRequest<VoiceProfile>(
    `/api/worlds/${worldId}/speech/voice-profiles/${voiceProfileId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function deleteVoiceProfile(worldId: string, voiceProfileId: string): Promise<void> {
  return adminRequest<void>(`/api/worlds/${worldId}/speech/voice-profiles/${voiceProfileId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listAgentVoiceBindings(
  worldId: string,
  agentId: string,
  filters: VoiceProfileFilters = {},
): Promise<AgentVoiceProfileBinding[]> {
  return adminRequest<AgentVoiceProfileBinding[]>(
    `/api/worlds/${worldId}/agents/${agentId}/voice-profiles${query(filters)}`,
    { method: "GET" },
  );
}

export function createAgentVoiceBinding(
  worldId: string,
  agentId: string,
  input: AgentVoiceProfileBindingInput,
): Promise<AgentVoiceProfileBinding> {
  return adminRequest<AgentVoiceProfileBinding>(
    `/api/worlds/${worldId}/agents/${agentId}/voice-profiles`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function deleteAgentVoiceBinding(
  worldId: string,
  agentId: string,
  bindingId: string,
): Promise<void> {
  return adminRequest<void>(
    `/api/worlds/${worldId}/agents/${agentId}/voice-profiles/${bindingId}`,
    {
      method: "DELETE",
      csrf: true,
    },
  );
}

export function listStyleMappings(
  worldId: string,
  filters: StyleMappingFilters = {},
): Promise<SpeechStyleMapping[]> {
  return adminRequest<SpeechStyleMapping[]>(
    `/api/worlds/${worldId}/speech/style-mappings${query(filters)}`,
    { method: "GET" },
  );
}

export function createStyleMapping(
  worldId: string,
  input: SpeechStyleMappingInput,
): Promise<SpeechStyleMapping> {
  return adminRequest<SpeechStyleMapping>(`/api/worlds/${worldId}/speech/style-mappings`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateStyleMapping(
  worldId: string,
  mappingId: string,
  input: SpeechStyleMappingUpdateInput,
): Promise<SpeechStyleMapping> {
  return adminRequest<SpeechStyleMapping>(
    `/api/worlds/${worldId}/speech/style-mappings/${mappingId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function deleteStyleMapping(worldId: string, mappingId: string): Promise<void> {
  return adminRequest<void>(`/api/worlds/${worldId}/speech/style-mappings/${mappingId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listTranscripts(
  worldId: string,
  filters: TranscriptFilters = {},
): Promise<SpeechTranscript[]> {
  return adminRequest<SpeechTranscript[]>(
    `/api/worlds/${worldId}/speech/transcripts${query(filters)}`,
    { method: "GET" },
  );
}

export function runTTS(worldId: string, input: TTSInput): Promise<TTSResult> {
  return adminRequest<TTSResult>(`/api/worlds/${worldId}/speech/tts`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function runSTT(worldId: string, input: STTInput): Promise<STTResult> {
  return adminRequest<STTResult>(`/api/worlds/${worldId}/speech/stt`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

function query(filters: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if ((typeof value === "string" || typeof value === "number" || typeof value === "boolean") && value !== "") {
      search.set(key, String(value));
    }
  }
  return search.size === 0 ? "" : `?${search.toString()}`;
}
