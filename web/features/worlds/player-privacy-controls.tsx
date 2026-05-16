"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  createPlayerDeleteRequest,
  createPlayerPrivacyExport,
} from "@/lib/worlds/client";
import type { PlayerPrivacyData } from "@/lib/worlds/server";
import type { PlayerPrivacyTargetKind } from "@/lib/worlds/types";
import { messageForError, optionalFormString } from "@/features/workspace/form-utils";

type PlayerPrivacyControlsProps = {
  worldId: string;
  data: PlayerPrivacyData;
};

type NoticeTone = "success" | "warning" | "error";

const TARGET_OPTIONS: { value: PlayerPrivacyTargetKind; label: string }[] = [
  { value: "all_player_data", label: "All player data" },
  { value: "player_profile", label: "Player profile" },
  { value: "player_choices", label: "Choices" },
  { value: "player_journal", label: "Journal" },
  { value: "notifications", label: "Notifications" },
  { value: "interventions", label: "Interventions" },
  { value: "conversation_references", label: "Conversation references" },
];

export function PlayerPrivacyControls({ worldId, data }: PlayerPrivacyControlsProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<{ message: string; tone: NoticeTone } | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const exportPreview = data.exportPreview;

  if (data.selectedWorld === null || exportPreview === null) {
    return (
      <section className="management-section">
        <p className="management-notice" data-tone="error">
          {data.loadError ?? "Player privacy controls are unavailable."}
        </p>
      </section>
    );
  }

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ message: successMessage, tone: "success" });
      router.refresh();
    } catch (error) {
      setNotice({ message: messageForError(error), tone: "error" });
    } finally {
      setIsBusy(false);
    }
  }

  async function handleExportRequest() {
    await runAction(async () => {
      await createPlayerPrivacyExport(worldId, {
        worldline_id: data.selectedWorldlineId,
      });
    }, "Export request recorded.");
  }

  async function handleDeleteRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      await createPlayerDeleteRequest(worldId, {
        worldline_id: data.selectedWorldlineId,
        target_ref_kind: form.get("target_ref_kind") as PlayerPrivacyTargetKind,
        reason: optionalFormString(form, "reason"),
      });
      formElement.reset();
    }, "Delete request sent for review.");
  }

  return (
    <section className="management-section player-surface">
      {notice !== null ? (
        <p className="management-notice" data-tone={notice.tone} role={notice.tone === "error" ? "alert" : "status"}>
          {notice.message}
        </p>
      ) : null}

      <section className="management-panel player-summary" aria-labelledby="privacy-summary-title">
        <div>
          <h2 className="section-title" id="privacy-summary-title">
            Export summary
          </h2>
          <p className="admin-section-copy">
            {data.selectedWorld.name} · {data.worldlines.length} worldline(s)
          </p>
        </div>
        <div className="player-metrics" aria-label="Player privacy counts">
          {Object.entries(exportPreview.counts).map(([key, count]) => (
            <span key={key}>
              {count} {labelForCount(key)}
            </span>
          ))}
        </div>
      </section>

      <div className="player-grid">
        <section className="management-panel" aria-labelledby="export-profile-title">
          <h2 className="section-title" id="export-profile-title">
            Profile
          </h2>
          <article className="resource-row">
            <div>
              <h3>{exportPreview.profile.display_name}</h3>
              <p>{exportPreview.profile.email}</p>
              <p>{exportPreview.profile.world_role ?? "world member"}</p>
            </div>
          </article>
          <button className="primary-button" type="button" onClick={handleExportRequest} disabled={isBusy}>
            Create export record
          </button>
        </section>

        <section className="management-panel" aria-labelledby="privacy-safeguards-title">
          <h2 className="section-title" id="privacy-safeguards-title">
            Safeguards
          </h2>
          <ul className="compact-list">
            {exportPreview.safeguards.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="management-panel" aria-labelledby="delete-request-title">
        <h2 className="section-title" id="delete-request-title">
          Delete requests
        </h2>
        <form className="player-form" onSubmit={handleDeleteRequest}>
          <select className="text-input" name="target_ref_kind" defaultValue="all_player_data">
            {TARGET_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <textarea className="text-input" name="reason" placeholder="Review note" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Request deletion review
          </button>
        </form>
        <RequestList requests={data.privacyRequests} />
      </section>
    </section>
  );
}

function RequestList({ requests }: { requests: PlayerPrivacyData["privacyRequests"] }) {
  if (requests.length === 0) {
    return <p className="management-notice">No privacy requests.</p>;
  }
  return (
    <div className="resource-list">
      {requests.map((request) => (
        <article className="resource-row" key={request.id}>
          <div>
            <h3>
              {request.request_kind} · {request.status}
            </h3>
            <p>{request.target_ref_kind ?? "all_player_data"}</p>
            <p>{dateLabel(request.created_at)}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function labelForCount(key: string): string {
  return key.replaceAll("_", " ");
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
