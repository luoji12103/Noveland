import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MultimodalDiagnosticsAdmin } from "@/features/admin/multimodal-diagnostics-admin";
import {
  getMultimodalDiagnostics,
  listMultimodalEvalRuns,
  runMultimodalEval,
} from "@/lib/worlds/diagnostics";
import type {
  MultimodalDiagnosticsResult,
  MultimodalEvalRun,
} from "@/lib/worlds/diagnostics";
import type { MultimodalDiagnosticsAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/diagnostics", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/diagnostics")>(
    "@/lib/worlds/diagnostics",
  );
  return {
    ...actual,
    getMultimodalDiagnostics: vi.fn(),
    listMultimodalEvalRuns: vi.fn(),
    runMultimodalEval: vi.fn(),
  };
});

describe("MultimodalDiagnosticsAdmin", () => {
  it("renders safe diagnostic summaries without raw evidence leaks", () => {
    render(<MultimodalDiagnosticsAdmin worldId="world-1" data={diagnosticsData} />);

    expect(screen.getByRole("heading", { name: "Multimodal diagnostics overview" })).toBeInTheDocument();
    expect(screen.getByText("provider_health_missing")).toBeInTheDocument();
    expect(screen.getByText("media_asset_missing_object")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Blockers" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Warnings" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Recent multimodal eval runs" })).toBeInTheDocument();
    expect(screen.getAllByText("long_run_eval_runs").length).toBeGreaterThan(0);
    expect(screen.queryByText(/media:\/\//)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/var\/noveland/)).not.toBeInTheDocument();
    expect(screen.queryByText(/base64/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sk-live-secret/)).not.toBeInTheDocument();
    expect(screen.queryByText(/actual raw prompt/)).not.toBeInTheDocument();
    expect(screen.queryByText(/actual raw output/)).not.toBeInTheDocument();
  });

  it("loads selected worldline diagnostics and runs explicit smoke eval", async () => {
    vi.mocked(getMultimodalDiagnostics).mockResolvedValue(diagnostics);
    vi.mocked(listMultimodalEvalRuns).mockResolvedValue([evalRun]);
    vi.mocked(runMultimodalEval).mockResolvedValue(evalRun);
    render(<MultimodalDiagnosticsAdmin worldId="world-1" data={diagnosticsData} />);

    fireEvent.click(screen.getByRole("button", { name: "Load diagnostics" }));

    await waitFor(() => {
      expect(getMultimodalDiagnostics).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
      });
    });
    expect(listMultimodalEvalRuns).toHaveBeenCalledWith("world-1", {
      worldline_id: "worldline-1",
      limit: 20,
    });

    fireEvent.click(screen.getByRole("button", { name: "Run multimodal smoke eval" }));

    await waitFor(() => {
      expect(runMultimodalEval).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          eval_key: "multimodal-smoke",
        }),
      );
    });
  });

  it("shows an ACL state when diagnostics are unavailable", () => {
    render(
      <MultimodalDiagnosticsAdmin
        worldId="world-1"
        data={{
          ...diagnosticsData,
          canManageSelectedWorld: false,
          diagnostics: null,
          evalRuns: [],
        }}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Multimodal diagnostics require world admin access.",
    );
  });
});

const diagnostics: MultimodalDiagnosticsResult = {
  world_id: "world-1",
  worldline_id: "worldline-1",
  status: "failed",
  generated_at: "2026-05-14T00:00:00.000Z",
  metrics: {
    providers: {
      configured_count: 2,
      auth_ref_configured_count: 1,
      health_status_counts: { healthy: 1 },
      providers_without_health_count: 1,
      unsafe_provider_config_count: 0,
    },
    invocations: {
      count: 3,
      provider_invocation_count: 2,
      missing_prompt_snapshot_count: 0,
      prompt_snapshot_leak_count: 0,
      average_latency_ms: 123,
      estimated_cost_total: 0.03,
    },
    media_assets: {
      asset_count: 5,
      object_count: 5,
      missing_object_count: 1,
      missing_storage_count: 0,
      invalid_checksum_count: 0,
      tts_missing_invocation_link_count: 0,
    },
    visual: {
      sprite_set_count: 1,
      sprite_variant_count: 3,
      sprite_sets_missing_default_count: 0,
      sprite_sets_missing_neutral_count: 0,
      scene_background_count: 1,
    },
    speech: {
      voice_profile_count: 1,
      voice_binding_count: 1,
      agents_missing_default_voice_count: 0,
      speech_transcript_count: 1,
      transcript_memory_write_count: 0,
    },
    events: {
      count: 1,
      payload_leak_count: 0,
    },
  },
  blockers: [
    {
      code: "media_asset_missing_object",
      severity: "blocker",
      message: "Available media assets are missing media objects.",
      evidence_refs: [{ kind: "media_asset", id: "asset-1" }],
    },
  ],
  warnings: [
    {
      code: "provider_health_missing",
      severity: "warning",
      message: "Some provider integrations do not have health or smoke evidence.",
      evidence_refs: [{ kind: "provider_integration", id: "provider-1" }],
    },
  ],
  recommendations: [
    "Repair media job outputs and verify media object storage integrity.",
    "Do not show media://hidden, /var/noveland/hidden, sk-live-secret, base64, actual raw prompt, or actual raw output.",
  ],
  evidence_refs: [{ kind: "provider_integration", id: "provider-1" }],
};

const evalRun: MultimodalEvalRun = {
  id: "run-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  eval_key: "multimodal-smoke",
  horizon_days: 7,
  status: "failed",
  started_at: "2026-05-14T00:00:00.000Z",
  finished_at: "2026-05-14T00:00:01.000Z",
  metrics: diagnostics.metrics,
  recommendations: [{ message: "Repair media job outputs." }],
  blockers: [{ code: "media_asset_missing_object" }],
  metadata: {
    diagnostic_eval_key: "multimodal-smoke",
    evidence_refs: [{ kind: "provider_integration", id: "provider-1" }],
  },
  created_at: "2026-05-14T00:00:00.000Z",
  updated_at: "2026-05-14T00:00:01.000Z",
};

const diagnosticsData: MultimodalDiagnosticsAdminData = {
  worlds: [],
  selectedWorld: null,
  memberships: [],
  worldlines: [
    {
      id: "worldline-1",
      world_id: "world-1",
      worldline_key: "main",
      name: "Main",
      description: null,
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: null,
      status: "active",
      created_by_actor_ref: "user:admin",
      metadata: {},
      created_at: "2026-05-14T00:00:00.000Z",
      updated_at: "2026-05-14T00:00:00.000Z",
    },
  ],
  selectedWorldlineId: "worldline-1",
  diagnostics,
  evalRuns: [evalRun],
  canManageSelectedWorld: true,
  isPlatformAdmin: false,
  loadError: null,
};
