import { AdminClientError, adminRequest } from "@/lib/admin/api-client";
import { readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from "@/lib/auth/types";

export type MediaAssetKind = "image" | "audio" | "video" | "document" | "other";
export type MediaAssetStatus = "registered" | "available" | "failed" | "deleted";
export type MediaVisibility =
  | "private"
  | "world_admin"
  | "world_member"
  | "player_visible"
  | "reader_visible"
  | "developer_only"
  | "hidden";
export type MediaSourceKind =
  | "provider_generated"
  | "manual_upload"
  | "imported_original"
  | "composed"
  | "background_removed"
  | "cropped"
  | "converted"
  | "system_generated"
  | "test_fixture"
  | "other";
export type MediaAssetRole =
  | "original_image"
  | "reference_image"
  | "mask_image"
  | "transparent_png"
  | "composite_image"
  | "scene_background"
  | "character_sprite"
  | "character_expression"
  | "character_pose"
  | "event_cg"
  | "speech_audio"
  | "voice_file"
  | "voice_sample"
  | "transcript_audio"
  | "video_clip"
  | "document"
  | "thumbnail"
  | "other";
export type MediaObjectRole =
  | "original"
  | "primary"
  | "thumbnail"
  | "preview"
  | "mask"
  | "alpha"
  | "transparent"
  | "composed"
  | "waveform"
  | "transcript_source"
  | "derived"
  | "other";
export type MediaReferenceKind =
  | "conversation_turn"
  | "conversation_session"
  | "world_event"
  | "narrative_artifact"
  | "agent"
  | "scene"
  | "world"
  | "model_invocation"
  | "media_job"
  | "memory_write_job"
  | "other";
export type MediaReferenceRole =
  | "attachment"
  | "input"
  | "output"
  | "evidence"
  | "preview"
  | "thumbnail"
  | "background"
  | "foreground"
  | "character_sprite"
  | "voice_reference"
  | "source"
  | "derived_from"
  | "other";
export type MediaJobKind =
  | "image_generation"
  | "image_edit"
  | "speech_generation"
  | "speech_transcription"
  | "background_removal"
  | "composition"
  | "upload_import"
  | "vision_analysis"
  | "transcode"
  | "thumbnail"
  | "import"
  | "other";
export type MediaJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export type MediaAsset = {
  id: string;
  world_id: string;
  worldline_id: string;
  asset_kind: MediaAssetKind;
  asset_role: MediaAssetRole;
  source_kind: MediaSourceKind;
  status: MediaAssetStatus;
  visibility: MediaVisibility;
  mime_type: string | null;
  file_ext: string | null;
  size_bytes: number | null;
  checksum_sha256: string | null;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  sample_rate_hz: number | null;
  audio_channels: number | null;
  has_alpha: boolean | null;
  color_mode: string | null;
  provider_kind: string | null;
  source_job_id: string | null;
  source_event_id: string | null;
  source_invocation_id: string | null;
  title: string | null;
  description: string | null;
  created_by_actor_ref: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MediaObject = {
  id: string;
  asset_id: string;
  world_id: string;
  worldline_id: string;
  object_role: MediaObjectRole;
  filename: string | null;
  mime_type: string;
  size_bytes: number;
  checksum_sha256: string;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  sample_rate_hz: number | null;
  audio_channels: number | null;
  frame_rate: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type MediaReference = {
  id: string;
  world_id: string;
  worldline_id: string;
  asset_id: string;
  ref_kind: MediaReferenceKind;
  ref_id: string;
  ref_role: MediaReferenceRole;
  display_order: number;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ReaderMediaObjectDescriptor = {
  object_id: string;
  object_role: string;
  content_type: string;
  size: number;
  checksum_sha256: string;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  sample_rate_hz: number | null;
  audio_channels: number | null;
  download_url: string;
};

export type ReaderMediaReferenceDescriptor = {
  reference_id: string;
  ref_kind: "conversation_turn" | "conversation_session" | "narrative_artifact" | string;
  ref_id: string;
  ref_role: string;
  display_order: number;
};

export type ReaderMediaDescriptor = {
  asset_id: string;
  world_id: string;
  worldline_id: string;
  asset_kind: "image" | "audio" | "video";
  asset_role: MediaAssetRole | string;
  visibility: "world_member" | "player_visible" | "reader_visible" | string;
  title: string | null;
  description: string | null;
  content_type: string | null;
  size: number | null;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  objects: ReaderMediaObjectDescriptor[];
  references: ReaderMediaReferenceDescriptor[];
  created_at: string;
  updated_at: string;
};

export type MediaAssetReferences = {
  asset_id: string;
  contexts: Array<Record<string, unknown>>;
  tags: Array<Record<string, unknown>>;
  collections: Array<Record<string, unknown>>;
  input_count: number;
  output_count: number;
  tag_count: number;
  collection_count: number;
};

export type MediaJob = {
  id: string;
  world_id: string;
  worldline_id: string;
  conversation_id: string | null;
  turn_id: string | null;
  agent_id: string | null;
  job_kind: MediaJobKind;
  provider_kind: string | null;
  priority: number;
  cancel_policy: string | null;
  deadline_hint: string | null;
  dedupe_key: string | null;
  invalidation_key: string | null;
  source_event_id: string | null;
  source_invocation_id: string | null;
  provider_config_json: Record<string, unknown>;
  request_json: Record<string, unknown>;
  status: MediaJobStatus;
  result_json: Record<string, unknown>;
  error_text: string | null;
  created_by_actor_ref: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MediaAssetFilters = {
  worldline_id?: string;
  asset_kind?: MediaAssetKind;
  asset_role?: MediaAssetRole;
  source_kind?: MediaSourceKind;
  status?: MediaAssetStatus;
  visibility?: MediaVisibility;
  contains_text?: string;
  limit?: number;
};

export type MediaJobFilters = {
  worldline_id?: string;
  job_kind?: MediaJobKind;
  status?: MediaJobStatus;
  provider_kind?: string;
  limit?: number;
};

export type MediaReferenceFilters = {
  worldline_id?: string;
  asset_id?: string;
  ref_kind?: MediaReferenceKind;
  ref_role?: MediaReferenceRole;
  limit?: number;
};

export type MediaAssetUpdateInput = {
  visibility?: MediaVisibility;
  status?: MediaAssetStatus;
  title?: string | null;
  description?: string | null;
  metadata?: Record<string, unknown>;
};

export type MediaAssetUploadInput = {
  file: File;
  worldline_id?: string | null;
  asset_kind: MediaAssetKind;
  asset_role: MediaAssetRole;
  visibility: MediaVisibility;
  title?: string | null;
  description?: string | null;
  metadata?: Record<string, unknown>;
};

export type MediaAssetUploadResponse = {
  asset: MediaAsset;
  object: MediaObject;
};

export const mediaAssetKindOptions: MediaAssetKind[] = ["image", "audio", "video", "document", "other"];

export const mediaAssetRoleOptions: MediaAssetRole[] = [
  "reference_image",
  "scene_background",
  "character_sprite",
  "character_expression",
  "composite_image",
  "speech_audio",
  "voice_sample",
  "transcript_audio",
  "document",
  "other",
];

export const mediaSourceKindOptions: MediaSourceKind[] = [
  "manual_upload",
  "provider_generated",
  "composed",
  "system_generated",
  "test_fixture",
  "other",
];

export const mediaStatusOptions: MediaAssetStatus[] = ["registered", "available", "failed", "deleted"];

export const mediaVisibilityOptions: MediaVisibility[] = [
  "private",
  "world_admin",
  "world_member",
  "player_visible",
  "reader_visible",
  "developer_only",
  "hidden",
];

export const mediaJobKindOptions: MediaJobKind[] = [
  "image_generation",
  "image_edit",
  "speech_generation",
  "speech_transcription",
  "background_removal",
  "composition",
  "upload_import",
  "vision_analysis",
  "transcode",
  "thumbnail",
  "import",
  "other",
];

export const mediaJobStatusOptions: MediaJobStatus[] = [
  "queued",
  "running",
  "succeeded",
  "failed",
  "cancelled",
];

function worldPath(worldId: string): string {
  return `/api/worlds/${encodeURIComponent(worldId)}`;
}

function mediaPath(worldId: string): string {
  return `${worldPath(worldId)}/media`;
}

function mediaAssetsPath(worldId: string): string {
  return `${mediaPath(worldId)}/assets`;
}

function mediaAssetPath(worldId: string, assetId: string): string {
  return `${mediaAssetsPath(worldId)}/${encodeURIComponent(assetId)}`;
}

function mediaAssetObjectsPath(worldId: string, assetId: string): string {
  return `${mediaAssetPath(worldId, assetId)}/objects`;
}

function mediaAssetReferencesPath(worldId: string, assetId: string): string {
  return `${mediaAssetPath(worldId, assetId)}/references`;
}

function mediaReferencesPath(worldId: string): string {
  return `${mediaPath(worldId)}/references`;
}

function mediaJobsPath(worldId: string): string {
  return `${mediaPath(worldId)}/jobs`;
}

function mediaJobPath(worldId: string, jobId: string): string {
  return `${mediaJobsPath(worldId)}/${encodeURIComponent(jobId)}`;
}

export function listMediaAssets(
  worldId: string,
  filters: MediaAssetFilters = {},
): Promise<MediaAsset[]> {
  return adminRequest<MediaAsset[]>(`${mediaAssetsPath(worldId)}${query(filters)}`, {
    method: "GET",
  });
}

export function updateMediaAsset(
  worldId: string,
  assetId: string,
  input: MediaAssetUpdateInput,
): Promise<MediaAsset> {
  return adminRequest<MediaAsset>(mediaAssetPath(worldId, assetId), {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function listMediaObjects(worldId: string, assetId: string): Promise<MediaObject[]> {
  return adminRequest<MediaObject[]>(mediaAssetObjectsPath(worldId, assetId), {
    method: "GET",
  });
}

export function listMediaAssetReferences(
  worldId: string,
  assetId: string,
): Promise<MediaAssetReferences> {
  return adminRequest<MediaAssetReferences>(mediaAssetReferencesPath(worldId, assetId), {
    method: "GET",
  });
}

export function listMediaReferences(
  worldId: string,
  filters: MediaReferenceFilters = {},
): Promise<MediaReference[]> {
  return adminRequest<MediaReference[]>(`${mediaReferencesPath(worldId)}${query(filters)}`, {
    method: "GET",
  });
}

export function listMediaJobs(worldId: string, filters: MediaJobFilters = {}): Promise<MediaJob[]> {
  return adminRequest<MediaJob[]>(`${mediaJobsPath(worldId)}${query(filters)}`, {
    method: "GET",
  });
}

export function cancelMediaJob(worldId: string, jobId: string): Promise<MediaJob> {
  return adminRequest<MediaJob>(`${mediaJobPath(worldId, jobId)}/cancel`, {
    method: "POST",
    csrf: true,
  });
}

export function retryMediaJob(worldId: string, jobId: string): Promise<MediaJob> {
  return adminRequest<MediaJob>(`${mediaJobPath(worldId, jobId)}/retry`, {
    method: "POST",
    csrf: true,
  });
}

export async function uploadMediaAsset(
  worldId: string,
  input: MediaAssetUploadInput,
): Promise<MediaAssetUploadResponse> {
  const formData = new FormData();
  formData.set("file", input.file);
  appendFormValue(formData, "worldline_id", input.worldline_id);
  formData.set("asset_kind", input.asset_kind);
  formData.set("asset_role", input.asset_role);
  formData.set("visibility", input.visibility);
  appendFormValue(formData, "title", input.title);
  appendFormValue(formData, "description", input.description);
  formData.set("metadata_json", JSON.stringify(input.metadata ?? {}));

  const response = await fetch(`${mediaAssetsPath(worldId)}/upload`, {
    method: "POST",
    headers: new Headers([[CSRF_HEADER_NAME, await csrfToken()]]),
    credentials: "include",
    cache: "no-store",
    body: formData,
  });

  if (response.ok) {
    return (await response.json()) as MediaAssetUploadResponse;
  }
  throw new AdminClientError((await errorDetail(response)) ?? "Media upload failed.", response.status);
}

export function mediaObjectDownloadPath(worldId: string, objectId: string): string {
  return `${mediaPath(worldId)}/objects/${encodeURIComponent(objectId)}/download`;
}

const UUID_PATH_SEGMENT = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const READER_MEDIA_DOWNLOAD_PATH_PATTERN = new RegExp(
  `^/api/worlds/${UUID_PATH_SEGMENT}/reader/media/worldlines/${UUID_PATH_SEGMENT}/objects/${UUID_PATH_SEGMENT}/download$`,
);

export function readerMediaObjectDownloadPath(downloadUrl: string): string | null {
  const path = downloadUrl.startsWith("/worlds/") ? `/api${downloadUrl}` : downloadUrl;
  if (READER_MEDIA_DOWNLOAD_PATH_PATTERN.test(path)) {
    return path;
  }
  return null;
}

function query(filters: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if ((typeof value === "string" || typeof value === "number") && value !== "") {
      search.set(key, String(value));
    }
  }
  return search.size === 0 ? "" : `?${search.toString()}`;
}

function appendFormValue(formData: FormData, key: string, value: string | null | undefined): void {
  if (value !== undefined && value !== null && value !== "") {
    formData.set(key, value);
  }
}

async function csrfToken(): Promise<string> {
  const existingToken = readCookie(CSRF_COOKIE_NAME);
  if (existingToken !== null) {
    return existingToken;
  }
  const response = await requestCsrf();
  return response.csrf_token;
}

async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    return null;
  }
  return null;
}
