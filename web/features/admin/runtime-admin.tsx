"use client";

import { useEffect, useState } from "react";

import { updateRuntimeControl } from "@/lib/worlds/client";
import type { RuntimeAdminData } from "@/lib/worlds/server";
import { subscribeToEventStream } from "@/lib/realtime";
import type { RuntimeStreamEnvelope } from "@/lib/realtime";
import type { RuntimeDiagnostic } from "@/lib/worlds/types";
import { messageForError } from "@/features/workspace/form-utils";

type RuntimeAdminProps = {
  data: RuntimeAdminData;
};

export function RuntimeAdmin({ data }: RuntimeAdminProps) {
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [runtimeControl, setRuntimeControl] = useState(data.runtimeControl);
  const [runtimeStatus, setRuntimeStatus] = useState(data.runtimeStatus);
  const [runtimeDiagnostics, setRuntimeDiagnostics] = useState(data.runtimeDiagnostics);
  const memoryWriteJobs = runtimeStatus?.memory_write_jobs ?? {
    pending_count: 0,
    processing_count: 0,
    succeeded_count: 0,
    failed_count: 0,
    due_count: 0,
    retryable_failed_count: 0,
    terminal_failed_count: 0,
    stalled_processing_count: 0,
  };
  const runtimeHealth = runtimeStatus?.runtime_health ?? null;

  useEffect(() => {
    setRuntimeControl(data.runtimeControl);
    setRuntimeStatus(data.runtimeStatus);
    setRuntimeDiagnostics(data.runtimeDiagnostics);
  }, [data.runtimeControl, data.runtimeDiagnostics, data.runtimeStatus]);

  useEffect(() => {
    return subscribeToEventStream<RuntimeStreamEnvelope["payload"]>(
      "/api/runtime/stream",
      (envelope) => {
        if (envelope.payload.runtime_control !== undefined) {
          setRuntimeControl(envelope.payload.runtime_control);
        }
        if (envelope.payload.runtime_status !== undefined) {
          setRuntimeStatus(envelope.payload.runtime_status);
        }
        if (envelope.payload.diagnostics.length > 0) {
          setRuntimeDiagnostics((current) =>
            mergeDiagnostics(current, envelope.payload.diagnostics),
          );
        }
      },
    );
  }, []);

  async function setDesiredState(desiredState: "running" | "stopped") {
    setIsBusy(true);
    setNotice(null);
    try {
      const nextControl = await updateRuntimeControl({ desired_state: desiredState });
      setRuntimeControl(nextControl);
      setNotice(desiredState === "running" ? "Runtime start requested." : "Runtime stop requested.");
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section">
      {notice !== null ? <p className="management-notice">{notice}</p> : null}

      <section className="management-panel" aria-labelledby="runtime-title">
        <h2 className="section-title" id="runtime-title">
          Runtime control
        </h2>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Runtime health</p>
            <p className="metric-value">{runtimeHealth?.status ?? "unknown"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Desired state</p>
            <p className="metric-value">{runtimeControl?.desired_state ?? "unknown"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Heartbeat age</p>
            <p className="metric-value">
              {runtimeHealth?.heartbeat_age_seconds === null ||
              runtimeHealth?.heartbeat_age_seconds === undefined
                ? "-"
                : `${runtimeHealth.heartbeat_age_seconds}s`}
            </p>
          </div>
          <div className="metric">
            <p className="metric-label">Loop interval</p>
            <p className="metric-value">
              {runtimeStatus?.runtime_loop_interval_seconds ?? "-"}s
            </p>
          </div>
          <div className="metric">
            <p className="metric-label">Batch limit</p>
            <p className="metric-value">{runtimeStatus?.runtime_batch_limit ?? "-"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Memory jobs</p>
            <p className="metric-value">
              {runtimeStatus === null
                ? "-"
                : `${memoryWriteJobs.due_count} due / ${memoryWriteJobs.failed_count} failed`}
            </p>
          </div>
          <div className="metric">
            <p className="metric-label">Terminal memory jobs</p>
            <p className="metric-value">
              {runtimeStatus === null
                ? "-"
                : `${memoryWriteJobs.terminal_failed_count} terminal / ${memoryWriteJobs.stalled_processing_count} stalled`}
            </p>
          </div>
          <div className="metric">
            <p className="metric-label">Recent runtime errors</p>
            <p className="metric-value">{runtimeHealth?.recent_error_count ?? "-"}</p>
          </div>
        </div>
        {runtimeHealth === null ? null : (
          <p className="management-notice">
            {runtimeHealth.reason} Recent diagnostics: {runtimeHealth.recent_diagnostic_count}.
          </p>
        )}
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Pending</p>
            <p className="metric-value">{memoryWriteJobs.pending_count}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Processing</p>
            <p className="metric-value">{memoryWriteJobs.processing_count}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Retryable failed</p>
            <p className="metric-value">{memoryWriteJobs.retryable_failed_count}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Succeeded</p>
            <p className="metric-value">{memoryWriteJobs.succeeded_count}</p>
          </div>
        </div>
        <div className="dashboard-grid">
          <div className="metric">
            <p className="metric-label">Last started</p>
            <p className="metric-value">
              {runtimeStatus?.last_run_started_at === null || runtimeStatus === null
                ? "-"
                : new Date(runtimeStatus.last_run_started_at).toLocaleString()}
            </p>
          </div>
          <div className="metric">
            <p className="metric-label">Last finished</p>
            <p className="metric-value">
              {runtimeStatus?.last_run_finished_at === null || runtimeStatus === null
                ? "-"
                : new Date(runtimeStatus.last_run_finished_at).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="button-row">
          <button
            className="primary-button"
            type="button"
            disabled={isBusy}
            onClick={() => setDesiredState("running")}
          >
            Start runtime
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={isBusy}
            onClick={() => setDesiredState("stopped")}
          >
            Stop runtime
          </button>
        </div>
      </section>

      <section className="management-panel" aria-labelledby="diagnostics-title">
        <h2 className="section-title" id="diagnostics-title">
          Runtime diagnostics
        </h2>
        <DiagnosticList diagnostics={runtimeDiagnostics} />
      </section>
    </section>
  );
}

function mergeDiagnostics(
  current: RuntimeDiagnostic[],
  incoming: RuntimeDiagnostic[],
): RuntimeDiagnostic[] {
  const byId = new Map(current.map((diagnostic) => [diagnostic.id, diagnostic]));
  for (const diagnostic of incoming) {
    byId.set(diagnostic.id, diagnostic);
  }
  return Array.from(byId.values()).sort((left, right) =>
    right.occurred_at.localeCompare(left.occurred_at),
  );
}

function DiagnosticList({ diagnostics }: { diagnostics: RuntimeAdminData["runtimeDiagnostics"] }) {
  if (diagnostics.length === 0) {
    return <p>No diagnostics recorded.</p>;
  }
  return (
    <div className="resource-list">
      {diagnostics.map((diagnostic) => (
        <article className="resource-row" key={diagnostic.id}>
          <div>
            <h3>
              {diagnostic.severity} - {diagnostic.component}
            </h3>
            <p>{diagnostic.message}</p>
            <p>{diagnostic.occurred_at}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
