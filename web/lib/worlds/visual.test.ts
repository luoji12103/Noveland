import { afterEach, describe, expect, it, vi } from "vitest";

import {
  composeScene,
  createSceneBackground,
  createSpriteSet,
  createSpriteVariant,
  deleteSceneBackground,
  deleteSpriteSet,
  deleteSpriteVariant,
  listSceneBackgrounds,
  listSpriteSets,
  listSpriteVariants,
  resolveBackground,
  resolveSprite,
  updateSceneBackground,
  updateSpriteSet,
  updateSpriteVariant,
} from "@/lib/worlds/visual";

describe("visual admin client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("lists visual records through strict worldline-scoped world proxy paths", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse([])));
    vi.stubGlobal("fetch", fetchMock);

    await listSpriteSets("world-1", { worldline_id: "worldline-1", agent_id: "agent-1" });
    await listSpriteVariants("world-1", "sprite-set-1");
    await listSceneBackgrounds("world-1", { worldline_id: "worldline-1" });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/visual/sprite-sets?worldline_id=worldline-1&agent_id=agent-1",
      "/api/worlds/world-1/visual/sprite-sets/sprite-set-1/variants",
      "/api/worlds/world-1/visual/backgrounds?worldline_id=worldline-1",
    ]);
  });

  it("uses csrf for visual binding writes and deletes", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(spriteSet))
      .mockResolvedValueOnce(jsonResponse(spriteSet))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(spriteVariant))
      .mockResolvedValueOnce(jsonResponse(spriteVariant))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(sceneBackground))
      .mockResolvedValueOnce(jsonResponse(sceneBackground))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await createSpriteSet("world-1", {
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      style_key: "default",
      display_name: "Akari default",
      status: "active",
      visibility: "world_admin",
      metadata_json: {},
    });
    await updateSpriteSet("world-1", "sprite-set-1", { display_name: "Akari saved" });
    await deleteSpriteSet("world-1", "sprite-set-1");
    await createSpriteVariant("world-1", "sprite-set-1", {
      worldline_id: "worldline-1",
      asset_id: "asset-1",
      expression_key: "neutral",
      mood_tags: [],
      priority: 100,
      is_default: true,
      status: "active",
      visibility: "world_admin",
      metadata_json: {},
    });
    await updateSpriteVariant("world-1", "sprite-set-1", "variant-1", { expression_key: "happy" });
    await deleteSpriteVariant("world-1", "sprite-set-1", "variant-1");
    await createSceneBackground("world-1", {
      worldline_id: "worldline-1",
      location_key: "school_rooftop",
      asset_id: "background-asset-1",
      priority: 100,
      is_default: true,
      status: "active",
      visibility: "world_admin",
      metadata_json: {},
    });
    await updateSceneBackground("world-1", "background-1", { weather_key: "clear" });
    await deleteSceneBackground("world-1", "background-1");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/visual/sprite-sets",
      "/api/worlds/world-1/visual/sprite-sets/sprite-set-1",
      "/api/worlds/world-1/visual/sprite-sets/sprite-set-1",
      "/api/worlds/world-1/visual/sprite-sets/sprite-set-1/variants",
      "/api/worlds/world-1/visual/sprite-sets/sprite-set-1/variants/variant-1",
      "/api/worlds/world-1/visual/sprite-sets/sprite-set-1/variants/variant-1",
      "/api/worlds/world-1/visual/backgrounds",
      "/api/worlds/world-1/visual/backgrounds/background-1",
      "/api/worlds/world-1/visual/backgrounds/background-1",
    ]);
    for (const call of fetchMock.mock.calls) {
      expect((call[1].headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    }
  });

  it("uses csrf for resolver previews and compose scene", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(spriteResolveResult))
      .mockResolvedValueOnce(jsonResponse(backgroundResolveResult))
      .mockResolvedValueOnce(jsonResponse(composeResult));
    vi.stubGlobal("fetch", fetchMock);

    await resolveSprite("world-1", {
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      expression_key: "happy",
    });
    await resolveBackground("world-1", {
      worldline_id: "worldline-1",
      location_key: "school_rooftop",
    });
    await composeScene("world-1", {
      worldline_id: "worldline-1",
      background_asset_id: "background-asset-1",
      layers: [{ asset_id: "asset-1", x: 100, y: 120, z_index: 1 }],
      metadata_json: { purpose: "admin_preview" },
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/visual/resolve-sprite",
      "/api/worlds/world-1/visual/resolve-background",
      "/api/worlds/world-1/visual/compose-scene",
    ]);
    for (const call of fetchMock.mock.calls) {
      expect((call[1].headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    }
    expect(fetchMock.mock.calls[2][0]).not.toContain("media://");
  });

  it("encodes visual admin API identifier path segments", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(spriteSet))
      .mockResolvedValueOnce(jsonResponse(spriteSet))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(spriteVariant))
      .mockResolvedValueOnce(jsonResponse(spriteVariant))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(spriteResolveResult))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(sceneBackground))
      .mockResolvedValueOnce(jsonResponse(sceneBackground))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(backgroundResolveResult))
      .mockResolvedValueOnce(jsonResponse(composeResult));
    vi.stubGlobal("fetch", fetchMock);

    const worldId = "world/visual?tab=admin#frag";
    const spriteSetId = "sprite/set?agent=akari#frag";
    const variantId = "variant/happy?pose=front#frag";
    const backgroundId = "background/roof?weather=clear#frag";

    await listSpriteSets(worldId, {
      worldline_id: "worldline/main?branch=1#frag",
      agent_id: "agent/main?role=hero#frag",
    });
    await createSpriteSet(worldId, {
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      style_key: "default",
      display_name: "Akari default",
      status: "active",
      visibility: "world_admin",
      metadata_json: {},
    });
    await updateSpriteSet(worldId, spriteSetId, { display_name: "Akari saved" });
    await deleteSpriteSet(worldId, spriteSetId);
    await listSpriteVariants(worldId, spriteSetId);
    await createSpriteVariant(worldId, spriteSetId, {
      worldline_id: "worldline-1",
      asset_id: "asset-1",
      expression_key: "neutral",
      mood_tags: [],
      priority: 100,
      is_default: true,
      status: "active",
      visibility: "world_admin",
      metadata_json: {},
    });
    await updateSpriteVariant(worldId, spriteSetId, variantId, { expression_key: "happy" });
    await deleteSpriteVariant(worldId, spriteSetId, variantId);
    await resolveSprite(worldId, { worldline_id: "worldline-1", agent_id: "agent-1", expression_key: "happy" });
    await listSceneBackgrounds(worldId, { worldline_id: "worldline/main?branch=1#frag" });
    await createSceneBackground(worldId, {
      worldline_id: "worldline-1",
      location_key: "school_rooftop",
      asset_id: "background-asset-1",
      priority: 100,
      is_default: true,
      status: "active",
      visibility: "world_admin",
      metadata_json: {},
    });
    await updateSceneBackground(worldId, backgroundId, { weather_key: "clear" });
    await deleteSceneBackground(worldId, backgroundId);
    await resolveBackground(worldId, { worldline_id: "worldline-1", location_key: "school_rooftop" });
    await composeScene(worldId, {
      worldline_id: "worldline-1",
      background_asset_id: "background-asset-1",
      layers: [{ asset_id: "asset-1", x: 100, y: 120, z_index: 1 }],
      metadata_json: { purpose: "admin_preview" },
    });

    const worldSegment = encodeURIComponent(worldId);
    const spriteSetSegment = encodeURIComponent(spriteSetId);
    const variantSegment = encodeURIComponent(variantId);
    const backgroundSegment = encodeURIComponent(backgroundId);
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/" + worldSegment + "/visual/sprite-sets?worldline_id=worldline%2Fmain%3Fbranch%3D1%23frag&agent_id=agent%2Fmain%3Frole%3Dhero%23frag",
      "/api/worlds/" + worldSegment + "/visual/sprite-sets",
      "/api/worlds/" + worldSegment + "/visual/sprite-sets/" + spriteSetSegment,
      "/api/worlds/" + worldSegment + "/visual/sprite-sets/" + spriteSetSegment,
      "/api/worlds/" + worldSegment + "/visual/sprite-sets/" + spriteSetSegment + "/variants",
      "/api/worlds/" + worldSegment + "/visual/sprite-sets/" + spriteSetSegment + "/variants",
      "/api/worlds/" + worldSegment + "/visual/sprite-sets/" + spriteSetSegment + "/variants/" + variantSegment,
      "/api/worlds/" + worldSegment + "/visual/sprite-sets/" + spriteSetSegment + "/variants/" + variantSegment,
      "/api/worlds/" + worldSegment + "/visual/resolve-sprite",
      "/api/worlds/" + worldSegment + "/visual/backgrounds?worldline_id=worldline%2Fmain%3Fbranch%3D1%23frag",
      "/api/worlds/" + worldSegment + "/visual/backgrounds",
      "/api/worlds/" + worldSegment + "/visual/backgrounds/" + backgroundSegment,
      "/api/worlds/" + worldSegment + "/visual/backgrounds/" + backgroundSegment,
      "/api/worlds/" + worldSegment + "/visual/resolve-background",
      "/api/worlds/" + worldSegment + "/visual/compose-scene",
    ]);
  });
});

const spriteSet = {
  id: "sprite-set-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  agent_id: "agent-1",
  style_key: "default",
  display_name: "Akari default",
  default_variant_id: "variant-1",
  status: "active",
  visibility: "world_admin",
  metadata_json: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const spriteVariant = {
  id: "variant-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  sprite_set_id: "sprite-set-1",
  asset_id: "asset-1",
  expression_key: "neutral",
  pose_key: null,
  outfit_key: null,
  mood_tags: [],
  priority: 100,
  is_default: true,
  status: "active",
  visibility: "world_admin",
  metadata_json: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const sceneBackground = {
  id: "background-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  scene_id: "scene-1",
  location_key: "school_rooftop",
  time_of_day: "evening",
  weather_key: null,
  asset_id: "background-asset-1",
  priority: 100,
  is_default: true,
  status: "active",
  visibility: "world_admin",
  metadata_json: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const visualAssetRef = {
  id: "asset-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  asset_kind: "image",
  asset_role: "character_sprite",
  source_kind: "manual_upload",
  status: "available",
  visibility: "world_admin",
  mime_type: "image/png",
  file_ext: "png",
  size_bytes: 12,
  checksum_sha256: "a".repeat(64),
  width: 512,
  height: 512,
  has_alpha: true,
  title: "Akari neutral",
  description: null,
  metadata: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const spriteResolveResult = {
  sprite_set: spriteSet,
  variant: spriteVariant,
  asset: visualAssetRef,
  fallback_reason: null,
  confidence: 1,
};

const backgroundResolveResult = {
  background: sceneBackground,
  asset: { ...visualAssetRef, id: "background-asset-1", asset_role: "scene_background" },
  fallback_reason: "default_background",
  confidence: 0.8,
};

const composeResult = {
  media_job: {
    id: "job-1",
    world_id: "world-1",
    worldline_id: "worldline-1",
    conversation_id: null,
    turn_id: null,
    agent_id: null,
    job_kind: "composition",
    provider_kind: null,
    priority: 100,
    cancel_policy: null,
    deadline_hint: null,
    dedupe_key: null,
    invalidation_key: null,
    source_event_id: null,
    source_invocation_id: null,
    provider_config_json: {},
    request_json: {},
    status: "succeeded",
    result_json: {},
    error_text: null,
    created_by_actor_ref: "user:admin",
    started_at: null,
    finished_at: "2026-05-13T00:00:00.000Z",
    created_at: "2026-05-13T00:00:00.000Z",
    updated_at: "2026-05-13T00:00:00.000Z",
  },
  output_asset: { ...visualAssetRef, id: "composite-asset-1", asset_role: "composite_image" },
  output_objects: [],
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
