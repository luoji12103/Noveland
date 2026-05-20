import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BetaFeedbackPanel } from "@/features/private-beta/beta-feedback-panel";
import {
  createBetaFeedbackReport,
  listBetaFeedbackReports,
  triageBetaFeedbackReport,
} from "@/lib/beta-feedback/client";
import type { BetaFeedbackData } from "@/lib/beta-feedback/server";
import type { BetaFeedbackReport } from "@/lib/beta-feedback/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/beta-feedback/client", () => ({
  createBetaFeedbackReport: vi.fn(),
  listBetaFeedbackReports: vi.fn(),
  triageBetaFeedbackReport: vi.fn(),
}));

describe("BetaFeedbackPanel", () => {
  it("renders feedback reports without internal evidence leakage", () => {
    render(<BetaFeedbackPanel worldId="world-1" data={feedbackData} />);

    expect(screen.getByRole("heading", { name: "Feedback overview" })).toBeVisible();
    expect(screen.getByText("OOC response")).toBeVisible();
    expect(screen.getByText(/dialogue · medium · submitted/)).toBeVisible();
    expect(serializedDocument()).not.toMatch(
      /storage_uri|media:\/\/|raw_prompt|raw_output|prompt_snapshot|sk-live-secret|base64/i,
    );
  });

  it("submits feedback, filters reports, and lets admins triage", async () => {
    vi.mocked(createBetaFeedbackReport).mockResolvedValue(nextReport);
    vi.mocked(listBetaFeedbackReports).mockResolvedValue([nextReport]);
    vi.mocked(triageBetaFeedbackReport).mockResolvedValue({
      ...feedbackReport,
      status: "investigating",
      triage_note: "Needs content repair.",
    });
    render(<BetaFeedbackPanel worldId="world-1" data={feedbackData} />);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Wrong voice" } });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "The voice style did not match the scene." },
    });
    fireEvent.change(screen.getByPlaceholderText("conversation id"), {
      target: { value: "conversation-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    await waitFor(() => {
      expect(createBetaFeedbackReport).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          title: "Wrong voice",
          evidence_refs: [
            {
              kind: "conversation",
              id: "conversation-1",
              worldline_id: "worldline-1",
            },
          ],
        }),
      );
    });

    fireEvent.change(screen.getByDisplayValue("all issue types"), {
      target: { value: "voice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(listBetaFeedbackReports).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ issue_type: "voice" }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("triage note"), {
      target: { value: "Needs content repair." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save triage" }));

    await waitFor(() => {
      expect(triageBetaFeedbackReport).toHaveBeenCalledWith(
        "world-1",
        "feedback-2",
        expect.objectContaining({ triage_note: "Needs content repair." }),
      );
    });
  });
});

function serializedDocument(): string {
  return document.body.textContent ?? "";
}

const feedbackReport: BetaFeedbackReport = {
  id: "feedback-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  reporter_user_id: "user-1",
  player_actor_id: "player-1",
  issue_type: "dialogue",
  severity: "medium",
  status: "submitted",
  title: "OOC response",
  description: "The character ignored the relationship state.",
  reporter_note: "Safe tester note.",
  evidence_refs: [
    {
      kind: "conversation",
      id: "conversation-1",
      label: "current scene",
      worldline_id: "worldline-1",
      metadata: {},
    },
  ],
  repair_proposal_refs: [],
  triage_note: null,
  triaged_by_actor_ref: null,
  triaged_at: null,
  moderation_report_id: null,
  metadata: {
    safe: true,
    storage_uri: "media://not-rendered",
    raw_prompt: "not-rendered",
  },
  created_at: "2026-05-20T00:00:00.000Z",
  updated_at: "2026-05-20T00:00:00.000Z",
};

const nextReport: BetaFeedbackReport = {
  ...feedbackReport,
  id: "feedback-2",
  issue_type: "voice",
  title: "Wrong voice",
  description: "The voice style did not match the scene.",
};

const feedbackData: BetaFeedbackData = {
  worlds: [
    {
      id: "world-1",
      owner_user_id: "owner-1",
      slug: "demo",
      name: "Demo World",
      description: null,
      rules_config: {},
      memory_backend_profile_id: null,
      memory_plugin_identifier: "builtin.local",
      memory_plugin_config: {},
      world_rules_plugin_identifier: "builtin.default",
      world_rules_plugin_config: {},
      is_active: true,
    },
  ],
  selectedWorld: null,
  worldlines: [
    {
      id: "worldline-1",
      world_id: "world-1",
      worldline_key: "primary",
      name: "Primary",
      description: null,
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: null,
      status: "active",
      created_by_actor_ref: "system:test",
      metadata: {},
      created_at: "2026-05-20T00:00:00.000Z",
      updated_at: "2026-05-20T00:00:00.000Z",
    },
  ],
  reports: [feedbackReport],
  canManageSelectedWorld: true,
  loadError: null,
};
