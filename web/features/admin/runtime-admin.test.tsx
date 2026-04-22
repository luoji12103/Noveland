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
  },
  runtimeDiagnostics: [],
  loadError: null,
};
