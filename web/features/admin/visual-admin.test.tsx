import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VisualAdmin } from "@/features/admin/visual-admin";
import {
  composeScene,
  createSpriteSet,
  createSpriteVariant,
  listSceneBackgrounds,
  listSpriteSets,
  listSpriteVariants,
  resolveBackground,
  resolveSprite,
  updateSpriteSet,
  updateSpriteVariant,
} from "@/lib/worlds/visual";
import type { SceneComposeResult } from "@/lib/worlds/visual";
import type { VisualAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/visual", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/visual")>("@/lib/worlds/visual");
  return {
    ...actual,
    composeScene: vi.fn(),
    createSceneBackground: vi.fn(),
    createSpriteSet: vi.fn(),
    createSpriteVariant: vi.fn(),
    deleteSceneBackground: vi.fn(),
    deleteSpriteSet: vi.fn(),
    deleteSpriteVariant: vi.fn(),
    listSceneBackgrounds: vi.fn(),
    listSpriteSets: vi.fn(),
    listSpriteVariants: vi.fn(),
    resolveBackground: vi.fn(),
    resolveSprite: vi.fn(),
    updateSceneBackground: vi.fn(),
    updateSpriteSet: vi.fn(),
    updateSpriteVariant: vi.fn(),
  };
});

describe("VisualAdmin", () => {
  it("renders visual bindings without storage paths or raw payloads", () => {
    render(<VisualAdmin worldId="world-1" data={visualData} />);

    expect(screen.getByRole("heading", { name: "Visual asset overview" })).toBeInTheDocument();
    expect(screen.getByText("Akari default")).toBeInTheDocument();
    expect(screen.getAllByText("neutral").length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: "Sprite variants" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Scene backgrounds" })).toBeInTheDocument();
    expect(screen.queryByText(/media:\/\//)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/var\/noveland/)).not.toBeInTheDocument();
    expect(screen.queryByText(/base64/)).not.toBeInTheDocument();
    expect(screen.queryByText(/raw prompt/)).not.toBeInTheDocument();
  });

  it("loads selected worldline records and writes sprite bindings through helpers", async () => {
    vi.mocked(listSpriteSets).mockResolvedValue([visualData.spriteSets[0]]);
    vi.mocked(listSpriteVariants).mockResolvedValue([visualData.variantsBySpriteSetId["sprite-set-1"][0]]);
    vi.mocked(listSceneBackgrounds).mockResolvedValue([visualData.backgrounds[0]]);
    vi.mocked(createSpriteSet).mockResolvedValue(visualData.spriteSets[0]);
    vi.mocked(createSpriteVariant).mockResolvedValue(visualData.variantsBySpriteSetId["sprite-set-1"][0]);
    vi.mocked(updateSpriteSet).mockResolvedValue(visualData.spriteSets[0]);
    vi.mocked(updateSpriteVariant).mockResolvedValue(visualData.variantsBySpriteSetId["sprite-set-1"][0]);
    render(<VisualAdmin worldId="world-1" data={visualData} />);

    fireEvent.click(screen.getByRole("button", { name: "Load visual records" }));

    await waitFor(() => {
      expect(listSpriteSets).toHaveBeenCalledWith("world-1", { worldline_id: "worldline-1" });
    });

    fireEvent.change(screen.getByPlaceholderText("Display name"), {
      target: { value: "Akari alternate" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create sprite set" }));

    await waitFor(() => {
      expect(createSpriteSet).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          agent_id: "agent-1",
          display_name: "Akari alternate",
        }),
      );
    });

    fireEvent.change(screen.getByDisplayValue("Akari default"), {
      target: { value: "Akari saved" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save sprite set" }));

    await waitFor(() => {
      expect(updateSpriteSet).toHaveBeenCalledWith(
        "world-1",
        "sprite-set-1",
        expect.objectContaining({ display_name: "Akari saved" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Add variant" }));

    await waitFor(() => {
      expect(createSpriteVariant).toHaveBeenCalledWith(
        "world-1",
        "sprite-set-1",
        expect.objectContaining({ worldline_id: "worldline-1", asset_id: "asset-1" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Save variant" }));

    await waitFor(() => {
      expect(updateSpriteVariant).toHaveBeenCalledWith(
        "world-1",
        "sprite-set-1",
        "variant-1",
        expect.objectContaining({ asset_id: "asset-1", expression_key: "neutral" }),
      );
    });
  });

  it("runs resolver previews and explicit compose scene actions", async () => {
    vi.mocked(resolveSprite).mockResolvedValue(spriteResolveResult);
    vi.mocked(resolveBackground).mockResolvedValue(backgroundResolveResult);
    vi.mocked(composeScene).mockResolvedValue(composeResult);
    render(<VisualAdmin worldId="world-1" data={visualData} />);

    fireEvent.click(screen.getByRole("button", { name: "Resolve sprite" }));

    await waitFor(() => {
      expect(resolveSprite).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ worldline_id: "worldline-1", agent_id: "agent-1" }),
      );
    });
    expect(await screen.findByText("Sprite asset")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Resolve background" }));

    await waitFor(() => {
      expect(resolveBackground).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ worldline_id: "worldline-1", location_key: "school_rooftop" }),
      );
    });
    expect(await screen.findByText("default_background")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Compose scene" }));

    await waitFor(() => {
      expect(composeScene).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          background_asset_id: "background-asset-1",
        }),
      );
    });
    expect(await screen.findByText("composite-asset-1")).toBeInTheDocument();
  });

  it("shows an ACL state when world management data is unavailable", () => {
    render(
      <VisualAdmin
        worldId="world-1"
        data={{
          ...visualData,
          canManageSelectedWorld: false,
          spriteSets: [],
          variantsBySpriteSetId: {},
          backgrounds: [],
        }}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Visual administration requires world admin access.",
    );
  });
});

const mediaAsset = {
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
  duration_ms: null,
  sample_rate_hz: null,
  audio_channels: null,
  has_alpha: true,
  color_mode: "rgba",
  provider_kind: null,
  source_job_id: null,
  source_event_id: null,
  source_invocation_id: null,
  title: "Akari neutral",
  description: null,
  created_by_actor_ref: "user:admin",
  metadata: { storage_uri: "media://hidden-object", prompt: "raw prompt" },
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
} as const;

const backgroundAsset = {
  ...mediaAsset,
  id: "background-asset-1",
  asset_role: "scene_background",
  title: "Rooftop background",
} as const;

const visualData: VisualAdminData = {
  worlds: [],
  selectedWorld: null,
  memberships: [],
  worldlines: [
    {
      id: "worldline-1",
      world_id: "world-1",
      worldline_key: "main",
      name: "Main",
      description: null,
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: null,
      status: "active",
      created_by_actor_ref: "user:admin",
      metadata: {},
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  selectedWorldlineId: "worldline-1",
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      source_preset_id: null,
      source_preset_version: null,
      agent_key: "akari",
      display_name: "Akari",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
  ],
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "school_rooftop",
      name: "School rooftop",
      description: null,
      region_key: null,
      location_tags: [],
      opening_rules: {},
      is_active: true,
    },
  ],
  imageAssets: [mediaAsset, backgroundAsset],
  spriteSets: [
    {
      id: "sprite-set-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      style_key: "default",
      display_name: "Akari default",
      default_variant_id: "variant-1",
      status: "active",
      visibility: "world_admin",
      metadata_json: { storage_uri: "media://hidden-sprite" },
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  variantsBySpriteSetId: {
    "sprite-set-1": [
      {
        id: "variant-1",
        world_id: "world-1",
        worldline_id: "worldline-1",
        sprite_set_id: "sprite-set-1",
        asset_id: "asset-1",
        expression_key: "neutral",
        pose_key: "standing",
        outfit_key: null,
        mood_tags: ["calm"],
        priority: 100,
        is_default: true,
        status: "active",
        visibility: "world_admin",
        metadata_json: { base64_preview: "base64-secret" },
        created_at: "2026-05-13T00:00:00.000Z",
        updated_at: "2026-05-13T00:00:00.000Z",
      },
    ],
  },
  backgrounds: [
    {
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
      metadata_json: { filesystem_path: "/var/noveland/media/background.png" },
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  canManageSelectedWorld: true,
  isPlatformAdmin: false,
  loadError: null,
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
  sprite_set: visualData.spriteSets[0],
  variant: visualData.variantsBySpriteSetId["sprite-set-1"][0],
  asset: visualAssetRef,
  fallback_reason: null,
  confidence: 1,
};

const backgroundResolveResult = {
  background: visualData.backgrounds[0],
  asset: { ...visualAssetRef, id: "background-asset-1", asset_role: "scene_background" },
  fallback_reason: "default_background",
  confidence: 0.8,
};

const composeResult: SceneComposeResult = {
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
