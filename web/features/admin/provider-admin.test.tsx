import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProviderAdmin } from "@/features/admin/provider-admin";
import type { ProviderAdminData } from "@/lib/worlds/server";
import { updateProviderProfile } from "@/lib/worlds/client";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/client", () => ({
  createProviderProfile: vi.fn(),
  disableProviderProfile: vi.fn(),
  testProviderProfile: vi.fn(),
  updateProviderProfile: vi.fn(),
}));

describe("ProviderAdmin", () => {
  it("renders provider health and missing secret state", () => {
    render(<ProviderAdmin data={providerData} />);

    expect(screen.getByText("configuration_error")).toBeInTheDocument();
    expect(screen.getByText("missing")).toBeInTheDocument();
    expect(screen.getByText("Reference: missing-ref")).toBeInTheDocument();
    expect(screen.getByText("`missing-ref` is not present in NOVELAND_PROVIDER_API_KEYS_JSON.")).toBeInTheDocument();
    expect(screen.getByText("Fix configuration before provider execution.")).toBeInTheDocument();
    expect(screen.getByText("Review diagnostics before normal use.")).toBeInTheDocument();
    expect(screen.getByText("Recent errors")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getAllByText("Plugin config")).toHaveLength(2);
    expect(screen.getAllByText("Raw JSON fallback")).toHaveLength(2);
    expect(screen.getAllByText("Headers")).toHaveLength(2);
    expect(screen.getByText("Plugin bindings")).toBeInTheDocument();
    expect(screen.getByText("2 bindings inspected - 1 issues")).toBeInTheDocument();
    expect(screen.getByText("1 recent plugin diagnostics")).toBeInTheDocument();
    expect(screen.getByText("plugin.binding_invalid_config")).toBeInTheDocument();
    expect(screen.getByText("missing_plugin - missing.world_rules is not registered.")).toBeInTheDocument();
  });


  it("redacts sensitive provider profile plugin config and capabilities", async () => {
    vi.mocked(updateProviderProfile).mockResolvedValue(providerData.profiles[0]);
    const dirtyPluginConfig = {
      headers: "Bearer profile-token",
      endpoint: "/v1/chat",
      json_mode: true,
      clientSecret: "sk-live-provider-secret",
      rawPrompt: "actual raw prompt should stay private",
      storageUri: "media://provider/raw-output",
      promptSnapshotId: "prompt-snapshot-secret",
      localModelPath: "/models/private-provider.bin",
      attachment: "U2VjcmV0UHJvdmlkZXJQYXlsb2Fk",
    };
    const dirtyCapabilities = {
      chat: true,
      max_tokens: 4096,
      rawOutput: "actual raw output should stay private",
      bearerToken: "Bearer capability-token",
      storageUri: "media://capability/raw-output",
      evidence: "U2VjcmV0Q2FwYWJpbGl0eVBheWxvYWQ=",
    };
    const dirtyData: ProviderAdminData = {
      ...providerData,
      profiles: [
        {
          ...providerData.profiles[0],
          plugin_config: dirtyPluginConfig,
          capabilities: dirtyCapabilities,
        },
      ],
    };

    const { container } = render(<ProviderAdmin data={dirtyData} />);

    const pluginConfigTextarea = container.querySelectorAll<HTMLTextAreaElement>(
      'textarea[name="plugin_config"]',
    )[1];
    const capabilitiesTextarea = container.querySelectorAll<HTMLTextAreaElement>(
      'textarea[name="capabilities"]',
    )[1];
    expect(pluginConfigTextarea.value).toContain('/v1/chat');
    expect(pluginConfigTextarea.value).toContain('json_mode');
    expect(pluginConfigTextarea.value).toContain('[redacted]');
    expect(capabilitiesTextarea.value).toContain('max_tokens');
    expect(capabilitiesTextarea.value).toContain('[redacted]');
    for (const dirtyValue of [
      'clientSecret',
      'rawPrompt',
      'storageUri',
      'promptSnapshotId',
      'localModelPath',
      'sk-live-provider-secret',
      'Bearer profile-token',
      'actual raw prompt should stay private',
      'media://provider/raw-output',
      '/models/private-provider.bin',
      'U2VjcmV0UHJvdmlkZXJQYXlsb2Fk',
      'rawOutput',
      'bearerToken',
      'Bearer capability-token',
      'media://capability/raw-output',
      'U2VjcmV0Q2FwYWJpbGl0eVBheWxvYWQ=',
    ]) {
      expect(container).not.toHaveTextContent(dirtyValue);
      expect(pluginConfigTextarea.value).not.toContain(dirtyValue);
      expect(capabilitiesTextarea.value).not.toContain(dirtyValue);
    }

    fireEvent.change(pluginConfigTextarea, {
      target: { value: JSON.stringify(dirtyPluginConfig, null, 2) },
    });
    fireEvent.change(capabilitiesTextarea, {
      target: { value: JSON.stringify(dirtyCapabilities, null, 2) },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));

    await waitFor(() => {
      expect(updateProviderProfile).toHaveBeenCalledWith('profile-1', {
        name: 'OpenAI Local',
        plugin_identifier: 'builtin.openai_compatible',
        plugin_config: {
          headers: '[redacted]',
          endpoint: '/v1/chat',
          json_mode: true,
          attachment: '[redacted]',
        },
        base_url: 'https://api.example.test/v1',
        model_name: 'gpt-test',
        api_key_ref: 'missing-ref',
        capabilities: {
          chat: true,
          max_tokens: 4096,
          evidence: '[redacted]',
        },
        timeout_seconds: 20,
        retry_attempts: 1,
        rate_limit_per_minute: null,
        is_enabled: true,
      });
    });
  });
});

const providerData: ProviderAdminData = {
  profiles: [
    {
      id: "profile-1",
      profile_key: "openai-local",
      name: "OpenAI Local",
      provider_type: "openai_compatible",
      plugin_identifier: "builtin.openai_compatible",
      plugin_config: {},
      base_url: "https://api.example.test/v1",
      model_name: "gpt-test",
      capabilities: {},
      api_key_ref: "missing-ref",
      timeout_seconds: 20,
      retry_attempts: 1,
      rate_limit_per_minute: null,
      last_tested_at: null,
      last_test_status: null,
      last_test_error: null,
      is_enabled: true,
    },
  ],
  providerHealth: [
    {
      id: "profile-1",
      profile_key: "openai-local",
      name: "OpenAI Local",
      provider_type: "openai_compatible",
      is_enabled: true,
      health: "configuration_error",
      api_key_ref: "missing-ref",
      secret_ref_status: "missing",
      secret_ref_message: "`missing-ref` is not present in NOVELAND_PROVIDER_API_KEYS_JSON.",
      last_tested_at: null,
      last_test_status: null,
      last_test_error: null,
      missing_secret_ref: true,
      recent_diagnostic_count: 3,
      recent_error_count: 2,
    },
  ],
  modelProviderPlugins: [
    {
      identifier: "builtin.openai_compatible",
      category: "model_provider",
      version: "0.1.0",
      config_schema: {
        type: "object",
        properties: {
          headers: {
            title: "Headers",
            type: "string",
            description: "Optional JSON object of extra headers.",
          },
        },
      },
      capabilities: ["chat.completions"],
      built_in: true,
    },
  ],
  pluginBindings: [
    {
      owner_kind: "provider_profile",
      owner_id: "profile-1",
      owner_key: "openai-local",
      world_id: null,
      agent_id: null,
      conversation_id: null,
      provider_profile_id: "profile-1",
      plugin_identifier: "builtin.openai_compatible",
      category: "model_provider",
      config_present: false,
      validation_status: "ok",
      issue_message: null,
    },
    {
      owner_kind: "world_rules",
      owner_id: "world-1",
      owner_key: "first-world",
      world_id: "world-1",
      agent_id: null,
      conversation_id: null,
      provider_profile_id: null,
      plugin_identifier: "missing.world_rules",
      category: "world_rules",
      config_present: false,
      validation_status: "missing_plugin",
      issue_message: "missing.world_rules is not registered.",
    },
  ],
  pluginDiagnostics: [
    {
      id: "diagnostic-1",
      severity: "error",
      component: "plugin",
      event_type: "plugin.binding_invalid_config",
      message: "Provider plugin binding config failed validation.",
      details: {
        plugin_identifier: "builtin.openai_compatible",
        category: "model_provider",
        owner_kind: "provider_profile",
        owner_key: "openai-local",
      },
      occurred_at: "2026-05-04T00:00:00Z",
      world_id: null,
      agent_id: null,
      run_id: null,
      provider_profile_id: null,
      created_at: "2026-05-04T00:00:00Z",
    },
  ],
  loadError: null,
};
