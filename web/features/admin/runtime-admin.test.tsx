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
  modelProviderPlugins: [],
  loadError: null,
};
