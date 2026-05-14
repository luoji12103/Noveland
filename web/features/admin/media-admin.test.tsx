import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MediaAdmin } from "@/features/admin/media-admin";
import {
  cancelMediaJob,
  listMediaAssets,
  listMediaJobs,
  listMediaReferences,
  retryMediaJob,
  updateMediaAsset,
  uploadMediaAsset,
} from "@/lib/worlds/media";
import type { MediaAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/media", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/media")>("@/lib/worlds/media");
  return {
    ...actual,
    cancelMediaJob: vi.fn(),
    listMediaAssets: vi.fn(),
    listMediaJobs: vi.fn(),
    listMediaReferences: vi.fn(),
    retryMediaJob: vi.fn(),
    updateMediaAsset: vi.fn(),
    uploadMediaAsset: vi.fn(),
  };
});

describe("MediaAdmin", () => {
  it("renders media records without internal storage references", () => {
    render(<MediaAdmin worldId="world-1" data={mediaData} />);

    expect(screen.getByRole("heading", { name: "Media asset overview" })).toBeInTheDocument();
    expect(screen.getByText("Neutral sprite")).toBeInTheDocument();
    expect(screen.getAllByText("character_sprite").length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: "Media objects" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      "/api/worlds/world-1/media/objects/object-1/download",
    );
    expect(screen.queryByText(/media:\/\//)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/var\/noveland/)).not.toBeInTheDocument();
    expect(screen.queryByText(/base64/)).not.toBeInTheDocument();
  });

  it("filters assets, jobs, and references through client helpers", async () => {
    vi.mocked(listMediaAssets).mockResolvedValue([mediaData.assets[0]]);
    vi.mocked(listMediaJobs).mockResolvedValue([mediaData.jobs[0]]);
    vi.mocked(listMediaReferences).mockResolvedValue([mediaData.references[0]]);
    render(<MediaAdmin worldId="world-1" data={mediaData} />);

    fireEvent.change(screen.getByPlaceholderText("metadata search"), {
      target: { value: "sprite" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply asset filters" }));

    await waitFor(() => {
      expect(listMediaAssets).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ contains_text: "sprite", limit: 100 }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("provider kind"), {
      target: { value: "image_generation" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply job filters" }));

    await waitFor(() => {
      expect(listMediaJobs).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ provider_kind: "image_generation", limit: 100 }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("asset id"), {
      target: { value: "asset-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply reference filters" }));

    await waitFor(() => {
      expect(listMediaReferences).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ asset_id: "asset-1", limit: 100 }),
      );
    });
  });

  it("updates assets and keeps upload/action paths explicit", async () => {
    vi.mocked(updateMediaAsset).mockResolvedValue(mediaData.assets[0]);
    vi.mocked(uploadMediaAsset).mockResolvedValue({
      asset: mediaData.assets[0],
      object: mediaData.objectsByAssetId["asset-1"][0],
    });
    vi.mocked(cancelMediaJob).mockResolvedValue(mediaData.jobs[0]);
    render(<MediaAdmin worldId="world-1" data={mediaData} />);

    fireEvent.change(screen.getByDisplayValue("Neutral sprite"), {
      target: { value: "Neutral sprite saved" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save media asset" }));

    await waitFor(() => {
      expect(updateMediaAsset).toHaveBeenCalledWith(
        "world-1",
        "asset-1",
        expect.objectContaining({ title: "Neutral sprite saved" }),
      );
    });

    const fileInput = screen.getByLabelText("Upload file", { selector: "input" });
    fireEvent.change(fileInput, {
      target: { files: [new File(["sprite"], "sprite.png", { type: "image/png" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Upload media asset" }));

    await waitFor(() => {
      expect(uploadMediaAsset).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    await waitFor(() => {
      expect(cancelMediaJob).toHaveBeenCalledWith("world-1", "job-1");
    });
    expect(retryMediaJob).not.toHaveBeenCalled();
  });

  it("shows an ACL state when world management data is unavailable", () => {
    render(
      <MediaAdmin
        worldId="world-1"
        data={{ ...mediaData, canManageSelectedWorld: false, assets: [], jobs: [], references: [] }}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Media administration requires world admin access.",
    );
  });
});

const mediaData: MediaAdminData = {
  worlds: [],
  selectedWorld: null,
  memberships: [],
  assets: [
    {
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
      source_job_id: "job-1",
      source_event_id: null,
      source_invocation_id: null,
      title: "Neutral sprite",
      description: null,
      created_by_actor_ref: "user:admin",
      metadata: { expression: "neutral", storage_uri: "media://hidden-object" },
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  objectsByAssetId: {
    "asset-1": [
      {
        id: "object-1",
        asset_id: "asset-1",
        world_id: "world-1",
        worldline_id: "worldline-1",
        object_role: "original",
        filename: "sprite.png",
        mime_type: "image/png",
        size_bytes: 12,
        checksum_sha256: "a".repeat(64),
        width: 512,
        height: 512,
        duration_ms: null,
        sample_rate_hz: null,
        audio_channels: null,
        frame_rate: null,
        metadata: { storage_uri: "media://hidden-object" },
        created_at: "2026-05-13T00:00:00.000Z",
      },
    ],
  },
  referencesByAssetId: {
    "asset-1": {
      asset_id: "asset-1",
      contexts: [],
      tags: [],
      collections: [],
      input_count: 0,
      output_count: 0,
      tag_count: 0,
      collection_count: 0,
    },
  },
  references: [
    {
      id: "reference-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      asset_id: "asset-1",
      ref_kind: "conversation_turn",
      ref_id: "turn-1",
      ref_role: "attachment",
      display_order: 0,
      metadata: {},
      created_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  jobs: [
    {
      id: "job-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      conversation_id: null,
      turn_id: null,
      agent_id: null,
      job_kind: "upload_import",
      provider_kind: null,
      priority: 1,
      cancel_policy: null,
      deadline_hint: null,
      dedupe_key: null,
      invalidation_key: null,
      source_event_id: null,
      source_invocation_id: null,
      provider_config_json: {},
      request_json: { prompt: "hidden" },
      status: "queued",
      result_json: {},
      error_text: null,
      created_by_actor_ref: "user:admin",
      started_at: null,
      finished_at: null,
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  canManageSelectedWorld: true,
  isPlatformAdmin: true,
  loadError: null,
};
