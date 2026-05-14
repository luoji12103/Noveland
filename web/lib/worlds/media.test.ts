import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelMediaJob,
  listMediaAssets,
  listMediaJobs,
  listMediaObjects,
  listMediaReferences,
  mediaObjectDownloadPath,
  retryMediaJob,
  updateMediaAsset,
  uploadMediaAsset,
} from "@/lib/worlds/media";

describe("media admin client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("lists media assets, objects, references, and jobs through the world proxy", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse([])));
    vi.stubGlobal("fetch", fetchMock);

    await listMediaAssets("world-1", {
      asset_kind: "image",
      status: "available",
      visibility: "world_admin",
    });
    await listMediaObjects("world-1", "asset-1");
    await listMediaReferences("world-1", { asset_id: "asset-1" });
    await listMediaJobs("world-1", { job_kind: "upload_import", status: "queued" });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/media/assets?asset_kind=image&status=available&visibility=world_admin",
      "/api/worlds/world-1/media/assets/asset-1/objects",
      "/api/worlds/world-1/media/references?asset_id=asset-1",
      "/api/worlds/world-1/media/jobs?job_kind=upload_import&status=queued",
    ]);
  });

  it("updates assets and uses explicit job actions with csrf", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(mediaAsset))
      .mockResolvedValueOnce(jsonResponse(mediaJob))
      .mockResolvedValueOnce(jsonResponse(mediaJob));
    vi.stubGlobal("fetch", fetchMock);

    await updateMediaAsset("world-1", "asset-1", {
      title: "Background",
      status: "available",
      visibility: "world_admin",
    });
    await cancelMediaJob("world-1", "job-1");
    await retryMediaJob("world-1", "job-1");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/media/assets/asset-1",
      "/api/worlds/world-1/media/jobs/job-1/cancel",
      "/api/worlds/world-1/media/jobs/job-1/retry",
    ]);
    for (const call of fetchMock.mock.calls) {
      expect((call[1].headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    }
  });

  it("uploads media with multipart form data and no storage path in the request URL", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ asset: mediaAsset, object: mediaObject }));
    vi.stubGlobal("fetch", fetchMock);

    await uploadMediaAsset("world-1", {
      file: new File(["image-bytes"], "sprite.png", { type: "image/png" }),
      worldline_id: "worldline-1",
      asset_kind: "image",
      asset_role: "character_sprite",
      visibility: "world_admin",
      title: "Sprite",
      metadata: { expression: "neutral" },
    });

    const [url, request] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/worlds/world-1/media/assets/upload");
    expect(request.method).toBe("POST");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(request.body).toBeInstanceOf(FormData);
    expect(url).not.toContain("media://");
  });

  it("builds safe backend download paths from object ids only", () => {
    expect(mediaObjectDownloadPath("world-1", "object-1")).toBe(
      "/api/worlds/world-1/media/objects/object-1/download",
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
  size_bytes: 11,
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
  title: "Sprite",
  description: null,
  created_by_actor_ref: "user:admin",
  metadata: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const mediaObject = {
  id: "object-1",
  asset_id: "asset-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  object_role: "original",
  filename: "sprite.png",
  mime_type: "image/png",
  size_bytes: 11,
  checksum_sha256: "a".repeat(64),
  width: 512,
  height: 512,
  duration_ms: null,
  sample_rate_hz: null,
  audio_channels: null,
  frame_rate: null,
  metadata: {},
  created_at: "2026-05-13T00:00:00.000Z",
};

const mediaJob = {
  id: "job-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  conversation_id: null,
  turn_id: null,
  agent_id: null,
  job_kind: "upload_import",
  provider_kind: null,
  priority: 0,
  cancel_policy: null,
  deadline_hint: null,
  dedupe_key: null,
  invalidation_key: null,
  source_event_id: null,
  source_invocation_id: null,
  provider_config_json: {},
  request_json: {},
  status: "queued",
  result_json: {},
  error_text: null,
  created_by_actor_ref: "user:admin",
  started_at: null,
  finished_at: null,
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
