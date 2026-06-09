import { adminRequest } from "@/lib/admin/api-client";

export type InvocationKind =
  | "agent_runtime"
  | "conversation_turn"
  | "narrative_generation"
  | "gm_generation"
  | "eval"
  | "image_generation"
  | "image_edit"
  | "image_analysis"
  | "speech_to_text"
  | "text_to_speech"
  | "voice_clone"
  | "tool_planning"
  | "repair"
  | "critique"
  | "other";

export type InvocationActorKind =
  | "system"
  | "platform_admin"
  | "world_admin"
  | "agent"
  | "player"
  | "runtime"
  | "service";

export type InvocationProviderKind =
  | "openai_compatible"
  | "anthropic_compatible"
  | "openai_image"
  | "openai_audio"
  | "custom_http"
  | "comfyui"
  | "mimo_tts"
  | "mimo_asr"
  | "omnivoice"
  | "gpt_sovits"
  | "local_stub"
  | "other";

export type InvocationStatus = "pending" | "running" | "succeeded" | "failed" | "cancelled" | "redacted";
export type InvocationVisibility = "private" | "world_admin" | "developer_only" | "hidden";
export type InvocationRedactionStatus = "raw" | "redacted" | "hidden" | "checksum_only";
export type InvocationRetentionPolicy =
  | "local_debug"
  | "short_term"
  | "long_term"
  | "eval_only"
  | "purge_after_days";
export type RedactionMode = "clear_raw_payloads" | "checksum_only" | "hide";
export type SortOrder = "asc" | "desc";

export type InvocationRecord = {
  id: string;
  world_id: string;
  worldline_id: string;
  trace_id: string;
  parent_invocation_id: string | null;
  invocation_kind: InvocationKind;
  actor_kind: InvocationActorKind;
  actor_ref: string | null;
  agent_id: string | null;
  conversation_id: string | null;
  turn_id: string | null;
  world_event_id: string | null;
  media_job_id: string | null;
  media_asset_id: string | null;
  memory_write_job_id: string | null;
  provider_kind: InvocationProviderKind;
  provider_profile_id: string | null;
  model_name: string | null;
  model_version: string | null;
  prompt_template_key: string | null;
  prompt_template_version: number | null;
  input_text: string | null;
  output_text: string | null;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  request_params_json: Record<string, unknown> | null;
  response_metadata_json: Record<string, unknown> | null;
  usage_json: Record<string, unknown> | null;
  latency_ms: number | null;
  estimated_cost: string | number | null;
  status: InvocationStatus;
  error_text: string | null;
  visibility: InvocationVisibility;
  redaction_status: InvocationRedactionStatus;
  retention_policy: InvocationRetentionPolicy;
  contains_sensitive_context: boolean;
  purge_after: string | null;
  created_at: string;
  updated_at: string;
};

export type InvocationSearchResult = {
  invocations: InvocationRecord[];
};

export type PromptSnapshot = {
  id: string;
  invocation_id: string;
  template_id: string | null;
  template_key: string | null;
  template_version: number | null;
  raw_prompt_text: string | null;
  raw_messages_json: Array<Record<string, unknown>> | null;
  raw_request_json: Record<string, unknown> | null;
  raw_response_json: Record<string, unknown> | null;
  raw_output_text: string | null;
  normalized_output_json: Record<string, unknown> | null;
  prompt_context_snapshot_json: Record<string, unknown> | null;
  tool_definitions_json: Record<string, unknown> | null;
  context_pack_refs_json: Record<string, unknown> | null;
  input_asset_refs_json: Array<Record<string, unknown>> | null;
  prompt_checksum_sha256: string;
  request_checksum_sha256: string | null;
  response_checksum_sha256: string | null;
  output_checksum_sha256: string | null;
  visibility: InvocationVisibility;
  redaction_status: InvocationRedactionStatus;
  contains_sensitive_context: boolean;
  created_at: string;
  updated_at: string;
};

export type InvocationTag = {
  id: string;
  world_id: string;
  worldline_id: string;
  invocation_id: string;
  tag_type: string;
  tag_key: string;
  tag_value: string;
  created_at: string;
};

export type InvocationFilters = {
  worldline_id?: string;
  invocation_kind?: InvocationKind;
  provider_kind?: InvocationProviderKind;
  status?: InvocationStatus;
  visibility?: InvocationVisibility;
  redaction_status?: InvocationRedactionStatus;
  retention_policy?: InvocationRetentionPolicy;
  contains_sensitive_context?: boolean;
  contains_text?: string;
  tag?: string[];
  limit?: number;
  order?: SortOrder;
  include_hidden?: boolean;
};

export type InvocationTagInput = {
  worldline_id?: string | null;
  tag_type: string;
  tag_key: string;
  tag_value: string;
};

export type InvocationRedactInput = {
  redaction_status: InvocationRedactionStatus;
  reason: string;
  mode: RedactionMode;
};

export const invocationKindOptions: InvocationKind[] = [
  "agent_runtime",
  "conversation_turn",
  "narrative_generation",
  "gm_generation",
  "eval",
  "image_generation",
  "image_edit",
  "image_analysis",
  "speech_to_text",
  "text_to_speech",
  "voice_clone",
  "tool_planning",
  "repair",
  "critique",
  "other",
];

export const invocationProviderKindOptions: InvocationProviderKind[] = [
  "openai_compatible",
  "anthropic_compatible",
  "openai_image",
  "openai_audio",
  "custom_http",
  "comfyui",
  "mimo_tts",
  "mimo_asr",
  "omnivoice",
  "gpt_sovits",
  "local_stub",
  "other",
];

export const invocationStatusOptions: InvocationStatus[] = [
  "pending",
  "running",
  "succeeded",
  "failed",
  "cancelled",
  "redacted",
];

export const invocationVisibilityOptions: InvocationVisibility[] = [
  "private",
  "world_admin",
  "developer_only",
  "hidden",
];

export const invocationRedactionStatusOptions: InvocationRedactionStatus[] = [
  "raw",
  "redacted",
  "hidden",
  "checksum_only",
];

export const invocationRetentionPolicyOptions: InvocationRetentionPolicy[] = [
  "local_debug",
  "short_term",
  "long_term",
  "eval_only",
  "purge_after_days",
];

export const redactionModeOptions: RedactionMode[] = [
  "clear_raw_payloads",
  "checksum_only",
  "hide",
];

function worldPath(worldId: string): string {
  return `/api/worlds/${encodeURIComponent(worldId)}`;
}

function invocationsPath(worldId: string): string {
  return `${worldPath(worldId)}/model-invocations`;
}

function invocationPath(worldId: string, invocationId: string): string {
  return `${invocationsPath(worldId)}/${encodeURIComponent(invocationId)}`;
}

function invocationTagsPath(worldId: string, invocationId: string): string {
  return `${invocationPath(worldId, invocationId)}/tags`;
}

export async function listInvocations(
  worldId: string,
  filters: InvocationFilters = {},
): Promise<InvocationRecord[]> {
  const result = await adminRequest<InvocationSearchResult>(
    `${invocationsPath(worldId)}${query(filters)}`,
    { method: "GET" },
  );
  return result.invocations;
}

export function getInvocation(worldId: string, invocationId: string): Promise<InvocationRecord> {
  return adminRequest<InvocationRecord>(invocationPath(worldId, invocationId), {
    method: "GET",
  });
}

export function getPromptSnapshot(worldId: string, invocationId: string): Promise<PromptSnapshot> {
  return adminRequest<PromptSnapshot>(
    `${invocationPath(worldId, invocationId)}/prompt-snapshot`,
    { method: "GET" },
  );
}

export function listInvocationTags(worldId: string, invocationId: string): Promise<InvocationTag[]> {
  return adminRequest<InvocationTag[]>(invocationTagsPath(worldId, invocationId), {
    method: "GET",
  });
}

export function createInvocationTag(
  worldId: string,
  invocationId: string,
  input: InvocationTagInput,
): Promise<InvocationTag> {
  return adminRequest<InvocationTag>(invocationTagsPath(worldId, invocationId), {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function deleteInvocationTag(
  worldId: string,
  invocationId: string,
  tagId: string,
): Promise<void> {
  return adminRequest<void>(
    `${invocationTagsPath(worldId, invocationId)}/${encodeURIComponent(tagId)}`,
    { method: "DELETE", csrf: true },
  );
}

export function redactInvocation(
  worldId: string,
  invocationId: string,
  input: InvocationRedactInput,
): Promise<InvocationRecord> {
  return adminRequest<InvocationRecord>(`${invocationPath(worldId, invocationId)}/redact`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

function query(filters: InvocationFilters): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== "") {
          search.append(key, item);
        }
      }
    } else if ((typeof value === "string" || typeof value === "number" || typeof value === "boolean") && value !== "") {
      search.set(key, String(value));
    }
  }
  return search.size === 0 ? "" : `?${search.toString()}`;
}
