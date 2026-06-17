import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createInvocationTag,
  deleteInvocationTag,
  getInvocation,
  getPromptSnapshot,
  listInvocationTags,
  listInvocations,
  redactInvocation,
} from "@/lib/worlds/invocations";

describe("invocation ledger admin client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("lists and reads invocation records through world proxy paths", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ invocations: [invocation] }))
      .mockResolvedValueOnce(jsonResponse(invocation))
      .mockResolvedValueOnce(jsonResponse(promptSnapshot))
      .mockResolvedValueOnce(jsonResponse([tag]));
    vi.stubGlobal("fetch", fetchMock);

    await listInvocations("world-1", {
      worldline_id: "worldline-1",
      invocation_kind: "text_to_speech",
      provider_kind: "openai_audio",
      status: "succeeded",
      tag: ["audit:phase:v0.4"],
      include_hidden: true,
    });
    await getInvocation("world-1", "invocation-1");
    await getPromptSnapshot("world-1", "invocation-1");
    await listInvocationTags("world-1", "invocation-1");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/model-invocations?worldline_id=worldline-1&invocation_kind=text_to_speech&provider_kind=openai_audio&status=succeeded&tag=audit%3Aphase%3Av0.4&include_hidden=true",
      "/api/worlds/world-1/model-invocations/invocation-1",
      "/api/worlds/world-1/model-invocations/invocation-1/prompt-snapshot",
      "/api/worlds/world-1/model-invocations/invocation-1/tags",
    ]);
  });

  it("uses csrf for tag and redaction writes", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(tag))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ ...invocation, redaction_status: "redacted" }));
    vi.stubGlobal("fetch", fetchMock);

    await createInvocationTag("world-1", "invocation-1", {
      worldline_id: "worldline-1",
      tag_type: "audit",
      tag_key: "phase",
      tag_value: "v0.4",
    });
    await deleteInvocationTag("world-1", "invocation-1", "tag-1");
    await redactInvocation("world-1", "invocation-1", {
      redaction_status: "redacted",
      mode: "clear_raw_payloads",
      reason: "test redaction",
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/model-invocations/invocation-1/tags",
      "/api/worlds/world-1/model-invocations/invocation-1/tags/tag-1",
      "/api/worlds/world-1/model-invocations/invocation-1/redact",
    ]);
    for (const call of fetchMock.mock.calls) {
      expect((call[1].headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    }
  });

  it("encodes reserved characters in invocation ledger route segments", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ invocations: [invocation] }))
      .mockResolvedValueOnce(jsonResponse(invocation))
      .mockResolvedValueOnce(jsonResponse(promptSnapshot))
      .mockResolvedValueOnce(jsonResponse([tag]))
      .mockResolvedValueOnce(jsonResponse(tag))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ ...invocation, redaction_status: "redacted" }));
    vi.stubGlobal("fetch", fetchMock);

    const worldId = "world/ledger?admin=true#frag";
    const invocationId = "invocation/raw?prompt=true#frag";
    const tagId = "tag/redact?x=1#frag";

    await listInvocations(worldId, {
      contains_text: "raw/prompt?x=1#frag",
      tag: ["audit/path?x=1#frag"],
      include_hidden: true,
    });
    await getInvocation(worldId, invocationId);
    await getPromptSnapshot(worldId, invocationId);
    await listInvocationTags(worldId, invocationId);
    await createInvocationTag(worldId, invocationId, {
      tag_type: "audit",
      tag_key: "path",
      tag_value: "encoded",
    });
    await deleteInvocationTag(worldId, invocationId, tagId);
    await redactInvocation(worldId, invocationId, {
      redaction_status: "checksum_only",
      mode: "checksum_only",
      reason: "reserved chars",
    });

    const encodedWorld = encodeURIComponent(worldId);
    const encodedInvocation = encodeURIComponent(invocationId);
    const encodedTag = encodeURIComponent(tagId);

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      `/api/worlds/${encodedWorld}/model-invocations?contains_text=raw%2Fprompt%3Fx%3D1%23frag&tag=audit%2Fpath%3Fx%3D1%23frag&include_hidden=true`,
      `/api/worlds/${encodedWorld}/model-invocations/${encodedInvocation}`,
      `/api/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/prompt-snapshot`,
      `/api/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/tags`,
      `/api/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/tags`,
      `/api/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/tags/${encodedTag}`,
      `/api/worlds/${encodedWorld}/model-invocations/${encodedInvocation}/redact`,
    ]);
    for (const call of fetchMock.mock.calls.slice(4)) {
      expect((call[1].headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    }
  });

});

const invocation = {
  id: "invocation-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  trace_id: "trace-1",
  parent_invocation_id: null,
  invocation_kind: "text_to_speech",
  actor_kind: "world_admin",
  actor_ref: "user:admin",
  agent_id: "agent-1",
  conversation_id: null,
  turn_id: null,
  world_event_id: null,
  media_job_id: "job-1",
  media_asset_id: "asset-1",
  memory_write_job_id: null,
  provider_kind: "openai_audio",
  provider_profile_id: "provider-1",
  model_name: "tts-1",
  model_version: null,
  prompt_template_key: null,
  prompt_template_version: null,
  input_text: "hello",
  output_text: "audio asset created",
  input_json: {},
  output_json: {},
  request_params_json: {},
  response_metadata_json: {},
  usage_json: {},
  latency_ms: 321,
  estimated_cost: "0.01",
  status: "succeeded",
  error_text: null,
  visibility: "world_admin",
  redaction_status: "raw",
  retention_policy: "local_debug",
  contains_sensitive_context: false,
  purge_after: null,
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const promptSnapshot = {
  id: "snapshot-1",
  invocation_id: "invocation-1",
  template_id: null,
  template_key: null,
  template_version: null,
  raw_prompt_text: "hello",
  raw_messages_json: [],
  raw_request_json: {},
  raw_response_json: {},
  raw_output_text: "audio asset created",
  normalized_output_json: {},
  prompt_context_snapshot_json: {},
  tool_definitions_json: {},
  context_pack_refs_json: {},
  input_asset_refs_json: [],
  prompt_checksum_sha256: "a".repeat(64),
  request_checksum_sha256: "b".repeat(64),
  response_checksum_sha256: "c".repeat(64),
  output_checksum_sha256: "d".repeat(64),
  visibility: "world_admin",
  redaction_status: "raw",
  contains_sensitive_context: false,
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const tag = {
  id: "tag-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  invocation_id: "invocation-1",
  tag_type: "audit",
  tag_key: "phase",
  tag_value: "v0.4",
  created_at: "2026-05-13T00:00:00.000Z",
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
