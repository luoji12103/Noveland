import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", () => ({
  updateRuntimeControl: vi.fn(),
}));

const { subscribeToEventStream } = vi.hoisted(() => ({
  subscribeToEventStream: vi.fn(),
}));

vi.mock("@/lib/realtime", () => ({
  subscribeToEventStream,
}));

import { RuntimeAdmin } from "@/features/admin/runtime-admin";
import { updateRuntimeControl } from "@/lib/worlds/client";
import type { RuntimeAdminData } from "@/lib/worlds/server";
import type { RuntimeStreamEnvelope } from "@/lib/realtime";

const emptyMemoryWriteJobs = {
  pending_count: 0,
  processing_count: 0,
  succeeded_count: 0,
  failed_count: 0,
  due_count: 0,
  retryable_failed_count: 0,
  terminal_failed_count: 0,
  stalled_processing_count: 0,
};

const stoppedRuntimeHealth = {
  status: "stopped" as const,
  reason: "Runtime desired state is stopped.",
  recent_diagnostic_count: 0,
  recent_error_count: 0,
  heartbeat_age_seconds: null,
};

const healthyRuntimeHealth = {
  status: "healthy" as const,
  reason: "Runtime is running without recent blocking errors.",
  recent_diagnostic_count: 1,
  recent_error_count: 0,
  heartbeat_age_seconds: 1,
};

describe("RuntimeAdmin", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("updates displayed runtime state from the stream", async () => {
    let onEnvelope: ((envelope: RuntimeStreamEnvelope) => void) | undefined;
    subscribeToEventStream.mockImplementation((_: string, handler: typeof onEnvelope) => {
      onEnvelope = handler;
      return () => {};
    });

    render(<RuntimeAdmin data={runtimeData} />);

    onEnvelope?.({
      cursor: "cursor-1",
      event_type: "runtime.delta",
      occurred_at: "2026-04-22T00:00:01.000Z",
      world_id: null,
      conversation_id: null,
      payload: {
        runtime_control: {
          desired_state: "running",
          last_heartbeat_at: null,
          last_run_started_at: null,
          last_run_finished_at: null,
          last_error: null,
        },
        runtime_status: {
          desired_state: "running",
          last_heartbeat_at: null,
          last_run_started_at: null,
          last_run_finished_at: null,
          last_error: null,
          runtime_loop_interval_seconds: 5,
          runtime_batch_limit: 20,
          memory_write_jobs: emptyMemoryWriteJobs,
          runtime_health: healthyRuntimeHealth,
        },
        diagnostics: [
          {
            id: "diag-1",
            severity: "info",
            component: "runtime",
            event_type: "runtime.iteration_finished",
            message: "Iteration finished.",
            details: {},
            occurred_at: "2026-04-22T00:00:01.000Z",
            world_id: null,
            agent_id: null,
            run_id: null,
            provider_profile_id: null,
            created_at: "2026-04-22T00:00:01.000Z",
          },
        ],
        provider_profiles: [],
      },
    });

    await waitFor(() => {
      expect(screen.getByText("running")).toBeInTheDocument();
      expect(screen.getByText("Iteration finished.")).toBeInTheDocument();
      expect(screen.getByText("0 due / 0 failed")).toBeInTheDocument();
      expect(screen.getByText("healthy")).toBeInTheDocument();
      expect(screen.getByText("policy_only")).toBeInTheDocument();
      expect(screen.getByText("database_indexes - ok")).toBeInTheDocument();
    });
  });

  it("redacts sensitive runtime admin text from loader and stream data", async () => {
    let onEnvelope: ((envelope: RuntimeStreamEnvelope) => void) | undefined;
    subscribeToEventStream.mockImplementation((_: string, handler: typeof onEnvelope) => {
      onEnvelope = handler;
      return () => {};
    });

    if (
      runtimeData.runtimeStatus === null ||
      runtimeData.externalToolPolicy === null ||
      runtimeData.scaleReadiness === null
    ) {
      throw new Error("runtime fixture is incomplete");
    }

    const dirtyData: RuntimeAdminData = {
      ...runtimeData,
      runtimeStatus: {
        ...runtimeData.runtimeStatus,
        runtime_health: {
          ...stoppedRuntimeHealth,
          reason:
            "Runtime blocked after rawPrompt at media://runtime-secret with sk-live-secret.",
        },
      },
      runtimeDiagnostics: [
        {
          id: "diag-initial",
          severity: "error",
          component: "runtime /tmp/runtime-worker" as RuntimeAdminData["runtimeDiagnostics"][number]["component"],
          event_type: "runtime.error",
          message: "Failed using Bearer runtime-token and promptSnapshotId snapshot-1.",
          details: {},
          occurred_at: "2026-04-22T00:00:00.000Z",
          world_id: null,
          agent_id: null,
          run_id: null,
          provider_profile_id: null,
          created_at: "2026-04-22T00:00:00.000Z",
        },
      ],
      externalToolPolicy: {
        ...runtimeData.externalToolPolicy,
        operator_message: "External tool denied storageUri media://tool-secret.",
        deny_reasons: ["Bearer runtime-token", "external_tool_execution_disabled"],
        audit_fields: ["actor_ref", "rawOutput"],
      },
      scaleReadiness: {
        ...runtimeData.scaleReadiness,
        sections: [
          {
            ...runtimeData.scaleReadiness.sections[0],
            summary: "Scale check saw /var/noveland/provider-cache.",
            blockers: ["rawPrompt in local-model /models/private.gguf"],
            recommendations: ["Review query plans before growth testing."],
          },
        ],
      },
    };

    render(<RuntimeAdmin data={dirtyData} />);

    onEnvelope?.({
      cursor: "cursor-dirty",
      event_type: "runtime.delta",
      occurred_at: "2026-04-22T00:00:02.000Z",
      world_id: null,
      conversation_id: null,
      payload: {
        diagnostics: [
          {
            id: "diag-stream",
            severity: "warning",
            component: "runtime media://stream-secret" as RuntimeAdminData["runtimeDiagnostics"][number]["component"],
            event_type: "runtime.warning",
            message: "SSE carried base64 c2VjcmV0MTIzNA== from rawOutput.",
            details: {},
            occurred_at: "2026-04-22T00:00:02.000Z",
            world_id: null,
            agent_id: null,
            run_id: null,
            provider_profile_id: null,
            created_at: "2026-04-22T00:00:02.000Z",
          },
        ],
        provider_profiles: [],
      },
    });

    await waitFor(() => {
      expect(screen.getByText(/external_tool_execution_disabled/)).toBeInTheDocument();
      expect(screen.getByText(/actor_ref/)).toBeInTheDocument();
      expect(screen.getByText("database_indexes - ok")).toBeInTheDocument();
      expect(screen.getByText(/Review query plans before growth testing/)).toBeInTheDocument();
      expect(
        screen.queryAllByText(
          /rawPrompt|rawOutput|promptSnapshotId|storageUri|media:\/\/|sk-live-secret|Bearer runtime-token|\/var\/noveland|\/tmp\/runtime|\/models\/private|c2VjcmV0MTIzNA==/i,
        ),
      ).toHaveLength(0);
    });
  });

  it("requests runtime state changes through the HTTP client", async () => {
    subscribeToEventStream.mockImplementation(() => () => {});
    vi.mocked(updateRuntimeControl).mockResolvedValue({
      desired_state: "running",
      last_heartbeat_at: null,
      last_run_started_at: null,
      last_run_finished_at: null,
      last_error: null,
    });

    render(<RuntimeAdmin data={runtimeData} />);
    fireEvent.click(screen.getByRole("button", { name: "Start runtime" }));

    await waitFor(() => {
      expect(updateRuntimeControl).toHaveBeenCalledWith({ desired_state: "running" });
    });
  });
});

const runtimeData: RuntimeAdminData = {
  runtimeControl: {
    desired_state: "stopped",
    last_heartbeat_at: null,
    last_run_started_at: null,
    last_run_finished_at: null,
    last_error: null,
  },
  runtimeStatus: {
    desired_state: "stopped",
    last_heartbeat_at: null,
    last_run_started_at: null,
    last_run_finished_at: null,
    last_error: null,
    runtime_loop_interval_seconds: 5,
    runtime_batch_limit: 20,
    memory_write_jobs: emptyMemoryWriteJobs,
    runtime_health: stoppedRuntimeHealth,
  },
  runtimeDiagnostics: [],
  externalToolPolicy: {
    policy_mode: "policy_only",
    execution_enabled: false,
    runtime_execution_enabled: false,
    supported_permission_modes: [
      "disabled",
      "allowlist_required",
      "denylist_block",
      "manual_approval_required",
    ],
    default_permission_mode: "disabled",
    deny_reasons: ["external_tool_execution_disabled"],
    audit_fields: ["world_id", "agent_id", "actor_ref"],
    secret_handling: ["Secret values are not exposed."],
    data_exposure_rules: ["No external execution is enabled."],
    operator_message:
      "External tool policy is defined for audit and future integration only.",
  },
  scaleReadiness: {
    status: "ok",
    section_count: 1,
    blocker_count: 0,
    generated_at: "2026-05-05T00:00:00.000Z",
    sections: [
      {
        area: "database_indexes",
        status: "ok",
        summary: "Core operational tables are available for derived scale review.",
        metrics: { world_count: 0 },
        blockers: [],
        recommendations: ["Review query plans before growth testing."],
      },
    ],
  },
  modelProviderPlugins: [],
  loadError: null,
};
