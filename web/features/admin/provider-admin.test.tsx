import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProviderAdmin } from "@/features/admin/provider-admin";
import type { ProviderAdminData } from "@/lib/worlds/server";

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
    expect(screen.getByText("missing-ref")).toBeInTheDocument();
    expect(screen.getByText("`missing-ref` is not present in NOVELAND_PROVIDER_API_KEYS_JSON.")).toBeInTheDocument();
    expect(screen.getByText("Recent errors")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Plugin bindings")).toBeInTheDocument();
    expect(screen.getByText("2 bindings inspected - 1 issues")).toBeInTheDocument();
    expect(screen.getByText("missing_plugin - missing.world_rules is not registered.")).toBeInTheDocument();
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
  modelProviderPlugins: [],
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
  loadError: null,
};
