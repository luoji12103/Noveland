"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import {
  bootstrapPrivateBetaPlayerProfile,
  redeemPrivateBetaInvite,
} from "@/lib/private-beta/client";
import type { PrivateBetaOnboardingData } from "@/lib/private-beta/server";
import type { PrivateBetaAccess } from "@/lib/private-beta/types";
import { messageForError } from "@/features/workspace/form-utils";

type PrivateBetaOnboardingProps = {
  data: PrivateBetaOnboardingData;
};

type Notice = {
  tone: "success" | "error" | "warning";
  message: string;
};

export function PrivateBetaOnboarding({ data }: PrivateBetaOnboardingProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<Notice | null>(
    data.loadError === null ? null : { tone: "warning", message: data.loadError },
  );
  const [isBusy, setIsBusy] = useState(false);
  const access = data.status?.access ?? [];
  const guidance = data.status?.guidance ?? [
    "Redeem an invite before creating a player identity.",
    "Ask the operator for help if the invite has expired or was revoked.",
  ];

  async function handleRedeem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const token = String(form.get("token") ?? "").trim();
    if (token === "") {
      setNotice({ tone: "error", message: "Invite token is required." });
      return;
    }
    await runAction(async () => {
      await redeemPrivateBetaInvite(token);
    }, "Invitation redeemed.");
    formElement.reset();
  }

  async function handleProfile(event: FormEvent<HTMLFormElement>, item: PrivateBetaAccess) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const displayName = String(form.get("display_name") ?? "").trim();
    if (displayName === "") {
      setNotice({ tone: "error", message: "Player display name is required." });
      return;
    }
    await runAction(async () => {
      await bootstrapPrivateBetaPlayerProfile(item.world_id, {
        worldline_id: item.worldline_id,
        display_name: displayName,
        profile: {},
      });
    }, "Player identity is ready.");
  }

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ tone: "success", message: successMessage });
      router.refresh();
    } catch (error) {
      setNotice({ tone: "error", message: messageForError(error) });
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="management-section private-beta-surface">
      {notice !== null ? (
        <p className="management-notice" data-tone={notice.tone} role={notice.tone === "error" ? "alert" : "status"}>
          {notice.message}
        </p>
      ) : null}

      <section className="management-panel" aria-labelledby="redeem-private-beta-title">
        <div className="admin-section-header">
          <div>
            <h2 className="section-title" id="redeem-private-beta-title">
              Redeem invite
            </h2>
            <p className="admin-section-copy">
              Paste the invite token from the operator. The token is submitted once and is not shown in the access list.
            </p>
          </div>
        </div>
        <form className="private-beta-form" onSubmit={handleRedeem}>
          <label className="field-label" htmlFor="private-beta-token">
            Invite token
          </label>
          <input
            className="text-input"
            id="private-beta-token"
            name="token"
            autoComplete="off"
            spellCheck={false}
          />
          <button className="primary-button" type="submit" disabled={isBusy}>
            Redeem invite
          </button>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="private-beta-worlds-title">
        <h2 className="section-title" id="private-beta-worlds-title">
          Invited worlds
        </h2>
        {access.length === 0 ? (
          <p className="management-notice">No redeemed private beta access.</p>
        ) : (
          <div className="resource-list">
            {access.map((item) => (
              <article className="resource-row private-beta-access-row" key={item.invite_id}>
                <div>
                  <h3>{item.world_name}</h3>
                  <p>
                    {item.beta_role} · {item.status}
                    {item.worldline_name === null ? "" : ` · ${item.worldline_name}`}
                  </p>
                  <p>Expires {dateLabel(item.expires_at)}</p>
                </div>
                {item.player_profile === null ? (
                  <form className="private-beta-inline-form" onSubmit={(event) => void handleProfile(event, item)}>
                    <input className="text-input" name="display_name" placeholder="Player display name" />
                    <button className="primary-button" type="submit" disabled={isBusy}>
                      Create identity
                    </button>
                  </form>
                ) : (
                  <div className="private-beta-actions">
                    <p>{item.player_profile.display_name}</p>
                    <Link className="secondary-button" href={`/worlds/${item.world_id}/player`}>
                      Open player surface
                    </Link>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="management-panel" aria-labelledby="private-beta-guidance-title">
        <h2 className="section-title" id="private-beta-guidance-title">
          First-run guidance
        </h2>
        <ul className="compact-list">
          {guidance.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
