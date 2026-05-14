"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  AdminDescriptionList,
  AdminMetric,
  AdminNotice,
  AdminSection,
  AdminState,
  AdminTable,
} from "@/features/admin/admin-foundation";
import { messageForError, optionalFormString } from "@/features/workspace/form-utils";
import {
  getMultimodalDiagnostics,
  listMultimodalEvalRuns,
  runMultimodalEval,
} from "@/lib/worlds/diagnostics";
import type {
  MultimodalDiagnosticFinding,
  MultimodalDiagnosticsResult,
  MultimodalEvalRun,
  MultimodalEvidenceRef,
} from "@/lib/worlds/diagnostics";
import type { MultimodalDiagnosticsAdminData } from "@/lib/worlds/server";

type MultimodalDiagnosticsAdminProps = {
  worldId: string;
  data: MultimodalDiagnosticsAdminData;
};

type SummaryMetric = {
  label: string;
  value: string | number;
  tone?: "neutral" | "ok" | "warning" | "error";
};

export function MultimodalDiagnosticsAdmin({ worldId, data }: MultimodalDiagnosticsAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [selectedWorldlineId, setSelectedWorldlineId] = useState(data.selectedWorldlineId ?? "");
  const [diagnostics, setDiagnostics] = useState(data.diagnostics);
  const [evalRuns, setEvalRuns] = useState(data.evalRuns);
  const metrics = diagnostics?.metrics ?? {};
  const statusTone = toneForStatus(diagnostics?.status ?? null);
  const blockerCount = diagnostics?.blockers.length ?? 0;
  const warningCount = diagnostics?.warnings.length ?? 0;
  const summaryMetrics = useMemo(() => buildSummaryMetrics(diagnostics), [diagnostics]);

  async function runAction(action: () => Promise<unknown>, success: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      router.refresh();
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const worldlineId = optionalFormString(form, "worldline_id") ?? "";
    setSelectedWorldlineId(worldlineId);
    await runAction(async () => {
      if (worldlineId === "") {
        setDiagnostics(null);
        setEvalRuns([]);
        return;
      }
      const [nextDiagnostics, nextRuns] = await Promise.all([
        getMultimodalDiagnostics(worldId, { worldline_id: worldlineId }),
        listMultimodalEvalRuns(worldId, { worldline_id: worldlineId, limit: 20 }),
      ]);
      setDiagnostics(nextDiagnostics);
      setEvalRuns(nextRuns);
    }, "Multimodal diagnostics loaded.");
  }

  async function handleRunEval() {
    if (selectedWorldlineId === "") {
      setNotice("Select a worldline before running diagnostics.");
      return;
    }
    await runAction(async () => {
      const run = await runMultimodalEval(worldId, {
        worldline_id: selectedWorldlineId,
        eval_key: "multimodal-smoke",
        horizon_days: 7,
        metadata: { source: "web_admin", capability: "multimodal_diagnostics_dashboard" },
      });
      const nextDiagnostics = await getMultimodalDiagnostics(worldId, {
        worldline_id: selectedWorldlineId,
      });
      setDiagnostics(nextDiagnostics);
      setEvalRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
    }, "Multimodal smoke eval completed.");
  }

  return (
    <section className="management-section">
      {notice !== null ? <AdminNotice>{notice}</AdminNotice> : null}

      {!data.canManageSelectedWorld ? (
        <AdminNotice tone="error">
          Multimodal diagnostics require world admin access.
        </AdminNotice>
      ) : null}

      <AdminSection
        title="Multimodal diagnostics overview"
        description="Diagnostics reuse the existing eval framework and summarize provider, media, invocation, visual, speech, and event-payload boundaries."
      >
        <div className="dashboard-grid">
          <AdminMetric
            label="Status"
            value={diagnostics?.status ?? "not loaded"}
            tone={statusTone}
          />
          <AdminMetric
            label="Blockers"
            value={blockerCount}
            tone={blockerCount > 0 ? "error" : "ok"}
          />
          <AdminMetric
            label="Warnings"
            value={warningCount}
            tone={warningCount > 0 ? "warning" : "ok"}
          />
          <AdminMetric label="Recommendations" value={diagnostics?.recommendations.length ?? 0} />
          <AdminMetric label="Evidence refs" value={diagnostics?.evidence_refs.length ?? 0} />
          <AdminMetric label="Recent runs" value={evalRuns.length} />
        </div>

        <form className="inline-form" onSubmit={handleLoad}>
          <select
            className="text-input"
            name="worldline_id"
            value={selectedWorldlineId}
            onChange={(event) => setSelectedWorldlineId(event.target.value)}
          >
            <option value="">select worldline</option>
            {data.worldlines.map((worldline) => (
              <option key={worldline.id} value={worldline.id}>
                {worldline.name} ({worldline.worldline_key})
              </option>
            ))}
          </select>
          <button
            className="secondary-button"
            type="submit"
            disabled={isBusy || !data.canManageSelectedWorld}
          >
            Load diagnostics
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={isBusy || !data.canManageSelectedWorld}
            onClick={handleRunEval}
          >
            Run multimodal smoke eval
          </button>
        </form>
      </AdminSection>

      {diagnostics === null ? (
        <AdminSection title="Diagnostic state">
          <AdminState title="No diagnostics loaded">
            Select a worldline to review the current multimodal smoke status.
          </AdminState>
        </AdminSection>
      ) : (
        <>
          <AdminSection
            title="Boundary summary"
            description="Only safe counts and status summaries are rendered. Evidence refs stay as IDs."
          >
            <div className="dashboard-grid">
              {summaryMetrics.map((metric) => (
                <AdminMetric
                  key={metric.label}
                  label={metric.label}
                  value={metric.value}
                  tone={metric.tone ?? "neutral"}
                />
              ))}
            </div>
            <AdminDescriptionList
              items={[
                { label: "Worldline", value: diagnostics.worldline_id },
                { label: "Generated", value: formatDate(diagnostics.generated_at) },
                { label: "Eval framework", value: "long_run_eval_runs" },
                { label: "Secret boundary", value: secretBoundaryLabel(metrics) },
                { label: "Event payload leaks", value: metricNumber(metrics, "events", "payload_leak_count") },
                { label: "Prompt snapshot leaks", value: metricNumber(metrics, "invocations", "prompt_snapshot_leak_count") },
              ]}
            />
          </AdminSection>

          <FindingsSection
            title="Blockers"
            findings={diagnostics.blockers}
            emptyTitle="No blockers"
            emptyMessage="The current sampled worldline has no blocking multimodal diagnostics."
          />

          <FindingsSection
            title="Warnings"
            findings={diagnostics.warnings}
            emptyTitle="No warnings"
            emptyMessage="The current sampled worldline has no warning diagnostics."
          />

          <AdminSection title="Recommendations">
            {diagnostics.recommendations.length === 0 ? (
              <AdminState title="No recommendations">
                Diagnostics did not return follow-up actions.
              </AdminState>
            ) : (
              <div className="resource-list">
                {diagnostics.recommendations.map((recommendation) => (
                  <article className="resource-row" key={recommendation}>
                    <div>
                      <h3>Recommendation</h3>
                      <p>{sanitizeText(recommendation)}</p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </AdminSection>
        </>
      )}

      <EvalRunsSection evalRuns={evalRuns} />
    </section>
  );
}

function FindingsSection({
  title,
  findings,
  emptyTitle,
  emptyMessage,
}: {
  title: string;
  findings: MultimodalDiagnosticFinding[];
  emptyTitle: string;
  emptyMessage: string;
}) {
  return (
    <AdminSection title={title}>
      <AdminTable
        caption={title}
        rows={findings}
        getRowKey={(finding) => `${finding.severity}:${finding.code}:${finding.message}`}
        columns={[
          { key: "severity", header: "Severity", render: (finding) => finding.severity },
          { key: "code", header: "Code", render: (finding) => finding.code },
          { key: "message", header: "Message", render: (finding) => sanitizeText(finding.message) },
          {
            key: "evidence",
            header: "Evidence refs",
            render: (finding) => formatEvidenceRefs(finding.evidence_refs),
          },
        ]}
        emptyTitle={emptyTitle}
        emptyMessage={emptyMessage}
      />
    </AdminSection>
  );
}

function EvalRunsSection({ evalRuns }: { evalRuns: MultimodalEvalRun[] }) {
  return (
    <AdminSection
      title="Recent multimodal eval runs"
      description="Runs are persisted in the existing release/eval framework. The table renders safe summaries only."
    >
      <AdminTable
        caption="Recent multimodal eval runs"
        rows={evalRuns}
        getRowKey={(run) => run.id}
        columns={[
          { key: "status", header: "Status", render: (run) => run.status },
          { key: "eval", header: "Eval key", render: (run) => run.eval_key },
          { key: "worldline", header: "Worldline", render: (run) => shortId(run.worldline_id) },
          { key: "started", header: "Started", render: (run) => formatDate(run.started_at) },
          { key: "blockers", header: "Findings", render: (run) => run.blockers.length },
          { key: "cost", header: "Cost", render: (run) => metricNumber(run.metrics, "invocations", "estimated_cost_total") },
          { key: "latency", header: "Avg latency", render: (run) => metricNumber(run.metrics, "invocations", "average_latency_ms") },
        ]}
        emptyTitle="No eval runs"
        emptyMessage="Run the multimodal smoke eval to persist release-framework evidence."
      />
    </AdminSection>
  );
}

function buildSummaryMetrics(diagnostics: MultimodalDiagnosticsResult | null): SummaryMetric[] {
  if (diagnostics === null) {
    return [];
  }
  const metrics = diagnostics.metrics;
  return [
    metric("Providers", metricNumber(metrics, "providers", "configured_count")),
    metric("Missing health", metricNumber(metrics, "providers", "providers_without_health_count"), "warning"),
    metric("Provider calls", metricNumber(metrics, "invocations", "provider_invocation_count")),
    metric("Prompt leaks", metricNumber(metrics, "invocations", "prompt_snapshot_leak_count"), "error"),
    metric("Media assets", metricNumber(metrics, "media_assets", "asset_count")),
    metric("Missing objects", metricNumber(metrics, "media_assets", "missing_object_count"), "error"),
    metric("Storage missing", metricNumber(metrics, "media_assets", "missing_storage_count"), "error"),
    metric("Sprite sets", metricNumber(metrics, "visual", "sprite_set_count")),
    metric("Sprite defaults missing", metricNumber(metrics, "visual", "sprite_sets_missing_default_count"), "error"),
    metric("Voice profiles", metricNumber(metrics, "speech", "voice_profile_count")),
    metric("Voice bindings missing", metricNumber(metrics, "speech", "agents_missing_default_voice_count"), "error"),
    metric("STT memory writes", metricNumber(metrics, "speech", "transcript_memory_write_count"), "error"),
  ];
}

function metric(label: string, value: string | number, alertTone?: "warning" | "error"): SummaryMetric {
  const numeric = typeof value === "number" ? value : Number(value);
  return {
    label,
    value,
    tone: alertTone !== undefined && Number.isFinite(numeric) && numeric > 0 ? alertTone : "neutral",
  };
}

function metricNumber(metrics: Record<string, unknown>, group: string, key: string): string | number {
  const groupValue = metrics[group];
  if (groupValue !== null && typeof groupValue === "object" && !Array.isArray(groupValue)) {
    const value = (groupValue as Record<string, unknown>)[key];
    if (typeof value === "number" || typeof value === "string") {
      return value;
    }
  }
  return "-";
}

function secretBoundaryLabel(metrics: Record<string, unknown>): string {
  const unsafe = metricNumber(metrics, "providers", "unsafe_provider_config_count");
  return unsafe === 0 ? "no unsafe config values" : `${unsafe} unsafe config values`;
}

function toneForStatus(status: string | null): "neutral" | "ok" | "warning" | "error" {
  if (status === "completed") {
    return "ok";
  }
  if (status === "warning") {
    return "warning";
  }
  if (status === "failed") {
    return "error";
  }
  return "neutral";
}

function formatEvidenceRefs(refs: MultimodalEvidenceRef[]): string {
  if (refs.length === 0) {
    return "-";
  }
  return refs.slice(0, 6).map((ref) => `${ref.kind}:${shortId(ref.id)}`).join(", ");
}

function formatDate(value: string): string {
  return new Date(value).toISOString();
}

function shortId(value: string): string {
  return value.length <= 12 ? value : value.slice(0, 12);
}

function sanitizeText(value: string): string {
  return sensitiveValue(value) ? "[redacted]" : truncate(value, 500);
}

function sensitiveValue(value: string): boolean {
  return (
    /media:\/\/|base64|\/var\/|\/tmp\/|[A-Za-z]:\\|sk-[A-Za-z0-9]|raw prompt|raw output/i.test(value)
    || isBase64Like(value)
  );
}

function isBase64Like(value: string): boolean {
  const normalized = value.trim();
  return (
    normalized.length >= 8
    && normalized.length % 4 === 0
    && /^[A-Za-z0-9+/]+={0,2}$/.test(normalized)
    && !/^[a-f0-9]{32,}$/i.test(normalized)
  );
}

function truncate(value: string, limit: number): string {
  return value.length <= limit ? value : `${value.slice(0, limit)}...`;
}
