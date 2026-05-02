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
  loadError: null,
};
