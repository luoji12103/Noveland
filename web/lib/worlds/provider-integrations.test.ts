import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createProviderIntegration,
  discoverProviderModels,
  listProviderCapabilities,
  listProviderHealthChecks,
  listProviderIntegrations,
  listProviderTemplates,
  runProviderHealthCheck,
  runProviderSmokeTest,
  updateProviderIntegration,
} from "@/lib/worlds/provider-integrations";

describe("provider integration client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("lists world provider integrations through the world proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await listProviderIntegrations("world-1", {
      include_global: true,
      include_hidden: false,
      provider_kind: "image_generation",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/worlds/world-1/providers?include_global=true&include_hidden=false&provider_kind=image_generation",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
  });

  it("creates provider integrations with csrf and safe reference fields", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(providerRecord));
    vi.stubGlobal("fetch", fetchMock);

    await createProviderIntegration("world-1", {
      scope_kind: "world",
      provider_kind: "image_generation",
      adapter_kind: "fake",
      provider_key: "fake-image",
      display_name: "Fake image",
      base_url: null,
      auth_ref: "env:OPENAI_API_KEY",
      config_json: {},
      default_params_json: {},
      status: "active",
      visibility: "world_admin",
      capabilities: [{ capability_key: "image.generate", capability_json: {} }],
    });

    const request = fetchMock.mock.calls[0][1];
    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/providers");
    expect(request.method).toBe("POST");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(request.body).toContain("env:OPENAI_API_KEY");
    expect(request.body).not.toContain("sk-");
  });

  it("lists templates and discovers models with manual fallback fields", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([providerTemplate]))
      .mockResolvedValueOnce(
        jsonResponse({
          provider_id: "provider-1",
          provider_kind: "text_generation",
          adapter_kind: "openai_compatible",
          discovery_status: "succeeded",
          models: ["alpha-model"],
          manual_fallback_allowed: true,
          error_code: null,
          error_message: null,
          metadata_json: {},
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await listProviderTemplates("world-1");
    await discoverProviderModels("world-1", {
      provider_id: "provider-1",
      base_url: "https://gateway.example/v1",
      auth_ref: "env:OPENAI_API_KEY",
    });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/providers/templates");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/providers/model-discovery");
    const request = fetchMock.mock.calls[1][1];
    expect(request.method).toBe("POST");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(request.body).toContain("env:OPENAI_API_KEY");
    expect(request.body).not.toContain("sk-");
  });

  it("updates, checks health, lists health, and smoke-tests providers", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(providerRecord))
      .mockResolvedValueOnce(jsonResponse({ id: "cap-1" }))
      .mockResolvedValueOnce(jsonResponse({ id: "health-1" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "health-1" }]))
      .mockResolvedValueOnce(jsonResponse({ smoke_status: "succeeded", provider: providerRecord }));
    vi.stubGlobal("fetch", fetchMock);

    await updateProviderIntegration("world-1", "provider-1", { status: "disabled" });
    await listProviderCapabilities("world-1", "provider-1");
    await runProviderHealthCheck("world-1", "provider-1");
    await listProviderHealthChecks("world-1", "provider-1", 10);
    await runProviderSmokeTest("world-1", "provider-1", { input_text: "smoke" });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/providers/provider-1",
      "/api/worlds/world-1/providers/provider-1/capabilities",
      "/api/worlds/world-1/providers/provider-1/health-check",
      "/api/worlds/world-1/providers/provider-1/health-checks?limit=10",
      "/api/worlds/world-1/providers/provider-1/smoke-test",
    ]);
  });
});

const providerRecord = {
  id: "provider-1",
  world_id: "world-1",
  scope_kind: "world",
  scope_key: "world-1",
  provider_kind: "image_generation",
  adapter_kind: "fake",
  provider_key: "fake-image",
  display_name: "Fake image",
  base_url: null,
  auth_ref: "env:OPENAI_API_KEY",
  auth_ref_configured: true,
  config_json: {},
  default_params_json: {},
  status: "active",
  visibility: "world_admin",
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const providerTemplate = {
  template_key: "openai-compatible-llm",
  display_name: "OpenAI-compatible LLM",
  provider_kind: "text_generation",
  adapter_kind: "openai_compatible",
  description: "Chat/completions-compatible text provider with custom base URL.",
  base_url_placeholder: "https://gateway.example/v1",
  model_name_placeholder: "model-name",
  auth_ref_placeholder: "env:OPENAI_API_KEY",
  config_json: { model_discovery_path: "/models" },
  default_params_json: { temperature: 0.7 },
  capabilities: [{ capability_key: "text.generate", capability_json: {} }],
  model_discovery: { strategy: "openai_models", path: "/models" },
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
