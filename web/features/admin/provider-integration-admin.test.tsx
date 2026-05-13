import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProviderIntegrationAdmin } from "@/features/admin/provider-integration-admin";
import {
  createProviderIntegration,
  runProviderHealthCheck,
  runProviderSmokeTest,
  updateProviderIntegration,
} from "@/lib/worlds/provider-integrations";
import type { ProviderIntegrationAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/provider-integrations", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/worlds/provider-integrations")>(
      "@/lib/worlds/provider-integrations",
    );
  return {
    ...actual,
    createProviderIntegration: vi.fn(),
    updateProviderIntegration: vi.fn(),
    deleteProviderIntegration: vi.fn(),
    runProviderHealthCheck: vi.fn(),
    runProviderSmokeTest: vi.fn(),
  };
});

describe("ProviderIntegrationAdmin", () => {
  it("renders provider integrations without resolved secrets", () => {
    render(<ProviderIntegrationAdmin worldId="world-1" data={providerData} />);

    expect(screen.getByRole("heading", { name: "Provider integration overview" })).toBeInTheDocument();
    expect(screen.getByText("Fake image")).toBeInTheDocument();
    expect(screen.getAllByText(/env:OPENAI_API_KEY/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/sk-live-secret/)).not.toBeInTheDocument();
    expect(screen.getByText("This provider uses restricted visibility. Non-platform users only see it when backend ACLs allow access.")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Provider capabilities" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Provider health checks" })).toBeInTheDocument();
    expect(screen.getByText("auth_resolved")).toBeInTheDocument();
  });

  it("creates and updates provider integrations through safe client helpers", async () => {
    vi.mocked(createProviderIntegration).mockResolvedValue(providerData.providers[0]);
    vi.mocked(updateProviderIntegration).mockResolvedValue(providerData.providers[0]);
    render(<ProviderIntegrationAdmin worldId="world-1" data={providerData} />);

    fireEvent.change(screen.getByPlaceholderText("fake-image"), {
      target: { value: "fake-tts" },
    });
    fireEvent.change(screen.getByPlaceholderText("Display name"), {
      target: { value: "Fake TTS" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create provider integration" }));

    await waitFor(() => {
      expect(createProviderIntegration).toHaveBeenCalled();
    });

    fireEvent.change(screen.getByDisplayValue("Fake image"), {
      target: { value: "Fake image saved" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save provider" }));

    await waitFor(() => {
      expect(updateProviderIntegration).toHaveBeenCalledWith(
        "world-1",
        "provider-1",
        expect.objectContaining({ display_name: "Fake image saved" }),
      );
    });
  });

  it("runs health checks and smoke tests through explicit admin actions", async () => {
    vi.mocked(runProviderHealthCheck).mockResolvedValue(providerData.healthChecksByProviderId["provider-1"][0]);
    vi.mocked(runProviderSmokeTest).mockResolvedValue({
      smoke_status: "succeeded",
      provider: providerData.providers[0],
      invocation: { id: "invocation-1", status: "succeeded", latency_ms: 3 },
      output_text: null,
      output_json: {},
    });
    render(<ProviderIntegrationAdmin worldId="world-1" data={providerData} />);

    fireEvent.click(screen.getByRole("button", { name: "Run health check" }));

    await waitFor(() => {
      expect(runProviderHealthCheck).toHaveBeenCalledWith("world-1", "provider-1");
    });

    fireEvent.click(screen.getByRole("button", { name: "Smoke test" }));

    await waitFor(() => {
      expect(runProviderSmokeTest).toHaveBeenCalledWith(
        "world-1",
        "provider-1",
        expect.objectContaining({ input_text: "Noveland provider smoke test" }),
      );
    });
  });

  it("shows an ACL state when world management data is unavailable", () => {
    render(
      <ProviderIntegrationAdmin
        worldId="world-1"
        data={{ ...providerData, canManageSelectedWorld: false, providers: [] }}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Provider integrations require world admin access.",
    );
  });
});

const providerData: ProviderIntegrationAdminData = {
  worlds: [],
  selectedWorld: null,
  memberships: [],
  providers: [
    {
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
      visibility: "developer_only",
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  capabilitiesByProviderId: {
    "provider-1": [
      {
        id: "capability-1",
        provider_integration_id: "provider-1",
        capability_key: "image.generate",
        capability_json: { transparent: true },
        created_at: "2026-05-13T00:00:00.000Z",
        updated_at: "2026-05-13T00:00:00.000Z",
      },
    ],
  },
  healthChecksByProviderId: {
    "provider-1": [
      {
        id: "health-1",
        provider_integration_id: "provider-1",
        status: "healthy",
        latency_ms: 4,
        checked_at: "2026-05-13T00:00:00.000Z",
        error_text: null,
        metadata_json: { auth_resolved: true },
      },
    ],
  },
  canManageSelectedWorld: true,
  isPlatformAdmin: true,
  loadError: null,
};
