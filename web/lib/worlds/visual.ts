import { adminRequest } from "@/lib/admin/api-client";
import type { MediaJob } from "@/lib/worlds/media";

export type VisualRecordStatus = "active" | "disabled" | "deleted";
export type VisualVisibility = "private" | "world_admin" | "world_member" | "developer_only" | "hidden";

export type SpriteSet = {
  id: string;
  world_id: string;
  worldline_id: string;
  agent_id: string;
  style_key: string;
  display_name: string;
  default_variant_id: string | null;
  status: VisualRecordStatus;
  visibility: VisualVisibility;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SpriteVariant = {
  id: string;
  world_id: string;
  worldline_id: string;
  sprite_set_id: string;
  asset_id: string;
  expression_key: string;
  pose_key: string | null;
  outfit_key: string | null;
  mood_tags: string[];
  priority: number;
  is_default: boolean;
  status: VisualRecordStatus;
  visibility: VisualVisibility;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SceneBackground = {
  id: string;
  world_id: string;
  worldline_id: string;
  scene_id: string | null;
  location_key: string;
  time_of_day: string | null;
  weather_key: string | null;
  asset_id: string;
  priority: number;
  is_default: boolean;
  status: VisualRecordStatus;
  visibility: VisualVisibility;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type VisualAssetRef = {
  id: string;
  world_id: string;
  worldline_id: string;
  asset_kind: string;
  asset_role: string;
  source_kind: string;
  status: string;
  visibility: string;
  mime_type: string | null;
  file_ext: string | null;
  size_bytes: number | null;
  checksum_sha256: string | null;
  width: number | null;
  height: number | null;
  has_alpha: boolean | null;
  title: string | null;
  description: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type VisualObjectRef = {
  id: string;
  asset_id: string;
  world_id: string;
  worldline_id: string;
  object_role: string;
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

export type SpriteSetInput = {
  worldline_id: string;
  agent_id: string;
  style_key: string;
  display_name: string;
  default_variant_id?: string | null;
  status: VisualRecordStatus;
  visibility: VisualVisibility;
  metadata_json: Record<string, unknown>;
};

export type SpriteSetUpdateInput = Partial<
  Pick<
    SpriteSetInput,
    "display_name" | "default_variant_id" | "status" | "visibility" | "metadata_json"
  >
>;

export type SpriteVariantInput = {
  worldline_id: string;
  asset_id: string;
  expression_key: string;
  pose_key?: string | null;
  outfit_key?: string | null;
  mood_tags: string[];
  priority: number;
  is_default: boolean;
  status: VisualRecordStatus;
  visibility: VisualVisibility;
  metadata_json: Record<string, unknown>;
};

export type SpriteVariantUpdateInput = Partial<
  Pick<
    SpriteVariantInput,
    | "asset_id"
    | "expression_key"
    | "pose_key"
    | "outfit_key"
    | "mood_tags"
    | "priority"
    | "is_default"
    | "status"
    | "visibility"
    | "metadata_json"
  >
>;

export type SceneBackgroundInput = {
  worldline_id: string;
  scene_id?: string | null;
  location_key: string;
  time_of_day?: string | null;
  weather_key?: string | null;
  asset_id: string;
  priority: number;
  is_default: boolean;
  status: VisualRecordStatus;
  visibility: VisualVisibility;
  metadata_json: Record<string, unknown>;
};

export type SceneBackgroundUpdateInput = Partial<
  Pick<
    SceneBackgroundInput,
    | "scene_id"
    | "location_key"
    | "time_of_day"
    | "weather_key"
    | "asset_id"
    | "priority"
    | "is_default"
    | "status"
    | "visibility"
    | "metadata_json"
  >
>;

export type SpriteResolveInput = {
  worldline_id: string;
  agent_id: string;
  expression_key?: string | null;
  pose_key?: string | null;
  outfit_key?: string | null;
  mood_tags?: string[];
  style_key?: string | null;
  include_restricted?: boolean;
};

export type SpriteResolveResult = {
  sprite_set: SpriteSet;
  variant: SpriteVariant;
  asset: VisualAssetRef;
  fallback_reason: string | null;
  confidence: number;
};

export type BackgroundResolveInput = {
  worldline_id: string;
  scene_id?: string | null;
  location_key: string;
  time_of_day?: string | null;
  weather_key?: string | null;
  include_restricted?: boolean;
};

export type BackgroundResolveResult = {
  background: SceneBackground;
  asset: VisualAssetRef;
  fallback_reason: string | null;
  confidence: number;
};

export type SceneLayerInput = {
  asset_id: string;
  x: number;
  y: number;
  width?: number | null;
  height?: number | null;
  opacity?: number;
  z_index?: number;
  blend_mode?: string | null;
};

export type SceneComposeInput = {
  worldline_id: string;
  background_asset_id: string;
  layers: SceneLayerInput[];
  metadata_json: Record<string, unknown>;
};

export type SceneComposeResult = {
  media_job: MediaJob;
  output_asset: VisualAssetRef;
  output_objects: VisualObjectRef[];
};

export type SpriteSetFilters = {
  worldline_id: string;
  agent_id?: string;
};

export type SceneBackgroundFilters = {
  worldline_id: string;
};

export const visualStatusOptions: VisualRecordStatus[] = ["active", "disabled", "deleted"];
export const visualVisibilityOptions: VisualVisibility[] = [
  "private",
  "world_admin",
  "world_member",
  "developer_only",
  "hidden",
];

function worldPath(worldId: string): string {
  return `/api/worlds/${encodeURIComponent(worldId)}`;
}

function visualPath(worldId: string): string {
  return `${worldPath(worldId)}/visual`;
}

function spriteSetsPath(worldId: string): string {
  return `${visualPath(worldId)}/sprite-sets`;
}

function spriteSetPath(worldId: string, spriteSetId: string): string {
  return `${spriteSetsPath(worldId)}/${encodeURIComponent(spriteSetId)}`;
}

function spriteVariantsPath(worldId: string, spriteSetId: string): string {
  return `${spriteSetPath(worldId, spriteSetId)}/variants`;
}

function spriteVariantPath(worldId: string, spriteSetId: string, variantId: string): string {
  return `${spriteVariantsPath(worldId, spriteSetId)}/${encodeURIComponent(variantId)}`;
}

function backgroundsPath(worldId: string): string {
  return `${visualPath(worldId)}/backgrounds`;
}

function backgroundPath(worldId: string, backgroundId: string): string {
  return `${backgroundsPath(worldId)}/${encodeURIComponent(backgroundId)}`;
}

export function listSpriteSets(worldId: string, filters: SpriteSetFilters): Promise<SpriteSet[]> {
  return adminRequest<SpriteSet[]>(`${spriteSetsPath(worldId)}${query(filters)}`, {
    method: "GET",
  });
}

export function createSpriteSet(worldId: string, input: SpriteSetInput): Promise<SpriteSet> {
  return adminRequest<SpriteSet>(spriteSetsPath(worldId), {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateSpriteSet(
  worldId: string,
  spriteSetId: string,
  input: SpriteSetUpdateInput,
): Promise<SpriteSet> {
  return adminRequest<SpriteSet>(spriteSetPath(worldId, spriteSetId), {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function deleteSpriteSet(worldId: string, spriteSetId: string): Promise<void> {
  return adminRequest<void>(spriteSetPath(worldId, spriteSetId), {
    method: "DELETE",
    csrf: true,
  });
}

export function listSpriteVariants(
  worldId: string,
  spriteSetId: string,
): Promise<SpriteVariant[]> {
  return adminRequest<SpriteVariant[]>(
    spriteVariantsPath(worldId, spriteSetId),
    { method: "GET" },
  );
}

export function createSpriteVariant(
  worldId: string,
  spriteSetId: string,
  input: SpriteVariantInput,
): Promise<SpriteVariant> {
  return adminRequest<SpriteVariant>(
    spriteVariantsPath(worldId, spriteSetId),
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function updateSpriteVariant(
  worldId: string,
  spriteSetId: string,
  variantId: string,
  input: SpriteVariantUpdateInput,
): Promise<SpriteVariant> {
  return adminRequest<SpriteVariant>(
    spriteVariantPath(worldId, spriteSetId, variantId),
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function deleteSpriteVariant(
  worldId: string,
  spriteSetId: string,
  variantId: string,
): Promise<void> {
  return adminRequest<void>(
    spriteVariantPath(worldId, spriteSetId, variantId),
    {
      method: "DELETE",
      csrf: true,
    },
  );
}

export function resolveSprite(
  worldId: string,
  input: SpriteResolveInput,
): Promise<SpriteResolveResult> {
  return adminRequest<SpriteResolveResult>(`${visualPath(worldId)}/resolve-sprite`, {
    method: "POST",
    body: input,
  });
}

export function listSceneBackgrounds(
  worldId: string,
  filters: SceneBackgroundFilters,
): Promise<SceneBackground[]> {
  return adminRequest<SceneBackground[]>(
    `${backgroundsPath(worldId)}${query(filters)}`,
    { method: "GET" },
  );
}

export function createSceneBackground(
  worldId: string,
  input: SceneBackgroundInput,
): Promise<SceneBackground> {
  return adminRequest<SceneBackground>(backgroundsPath(worldId), {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateSceneBackground(
  worldId: string,
  backgroundId: string,
  input: SceneBackgroundUpdateInput,
): Promise<SceneBackground> {
  return adminRequest<SceneBackground>(
    backgroundPath(worldId, backgroundId),
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function deleteSceneBackground(worldId: string, backgroundId: string): Promise<void> {
  return adminRequest<void>(backgroundPath(worldId, backgroundId), {
    method: "DELETE",
    csrf: true,
  });
}

export function resolveBackground(
  worldId: string,
  input: BackgroundResolveInput,
): Promise<BackgroundResolveResult> {
  return adminRequest<BackgroundResolveResult>(
    `${visualPath(worldId)}/resolve-background`,
    {
      method: "POST",
      body: input,
    },
  );
}

export function composeScene(
  worldId: string,
  input: SceneComposeInput,
): Promise<SceneComposeResult> {
  return adminRequest<SceneComposeResult>(`${visualPath(worldId)}/compose-scene`, {
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
