import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { headersMock } = vi.hoisted(() => ({
  headersMock: vi.fn(),
}));

vi.mock("next/headers", () => ({
  headers: headersMock,
}));

import {
  getAgentDetailData,
  getConversationDetailData,
  getConversationPlaybackData,
  getInvocationLedgerAdminData,
  getMediaAdminData,
  getMemoryBackendAdminData,
  getMultimodalDiagnosticsAdminData,
  getNarrativeReaderDetailData,
  getPlayerInteractionData,
  getProviderIntegrationAdminData,
  getSpeechAdminData,
  getVisualAdminData,
  getWorldWorkspaceData,
  getWorldsIndexData,
  getWorldlineBrowserData,
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

  it("normalizes sensitive backend error details before throwing", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", apiBase);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          { detail: "World index failed with clientSecret sk-world-server and storageUri media://world/index" },
          500,
        ),
      ),
    );

    await expect(getWorldsIndexData()).rejects.toMatchObject({ message: "World request failed.", status: 500 });
  });

  it("sanitizes world workspace data before client prop serialization", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", apiBase);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (requestUrl: string) => responseForDirtyWorkspaceLoader(requestUrl)),
    );

    const data = await getWorldWorkspaceData(worldId, true);
    const serialized = JSON.stringify(data);

    expect(serialized).toContain("safeWorldSetting");
    expect(serialized).toContain("safeBibleMetadata");
    expect(serialized).toContain("safeReleaseMetadata");
    expect(serialized).toContain("safeEvent");
    expect(serialized).toContain("safeDiagnostic");
    expect(serialized).not.toMatch(
      /clientSecret|sk-workspace-secret|storageUri|media:\/\/workspace|rawPrompt|rawOutput|promptSnapshotId|Bearer workspace-token|\/tmp\/workspace|\/root\/workspace|s3:\/\/workspace|YWJjZGVmZ2hpamtsbW5vcA/i,
    );
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

  it("encodes reserved characters in workspace server loader backend path segments", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", apiBase);
    const fetchMock = vi.fn(async (requestUrl: string) => responseForWorkspaceLoader(requestUrl));
    vi.stubGlobal("fetch", fetchMock);

    await getWorldWorkspaceData(worldId, true);
    await getAgentDetailData(worldId, agentId, true);
    await getConversationDetailData(worldId, conversationId);
    await getConversationPlaybackData(worldId, conversationId);
    await getPlayerInteractionData(worldId, userId);
    await getWorldlineBrowserData(worldId, worldlineId, compareWorldlineId);
    await getNarrativeReaderDetailData(worldId, artifactId);
    await getMemoryBackendAdminData();

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    const encodedWorld = encodeURIComponent(worldId);
    const encodedAgent = encodeURIComponent(agentId);
    const encodedConversation = encodeURIComponent(conversationId);
    const encodedTurn = encodeURIComponent(turnId);
    const encodedOrganization = encodeURIComponent(organizationId);
    const encodedChecklistRun = encodeURIComponent(checklistRunId);
    const encodedWorldline = encodeURIComponent(worldlineId);
    const encodedCompareWorldline = encodeURIComponent(compareWorldlineId);
    const encodedArtifact = encodeURIComponent(artifactId);
    const encodedMemoryProfile = encodeURIComponent(memoryProfileId);

    expect(urls).toContain(`${apiBase}/worlds/${encodedWorld}/agents/${encodedAgent}/presence`);
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/organizations/${encodedOrganization}/memberships`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/beta-checklists/${encodedChecklistRun}/items`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/conversations/${encodedConversation}/turns`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/conversations/${encodedConversation}/turns/${encodedTurn}/presentation`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/worldlines/${encodedWorldline}/compare/${encodedCompareWorldline}`,
    );
    expect(urls).toContain(
      `${apiBase}/worlds/${encodedWorld}/narrative-artifacts/${encodedArtifact}`,
    );
    expect(urls).toContain(`${apiBase}/memory-backend-profiles/${encodedMemoryProfile}/health`);
    expect(urls.join("\n")).not.toContain("/worlds/world/admin?");
    expect(urls.join("\n")).not.toContain("/agents/agent/detail?");
    expect(urls.join("\n")).not.toContain("/conversations/conversation/live?");
    expect(urls.join("\n")).not.toContain("/memory-backend-profiles/memory/profile?");
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
const compareWorldlineId = "worldline/compare?branch=2#frag";
const conversationId = "conversation/live?debug=true#frag";
const turnId = "turn/live?presentation=true#frag";
const artifactId = "artifact/reader?draft=false#frag";
const organizationId = "organization/main?view=admin#frag";
const checklistRunId = "checklist/run?items=true#frag";
const memoryProfileId = "memory/profile?logs=true#frag";
const userId = "user/player?scope=member#frag";

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

function responseForDirtyWorkspaceLoader(requestUrl: string): Response {
  const url = new URL(requestUrl);
  const encodedWorld = encodeURIComponent(worldId);
  const worldPrefix = `/worlds/${encodedWorld}`;

  if (url.pathname === "/worlds") {
    return jsonResponse([
      {
        id: worldId,
        name: "World",
        memory_plugin_config: { safeWorldSetting: true, rawPrompt: "system prompt" },
        world_rules_plugin_config: {
          safeWorldRules: true,
          clientSecret: "sk-workspace-secret",
          nested: { storageUri: "media://workspace/rules" },
        },
      },
    ]);
  }

  if (!url.pathname.startsWith(worldPrefix)) {
    return responseForWorkspaceLoader(requestUrl);
  }

  if (url.pathname.endsWith("/bible")) {
    return jsonResponse({
      id: "bible-1",
      world_id: worldId,
      canon_timeline: [{ safeBibleEvent: "festival", rawOutput: "model output" }],
      setting_rules: { safeSetting: "public", filePath: "/tmp/workspace/bible.json" },
      forbidden_changes: [{ rule: "no retcon", storageUri: "media://workspace/forbidden" }],
      sequel_boundaries: { safeBoundary: true, bearerToken: "Bearer workspace-token" },
      continuity_config: { safeContinuity: true, promptSnapshotId: "snapshot-workspace" },
      metadata: { safeBibleMetadata: true, bytes: "YWJjZGVmZ2hpamtsbW5vcA" },
    });
  }

  if (url.pathname.endsWith("/release-profile")) {
    return jsonResponse({
      id: "release-1",
      world_id: worldId,
      branch_policy: { safeReleaseBranch: true, storageUri: "s3://workspace/release" },
      backup_policy: { safeBackup: true, rawPrompt: "backup prompt" },
      content_review_policy: { safeReview: true },
      player_permission_policy: { safePermission: true, clientSecret: "sk-workspace-secret" },
      worldline_policy: { safeWorldline: true },
      checklist: { safeChecklist: true, localModelPath: "/models/workspace.bin" },
      metadata: { safeReleaseMetadata: true, bearerToken: "Bearer workspace-token" },
    });
  }

  if (url.pathname.endsWith("/events")) {
    return jsonResponse([
      {
        id: "event-1",
        event_type: "world.note",
        payload: { safeEvent: "visible", rawPrompt: "event prompt", storageUri: "media://workspace/event" },
      },
    ]);
  }

  if (url.pathname.endsWith("/daily-life/preview")) {
    return jsonResponse({ safePreview: true, diagnostics: { rawOutput: "preview output" } });
  }

  if (url.pathname.endsWith("/daily-life/candidates")) {
    return jsonResponse([{ id: "candidate-1", payload: { safeCandidate: true, promptSnapshotId: "snapshot-workspace" } }]);
  }

  if (url.pathname.endsWith("/offscreen-events")) {
    return jsonResponse([{ id: "offscreen-1", payload: { safeOffscreen: true, filePath: "/root/workspace/offscreen.json" } }]);
  }

  if (url.pathname.endsWith("/diagnostics")) {
    return jsonResponse([{ id: "diagnostic-1", message: "safeDiagnostic", metadata: { clientSecret: "sk-workspace-secret" } }]);
  }

  if (url.pathname.endsWith("/schedule-rules")) {
    return jsonResponse([{ id: "schedule-1", config: { safeSchedule: true, rawPrompt: "schedule prompt" } }]);
  }

  return responseForWorkspaceLoader(requestUrl);
}

function responseForWorkspaceLoader(requestUrl: string): Response {
  const url = new URL(requestUrl);
  const encodedWorld = encodeURIComponent(worldId);
  const worldPrefix = `/worlds/${encodedWorld}`;

  if (url.pathname === "/worlds") {
    return jsonResponse([{ id: worldId, name: "World" }]);
  }
  if (url.pathname === "/plugins/catalog") {
    return jsonResponse([]);
  }
  if (url.pathname === "/provider-profiles" || url.pathname === "/agent-presets") {
    return jsonResponse([]);
  }
  if (url.pathname === "/memory-backend-profiles") {
    return jsonResponse([{ id: memoryProfileId, profile_key: "mem0", display_name: "Mem0" }]);
  }
  if (url.pathname === `/memory-backend-profiles/${encodeURIComponent(memoryProfileId)}/health`) {
    return jsonResponse({ status: "healthy" });
  }
  if (url.pathname === `/memory-backend-profiles/${encodeURIComponent(memoryProfileId)}/logs`) {
    return jsonResponse({ write_logs: [], retrieval_logs: [] });
  }
  if (url.pathname === `/memory-backend-profiles/${encodeURIComponent(memoryProfileId)}/jobs`) {
    return jsonResponse({ jobs: [], total: 0 });
  }
  if (url.pathname === "/memory-backfill/dry-run") {
    return jsonResponse({ backend: "memory", deleted_count: null });
  }
  if (!url.pathname.startsWith(worldPrefix)) {
    return jsonResponse([]);
  }

  if (url.pathname.endsWith("/agents")) {
    return jsonResponse([{ id: agentId, name: "Agent" }]);
  }
  if (url.pathname.endsWith("/organizations")) {
    return jsonResponse([{ id: organizationId, name: "Organization" }]);
  }
  if (url.pathname.endsWith("/worldlines")) {
    return jsonResponse([
      { id: worldlineId, status: "active", parent_worldline_id: null },
      { id: compareWorldlineId, status: "active", parent_worldline_id: worldlineId },
    ]);
  }
  if (url.pathname.endsWith("/conversations")) {
    return jsonResponse([{ id: conversationId, worldline_id: worldlineId, title: "Conversation" }]);
  }
  if (url.pathname.endsWith("/turns")) {
    return jsonResponse([{ id: turnId, speaker: "Agent" }]);
  }
  if (url.pathname.endsWith("/player-actors")) {
    return jsonResponse([{ id: "player-actor-1", user_id: userId }]);
  }
  if (url.pathname.endsWith("/beta-checklists")) {
    return jsonResponse([{ id: checklistRunId, status: "blocked" }]);
  }
  if (url.pathname.endsWith("/narrative-artifacts")) {
    return jsonResponse([{ id: artifactId, title: "Artifact" }]);
  }
  if (url.pathname.endsWith(`/${encodeURIComponent(artifactId)}`)) {
    return jsonResponse({ id: artifactId, title: "Artifact" });
  }
  if (url.pathname.endsWith("/clock") || url.pathname.endsWith("/replay/state")) {
    return jsonResponse({});
  }
  if (url.pathname.endsWith("/bible") || url.pathname.endsWith("/snapshots/latest")) {
    return jsonResponse(null);
  }
  if (url.pathname.endsWith("/presentation")) {
    return jsonResponse(null);
  }
  if (url.pathname.includes("/compare/")) {
    return jsonResponse({ base_worldline_id: worldlineId, compare_worldline_id: compareWorldlineId });
  }
  if (url.pathname.endsWith("/reader/media")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/player-sessions/resume")) {
    return jsonResponse(null);
  }

  return jsonResponse([]);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
