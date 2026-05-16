import { adminRequest } from "@/lib/admin/api-client";

export type ProviderScopeKind = "global" | "world";
export type ProviderKind =
  | "text_generation"
  | "image_generation"
  | "image_editing"
  | "image_analysis"
  | "image_composition"
  | "speech_to_text"
  | "text_to_speech"
  | "voice_cloning"
  | "background_removal"
  | "workflow_engine"
  | "embedding"
  | "reranker"
  | "other";
export type ProviderAdapterKind =
  | "fake"
  | "openai"
  | "openai_compatible"
  | "anthropic"
  | "anthropic_compatible"
  | "comfyui"
  | "mimo_tts"
  | "mimo_asr"
  | "omnivoice"
  | "gpt_sovits"
  | "rembg"
  | "sam2"
  | "custom_http"
  | "local_stub"
  | "other";
export type ProviderIntegrationStatus = "draft" | "active" | "disabled" | "deleted";
export type ProviderVisibility = "private" | "world_admin" | "developer_only" | "hidden";
export type ProviderHealthStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

export type ProviderCapabilityInput = {
  capability_key: string;
  capability_json: Record<string, unknown>;
};

export type ProviderTemplate = {
  template_key: string;
  display_name: string;
  provider_kind: ProviderKind;
  adapter_kind: ProviderAdapterKind;
  description: string;
  base_url_placeholder: string | null;
  model_name_placeholder: string | null;
  auth_ref_placeholder: string | null;
  config_json: Record<string, unknown>;
  default_params_json: Record<string, unknown>;
  capabilities: ProviderCapabilityInput[];
  model_discovery: Record<string, unknown>;
};

export type ProviderModelDiscoveryInput = {
  provider_id?: string | null;
  provider_kind?: ProviderKind | null;
  adapter_kind?: ProviderAdapterKind | null;
  base_url?: string | null;
  auth_ref?: string | null;
  config_json?: Record<string, unknown>;
  default_params_json?: Record<string, unknown>;
};

export type ProviderModelDiscoveryResult = {
  provider_id: string | null;
  provider_kind: ProviderKind;
  adapter_kind: ProviderAdapterKind;
  discovery_status: "succeeded" | "failed" | string;
  models: string[];
  manual_fallback_allowed: boolean;
  error_code: string | null;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
};

export type ProviderIntegrationInput = {
  scope_kind: ProviderScopeKind;
  provider_kind: ProviderKind;
  adapter_kind: ProviderAdapterKind;
  provider_key: string;
  display_name: string;
  base_url: string | null;
  auth_ref: string | null;
  config_json: Record<string, unknown>;
  default_params_json: Record<string, unknown>;
  status: ProviderIntegrationStatus;
  visibility: ProviderVisibility;
  capabilities: ProviderCapabilityInput[];
};

export type ProviderIntegrationUpdateInput = Partial<
  Pick<
    ProviderIntegrationInput,
    | "display_name"
    | "base_url"
    | "auth_ref"
    | "config_json"
    | "default_params_json"
    | "status"
    | "visibility"
    | "capabilities"
  >
>;

export type ProviderIntegration = {
  id: string;
  world_id: string | null;
  scope_kind: ProviderScopeKind;
  scope_key: string;
  provider_kind: ProviderKind;
  adapter_kind: ProviderAdapterKind;
  provider_key: string;
  display_name: string;
  base_url: string | null;
  auth_ref: string | null;
  auth_ref_configured: boolean;
  config_json: Record<string, unknown>;
  default_params_json: Record<string, unknown>;
  status: ProviderIntegrationStatus;
  visibility: ProviderVisibility;
  created_at: string;
  updated_at: string;
};

export type ProviderCapability = ProviderCapabilityInput & {
  id: string;
  provider_integration_id: string;
  created_at: string;
  updated_at: string;
};

export type ProviderHealthCheck = {
  id: string;
  provider_integration_id: string;
  status: ProviderHealthStatus;
  latency_ms: number | null;
  checked_at: string;
  error_text: string | null;
  metadata_json: Record<string, unknown>;
};

export type ProviderSmokeTestInput = {
  worldline_id?: string | null;
  input_text?: string | null;
  input_json?: Record<string, unknown>;
  request_json?: Record<string, unknown>;
  model_name?: string | null;
  media_job_id?: string | null;
  media_asset_id?: string | null;
};

export type ProviderSmokeTestResult = {
  smoke_status: "succeeded" | "failed" | string;
  provider: ProviderIntegration;
  invocation: {
    id: string;
    status: string;
    latency_ms: number | null;
    request_params_json?: Record<string, unknown>;
    response_metadata_json?: Record<string, unknown>;
  };
  output_text: string | null;
  output_json: Record<string, unknown>;
};

export type ProviderListFilters = {
  include_global?: boolean;
  include_hidden?: boolean;
  provider_kind?: ProviderKind;
  adapter_kind?: ProviderAdapterKind;
  status?: ProviderIntegrationStatus;
  visibility?: ProviderVisibility;
  capability_key?: string;
};

export const providerKindOptions: ProviderKind[] = [
  "text_generation",
  "image_generation",
  "image_editing",
  "image_analysis",
  "image_composition",
  "speech_to_text",
  "text_to_speech",
  "voice_cloning",
  "background_removal",
  "workflow_engine",
  "embedding",
  "reranker",
  "other",
];

export const providerAdapterOptions: ProviderAdapterKind[] = [
  "fake",
  "openai",
  "openai_compatible",
  "anthropic",
  "anthropic_compatible",
  "comfyui",
  "mimo_tts",
  "mimo_asr",
  "omnivoice",
  "gpt_sovits",
  "rembg",
  "sam2",
  "custom_http",
  "local_stub",
  "other",
];

export const providerStatusOptions: ProviderIntegrationStatus[] = [
  "draft",
  "active",
  "disabled",
  "deleted",
];

export const providerVisibilityOptions: ProviderVisibility[] = [
  "private",
  "world_admin",
  "developer_only",
  "hidden",
];

export function listProviderIntegrations(
  worldId: string,
  filters: ProviderListFilters = {},
): Promise<ProviderIntegration[]> {
  return adminRequest<ProviderIntegration[]>(
    `/api/worlds/${worldId}/providers${providerQuery(filters)}`,
    { method: "GET" },
  );
}

export function listProviderTemplates(worldId: string): Promise<ProviderTemplate[]> {
  return adminRequest<ProviderTemplate[]>(`/api/worlds/${worldId}/providers/templates`, {
    method: "GET",
  });
}

export function discoverProviderModels(
  worldId: string,
  input: ProviderModelDiscoveryInput,
): Promise<ProviderModelDiscoveryResult> {
  return adminRequest<ProviderModelDiscoveryResult>(
    `/api/worlds/${worldId}/providers/model-discovery`,
    { method: "POST", body: input, csrf: true },
  );
}

export function createProviderIntegration(
  worldId: string,
  input: ProviderIntegrationInput,
): Promise<ProviderIntegration> {
  return adminRequest<ProviderIntegration>(`/api/worlds/${worldId}/providers`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateProviderIntegration(
  worldId: string,
  providerId: string,
  input: ProviderIntegrationUpdateInput,
): Promise<ProviderIntegration> {
  return adminRequest<ProviderIntegration>(`/api/worlds/${worldId}/providers/${providerId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function deleteProviderIntegration(worldId: string, providerId: string): Promise<void> {
  return adminRequest<void>(`/api/worlds/${worldId}/providers/${providerId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listProviderCapabilities(
  worldId: string,
  providerId: string,
): Promise<ProviderCapability[]> {
  return adminRequest<ProviderCapability[]>(
    `/api/worlds/${worldId}/providers/${providerId}/capabilities`,
    { method: "GET" },
  );
}

export function runProviderHealthCheck(
  worldId: string,
  providerId: string,
): Promise<ProviderHealthCheck> {
  return adminRequest<ProviderHealthCheck>(
    `/api/worlds/${worldId}/providers/${providerId}/health-check`,
    { method: "POST", csrf: true },
  );
}

export function listProviderHealthChecks(
  worldId: string,
  providerId: string,
  limit = 50,
): Promise<ProviderHealthCheck[]> {
  return adminRequest<ProviderHealthCheck[]>(
    `/api/worlds/${worldId}/providers/${providerId}/health-checks?limit=${limit}`,
    { method: "GET" },
  );
}

export function runProviderSmokeTest(
  worldId: string,
  providerId: string,
  input: ProviderSmokeTestInput,
): Promise<ProviderSmokeTestResult> {
  return adminRequest<ProviderSmokeTestResult>(
    `/api/worlds/${worldId}/providers/${providerId}/smoke-test`,
    { method: "POST", body: input, csrf: true },
  );
}

function providerQuery(filters: ProviderListFilters): string {
  const search = new URLSearchParams();
  appendOptional(search, "include_global", filters.include_global);
  appendOptional(search, "include_hidden", filters.include_hidden);
  appendOptional(search, "provider_kind", filters.provider_kind);
  appendOptional(search, "adapter_kind", filters.adapter_kind);
  appendOptional(search, "status", filters.status);
  appendOptional(search, "visibility", filters.visibility);
  appendOptional(search, "capability_key", filters.capability_key);
  return search.size === 0 ? "" : `?${search.toString()}`;
}

function appendOptional(
  search: URLSearchParams,
  key: string,
  value: string | boolean | undefined,
): void {
  if (value !== undefined && value !== "") {
    search.set(key, String(value));
  }
}
