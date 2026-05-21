"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import {
  AdminMetric,
  AdminNotice,
  AdminSection,
  AdminState,
} from "@/features/admin/admin-foundation";
import { formString, messageForError, optionalFormString } from "@/features/workspace/form-utils";
import {
  createBetaFeedbackReport,
  listBetaFeedbackReports,
  triageBetaFeedbackReport,
} from "@/lib/beta-feedback/client";
import type {
  BetaFeedbackEvidenceRef,
  BetaFeedbackIssueType,
  BetaFeedbackReport,
  BetaFeedbackReportStatus,
  BetaFeedbackSeverity,
} from "@/lib/beta-feedback/types";
import {
  betaFeedbackIssueTypes,
  betaFeedbackSeverities,
  betaFeedbackStatuses,
} from "@/lib/beta-feedback/types";
import type { BetaFeedbackData } from "@/lib/beta-feedback/server";

type BetaFeedbackPanelProps = {
  worldId: string;
  data: BetaFeedbackData;
};

type Notice = {
  tone: "success" | "error" | "warning";
  message: string;
};

export function BetaFeedbackPanel({ worldId, data }: BetaFeedbackPanelProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<Notice | null>(
    data.loadError === null ? null : { tone: "warning", message: data.loadError },
  );
  const [isBusy, setIsBusy] = useState(false);
  const [reports, setReports] = useState(data.reports);
  const statusCounts = useMemo(() => countBy(reports, "status"), [reports]);
  const selectedWorldlineId = data.worldlines[0]?.id ?? "";

  async function runAction(action: () => Promise<unknown>, success: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ tone: "success", message: success });
      router.refresh();
    } catch (error) {
      setNotice({ tone: "error", message: messageForError(error) });
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const worldlineId = formString(form, "worldline_id");
    const title = formString(form, "title");
    const description = formString(form, "description");
    await runAction(async () => {
      const report = await createBetaFeedbackReport(worldId, {
        worldline_id: worldlineId,
        issue_type: formString(form, "issue_type") as BetaFeedbackIssueType,
        severity: formString(form, "severity") as BetaFeedbackSeverity,
        title,
        description,
        reporter_note: optionalFormString(form, "reporter_note"),
        evidence_refs: evidenceRefsFromForm(form, worldlineId),
        metadata: { source: "web_feedback_panel" },
      });
      setReports((current) => [report, ...current]);
      event.currentTarget.reset();
    }, "Feedback submitted.");
  }

  async function handleFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const filtered = await listBetaFeedbackReports(worldId, {
        worldline_id: optionalFormString(form, "worldline_id"),
        status: optionalFormString(form, "status") as BetaFeedbackReportStatus | null,
        issue_type: optionalFormString(form, "issue_type") as BetaFeedbackIssueType | null,
      });
      setReports(filtered);
    }, "Feedback filters applied.");
  }

  async function handleTriage(event: FormEvent<HTMLFormElement>, reportId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      const updated = await triageBetaFeedbackReport(worldId, reportId, {
        status: formString(form, "status") as BetaFeedbackReportStatus,
        severity: formString(form, "severity") as BetaFeedbackSeverity,
        triage_note: optionalFormString(form, "triage_note"),
      });
      setReports((current) => current.map((report) => (report.id === updated.id ? updated : report)));
    }, "Feedback triaged.");
  }

  return (
    <section className="management-section beta-feedback-surface">
      {notice !== null ? <AdminNotice tone={notice.tone}>{notice.message}</AdminNotice> : null}

      <AdminSection
        title="Feedback overview"
        description="Private beta reports stay scoped to the tester and world admins. Evidence uses IDs only."
      >
        <div className="dashboard-grid">
          <AdminMetric label="Visible reports" value={reports.length} />
          <AdminMetric label="Submitted" value={statusCounts.submitted ?? 0} />
          <AdminMetric
            label="Critical"
            value={reports.filter((report) => report.severity === "critical").length}
            tone={reports.some((report) => report.severity === "critical") ? "error" : "neutral"}
          />
        </div>
      </AdminSection>

      <AdminSection
        title="Submit feedback"
        description="Use safe IDs to bind the report to scene, dialogue, persona, voice, image, provider, quota, session, or UX context."
      >
        {data.worldlines.length === 0 ? (
          <AdminState title="No worldlines">Feedback requires a worldline-scoped beta world.</AdminState>
        ) : (
          <form className="feedback-form" onSubmit={handleCreate}>
            <label className="field-label">
              Worldline
              <select className="text-input" name="worldline_id" defaultValue={selectedWorldlineId}>
                {data.worldlines.map((worldline) => (
                  <option key={worldline.id} value={worldline.id}>
                    {worldline.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Issue type
              <select className="text-input" name="issue_type" defaultValue="dialogue">
                {betaFeedbackIssueTypes.map((value) => (
                  <option key={value} value={value}>
                    {labelFor(value)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Severity
              <select className="text-input" name="severity" defaultValue="low">
                {betaFeedbackSeverities.map((value) => (
                  <option key={value} value={value}>
                    {labelFor(value)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label feedback-wide">
              Title
              <input className="text-input" name="title" required maxLength={200} />
            </label>
            <label className="field-label feedback-wide">
              Description
              <textarea className="text-input" name="description" rows={5} required maxLength={1200} />
            </label>
            <label className="field-label feedback-wide">
              Reporter note
              <textarea className="text-input" name="reporter_note" rows={3} maxLength={1000} />
            </label>
            <p className="inline-help feedback-wide">
              Evidence fields accept safe object IDs only. Do not paste storage paths, prompt text, provider credentials,
              or raw model output.
            </p>
            <div className="feedback-evidence-grid feedback-wide">
              <label>
                Conversation ID
                <input className="text-input" name="conversation_id" placeholder="conversation id" />
              </label>
              <label>
                Turn ID
                <input className="text-input" name="turn_id" placeholder="turn id" />
              </label>
              <label>
                Presentation ID
                <input className="text-input" name="presentation_id" placeholder="presentation id" />
              </label>
              <label>
                Media asset ID
                <input className="text-input" name="media_asset_id" placeholder="media asset id" />
              </label>
            </div>
            <button className="primary-button feedback-wide" type="submit" disabled={isBusy}>
              {isBusy ? "Submitting..." : "Submit feedback"}
            </button>
          </form>
        )}
      </AdminSection>

      <AdminSection title="Reports" description="Members see their own reports. Admins see all reports.">
        <form className="management-form" onSubmit={handleFilter}>
          <select className="text-input" name="worldline_id" defaultValue="">
            <option value="">all worldlines</option>
            {data.worldlines.map((worldline) => (
              <option key={worldline.id} value={worldline.id}>
                {worldline.name}
              </option>
            ))}
          </select>
          <select className="text-input" name="issue_type" defaultValue="">
            <option value="">all issue types</option>
            {betaFeedbackIssueTypes.map((value) => (
              <option key={value} value={value}>
                {labelFor(value)}
              </option>
            ))}
          </select>
          <select className="text-input" name="status" defaultValue="">
            <option value="">all statuses</option>
            {betaFeedbackStatuses.map((value) => (
              <option key={value} value={value}>
                {labelFor(value)}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit" disabled={isBusy}>
            Apply filters
          </button>
        </form>

        <div className="resource-list">
          {reports.length === 0 ? (
            <AdminState title="No feedback reports">Submitted beta reports will appear here.</AdminState>
          ) : (
            reports.map((report) => (
              <FeedbackReportRow
                canManage={data.canManageSelectedWorld}
                isBusy={isBusy}
                key={report.id}
                onTriage={handleTriage}
                report={report}
              />
            ))
          )}
        </div>
      </AdminSection>
    </section>
  );
}

type FeedbackReportRowProps = {
  report: BetaFeedbackReport;
  canManage: boolean;
  isBusy: boolean;
  onTriage: (event: FormEvent<HTMLFormElement>, reportId: string) => void;
};

function FeedbackReportRow({ report, canManage, isBusy, onTriage }: FeedbackReportRowProps) {
  return (
    <article className="resource-row feedback-report-row">
      <div className="feedback-report-summary">
        <h3>{report.title}</h3>
        <div className="status-pill-list" aria-label={`${report.title} feedback status`}>
          <span className="status-pill">{labelFor(report.issue_type)}</span>
          <span className="status-pill" data-tone={severityTone(report.severity)}>
            {labelFor(report.severity)}
          </span>
          <span className="status-pill" data-tone={statusTone(report.status)}>
            {labelFor(report.status)}
          </span>
        </div>
        <p>{report.description}</p>
        <p>
          Evidence: {report.evidence_refs.length} · Repairs: {report.repair_proposal_refs.length}
        </p>
      </div>
      {canManage ? (
        <form className="feedback-triage-form" onSubmit={(event) => onTriage(event, report.id)}>
          <select className="text-input" name="status" defaultValue={report.status}>
            {betaFeedbackStatuses.map((value) => (
              <option key={value} value={value}>
                {labelFor(value)}
              </option>
            ))}
          </select>
          <select className="text-input" name="severity" defaultValue={report.severity}>
            {betaFeedbackSeverities.map((value) => (
              <option key={value} value={value}>
                {labelFor(value)}
              </option>
            ))}
          </select>
          <textarea
            className="text-input"
            name="triage_note"
            placeholder="triage note"
            defaultValue={report.triage_note ?? ""}
            rows={3}
          />
          <button className="secondary-button" type="submit" disabled={isBusy}>
            {isBusy ? "Saving..." : "Save triage"}
          </button>
        </form>
      ) : null}
    </article>
  );
}

function evidenceRefsFromForm(form: FormData, worldlineId: string): BetaFeedbackEvidenceRef[] {
  const entries: Array<[BetaFeedbackEvidenceRef["kind"], string]> = [
    ["conversation", optionalFormString(form, "conversation_id") ?? ""],
    ["turn", optionalFormString(form, "turn_id") ?? ""],
    ["presentation", optionalFormString(form, "presentation_id") ?? ""],
    ["media_asset", optionalFormString(form, "media_asset_id") ?? ""],
  ];
  return entries
    .filter(([, id]) => id !== "")
    .map(([kind, id]) => ({ kind, id, worldline_id: worldlineId }));
}

function countBy<T extends Record<string, unknown>>(items: T[], key: keyof T): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const value = String(item[key]);
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

function labelFor(value: string): string {
  return value.replaceAll("_", " ");
}

function severityTone(severity: BetaFeedbackSeverity): "success" | "warning" | "error" {
  if (severity === "critical" || severity === "high") {
    return "error";
  }
  if (severity === "medium") {
    return "warning";
  }
  return "success";
}

function statusTone(status: BetaFeedbackReportStatus): "success" | "warning" | "error" {
  if (status === "resolved") {
    return "success";
  }
  return "warning";
}
