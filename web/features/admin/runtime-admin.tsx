"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { updateRuntimeControl } from "@/lib/worlds/client";
import type { RuntimeAdminData } from "@/lib/worlds/server";
import { messageForError } from "@/features/workspace/form-utils";

type RuntimeAdminProps = {
  data: RuntimeAdminData;
};

export function RuntimeAdmin({ data }: RuntimeAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState(data.loadError);
  const [isBusy, setIsBusy] = useState(false);

  async function setDesiredState(desiredState: "running" | "stopped") {
    setIsBusy(true);
    setNotice(null);
    try {
      await updateRuntimeControl({ desired_state: desiredState });
      setNotice(desiredState === "running" ? "Runtime start requested." : "Runtime stop requested.");
      router.refresh();
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
            <p className="metric-label">Desired state</p>
            <p className="metric-value">{data.runtimeControl?.desired_state ?? "unknown"}</p>
          </div>
          <div className="metric">
            <p className="metric-label">Loop interval</p>
            <p className="metric-value">
              {data.runtimeStatus?.runtime_loop_interval_seconds ?? "-"}s
            </p>
          </div>
          <div className="metric">
            <p className="metric-label">Batch limit</p>
            <p className="metric-value">{data.runtimeStatus?.runtime_batch_limit ?? "-"}</p>
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
        <DiagnosticList diagnostics={data.runtimeDiagnostics} />
      </section>
    </section>
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
