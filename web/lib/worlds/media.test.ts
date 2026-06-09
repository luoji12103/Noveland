import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelMediaJob,
  listMediaAssetReferences,
  listMediaAssets,
  listMediaJobs,
  listMediaObjects,
  listMediaReferences,
  mediaObjectDownloadPath,
  readerMediaObjectDownloadPath,
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

  it("encodes reserved characters in media admin route segments", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(jsonResponse([])))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(mediaAsset))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(mediaJob))
      .mockResolvedValueOnce(jsonResponse(mediaJob))
      .mockResolvedValueOnce(jsonResponse({ asset: mediaAsset, object: mediaObject }));
    vi.stubGlobal("fetch", fetchMock);

    const worldId = "world/alpha?admin=true#frag";
    const assetId = "asset/input?role=source#frag";
    const jobId = "job/retry?force=true#frag";
    const objectId = "object/main?download=1#frag";

    await listMediaAssets(worldId, { contains_text: "sprite/one?x=1#y" });
    await listMediaObjects(worldId, assetId);
    await updateMediaAsset(worldId, assetId, { title: "Encoded" });
    await listMediaAssetReferences(worldId, assetId);
    await listMediaReferences(worldId, { asset_id: assetId });
    await listMediaJobs(worldId, { provider_kind: "fake/provider?x=1#frag" });
    await cancelMediaJob(worldId, jobId);
    await retryMediaJob(worldId, jobId);
    await uploadMediaAsset(worldId, {
      file: new File(["image-bytes"], "sprite.png", { type: "image/png" }),
      asset_kind: "image",
      asset_role: "character_sprite",
      visibility: "world_admin",
    });

    const encodedWorld = encodeURIComponent(worldId);
    const encodedAsset = encodeURIComponent(assetId);
    const encodedJob = encodeURIComponent(jobId);
    const calls = fetchMock.mock.calls.map((call) => call[0]);

    expect(calls).toEqual([
      `/api/worlds/${encodedWorld}/media/assets?contains_text=sprite%2Fone%3Fx%3D1%23y`,
      `/api/worlds/${encodedWorld}/media/assets/${encodedAsset}/objects`,
      `/api/worlds/${encodedWorld}/media/assets/${encodedAsset}`,
      `/api/worlds/${encodedWorld}/media/assets/${encodedAsset}/references`,
      `/api/worlds/${encodedWorld}/media/references?asset_id=asset%2Finput%3Frole%3Dsource%23frag`,
      `/api/worlds/${encodedWorld}/media/jobs?provider_kind=fake%2Fprovider%3Fx%3D1%23frag`,
      `/api/worlds/${encodedWorld}/media/jobs/${encodedJob}/cancel`,
      `/api/worlds/${encodedWorld}/media/jobs/${encodedJob}/retry`,
      `/api/worlds/${encodedWorld}/media/assets/upload`,
    ]);
    expect(mediaObjectDownloadPath(worldId, objectId)).toBe(
      `/api/worlds/${encodedWorld}/media/objects/${encodeURIComponent(objectId)}/download`,
    );
  });

  it("builds safe backend download paths from object ids only", () => {
    expect(mediaObjectDownloadPath("world-1", "object-1")).toBe(
      "/api/worlds/world-1/media/objects/object-1/download",
    );
    expect(
      readerMediaObjectDownloadPath("/worlds/world-1/reader/media/objects/object-1/download"),
    ).toBe("/api/worlds/world-1/reader/media/objects/object-1/download");
    expect(readerMediaObjectDownloadPath("media://hidden/object")).toBe("");
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
