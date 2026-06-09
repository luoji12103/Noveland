import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { headersMock } = vi.hoisted(() => ({
  headersMock: vi.fn(),
}));

vi.mock("next/headers", () => ({
  headers: headersMock,
}));

import {
  getInvocationLedgerAdminData,
  getMediaAdminData,
  getMultimodalDiagnosticsAdminData,
  getProviderIntegrationAdminData,
  getSpeechAdminData,
  getVisualAdminData,
} from "@/lib/worlds/server";

describe("world server admin loaders", () => {
  beforeEach(() => {
    headersMock.mockResolvedValue({
      get: (name: string) => (name === "cookie" ? "noveland_session=session" : null),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("encodes reserved characters in admin backend path segments", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", apiBase);
    const fetchMock = vi.fn(async (requestUrl: string) => responseFor(requestUrl));
    vi.stubGlobal("fetch", fetchMock);

    await getProviderIntegrationAdminData(worldId, true);
    await getMediaAdminData(worldId, true);
    await getVisualAdminData(worldId, true);
    await getSpeechAdminData(worldId, true);
    await getInvocationLedgerAdminData(worldId, true);
    await getMultimodalDiagnosticsAdminData(worldId, true);

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    const encodedWorld = encodeURIComponent(worldId);
    const encodedProvider = encodeURIComponent(providerId);
    const encodedAsset = encodeURIComponent(assetId);
    const encodedSpriteSet = encodeURIComponent(spriteSetId);
    const encodedAgent = encodeURIComponent(agentId);
    const encodedInvocation = encodeURIComponent(invocationId);
    const encodedWorldline = encodeURIComponent(worldlineId);

    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/providers/${encodedProvider}/capabilities`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/providers/${encodedProvider}/health-checks?limit=10`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/media/assets/${encodedAsset}/objects`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/media/assets/${encodedAsset}/references`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/visual/sprite-sets?worldline_id=${encodedWorldline}`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/visual/sprite-sets/${encodedSpriteSet}/variants`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/agents/${encodedAgent}/voice-profiles?worldline_id=${encodedWorldline}`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/tags`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/prompt-snapshot`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/diagnostics/multimodal?worldline_id=${encodedWorldline}`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/multimodal-evals?worldline_id=${encodedWorldline}&limit=20`,
    );
    expect(urls.join("\n")).not.toContain("/worlds/world/admin?");
  });
});

const apiBase = "http://api.example.test";
const worldId = "world/admin?scope=true#frag";
const providerId = "provider/openai?hidden=true#frag";
const assetId = "asset/image?kind=png#frag";
const spriteSetId = "sprite/set?variant=true#frag";
const agentId = "agent/voice?main=true#frag";
const invocationId = "invoke/raw?prompt=true#frag";
const worldlineId = "worldline/live?branch=1#frag";

function responseFor(requestUrl: string): Response {
  const url = new URL(requestUrl);
  const encodedWorld = encodeURIComponent(worldId);
  const worldPrefix = `/worlds/${encodedWorld}`;

  if (url.pathname === "/worlds") {
    return jsonResponse([{ id: worldId, name: "World" }]);
  }
  if (!url.pathname.startsWith(worldPrefix)) {
    throw new Error(`Unexpected backend URL: ${requestUrl}`);
  }

  if (url.pathname.endsWith("/memberships")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/worldlines")) {
    return jsonResponse([{ id: worldlineId, status: "active", parent_worldline_id: null }]);
  }
  if (url.pathname.endsWith("/providers")) {
    return jsonResponse([{ id: providerId, provider_kind: "text_to_speech" }]);
  }
  if (url.pathname.endsWith("/providers/templates")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/capabilities") || url.pathname.endsWith("/health-checks")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/media/assets")) {
    return jsonResponse([{ id: assetId }]);
  }
  if (url.pathname.endsWith("/media/jobs") || url.pathname.endsWith("/media/references")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/objects")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/references")) {
    return jsonResponse({ asset_id: assetId, references: [] });
  }
  if (url.pathname.endsWith("/agents")) {
    return jsonResponse([{ id: agentId }]);
  }
  if (url.pathname.endsWith("/scenes")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/visual/sprite-sets")) {
    return jsonResponse([{ id: spriteSetId }]);
  }
  if (url.pathname.endsWith("/visual/backgrounds") || url.pathname.endsWith("/variants")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/speech/voice-profiles")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/voice-profiles")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/speech/style-mappings") || url.pathname.endsWith("/speech/transcripts")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/model-invocations")) {
    return jsonResponse({ invocations: [{ id: invocationId }] });
  }
  if (url.pathname.endsWith("/tags")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/prompt-snapshot")) {
    return jsonResponse(null);
  }
  if (url.pathname.endsWith("/diagnostics/multimodal")) {
    return jsonResponse({ findings: [], metrics: [], generated_at: "2026-06-09T00:00:00Z" });
  }
  if (url.pathname.endsWith("/multimodal-evals")) {
    return jsonResponse([]);
  }

  throw new Error(`Unexpected backend URL: ${requestUrl}`);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
