import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PlayerPrivacyControls } from "@/features/worlds/player-privacy-controls";
import {
  createPlayerDeleteRequest,
  createPlayerPrivacyExport,
} from "@/lib/worlds/client";
import type { PlayerPrivacyData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>(
    "@/lib/worlds/client",
  );
  return {
    ...actual,
    createPlayerDeleteRequest: vi.fn(),
    createPlayerPrivacyExport: vi.fn(),
  };
});

describe("PlayerPrivacyControls", () => {
  it("renders safe export summary and request status", () => {
    render(<PlayerPrivacyControls worldId="world-1" data={privacyData} />);

    expect(screen.getByRole("heading", { name: "Export summary" })).toBeVisible();
    expect(screen.getByText("member@example.test")).toBeVisible();
    expect(screen.getByText("1 choices")).toBeVisible();
    expect(screen.getByText("delete · requested")).toBeVisible();
    expect(serializedDocument()).not.toMatch(
      /storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret|\/var\/|\/tmp\//i,
    );
  });

  it("creates export and deletion requests", async () => {
    vi.mocked(createPlayerPrivacyExport).mockResolvedValue({
      ...privacyData.exportPreview!,
      request_id: "request-export-2",
    });
    vi.mocked(createPlayerDeleteRequest).mockResolvedValue({
      ...privacyData.privacyRequests[0],
      id: "request-delete-2",
    });
    render(<PlayerPrivacyControls worldId="world-1" data={privacyData} />);

    fireEvent.click(screen.getByRole("button", { name: "Create export record" }));
    await waitFor(() => {
      expect(createPlayerPrivacyExport).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
      });
    });

    fireEvent.change(screen.getByPlaceholderText("Review note"), {
      target: { value: "Please review my player journal." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Request deletion review" }));
    await waitFor(() => {
      expect(createPlayerDeleteRequest).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          target_ref_kind: "all_player_data",
          reason: "Please review my player journal.",
        }),
      );
    });
  });
});

function serializedDocument(): string {
  return document.body.textContent ?? "";
}

const privacyData: PlayerPrivacyData = {
  worlds: [],
  selectedWorld: {
    id: "world-1",
    owner_user_id: "owner-1",
    slug: "world-one",
    name: "World One",
    description: null,
    rules_config: {},
    memory_backend_profile_id: null,
    memory_plugin_identifier: "builtin.mem0",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.rules",
    world_rules_plugin_config: {},
    is_active: true,
  },
  worldlines: [
    {
      id: "worldline-1",
      world_id: "world-1",
      worldline_key: "primary",
      name: "Primary",
      description: null,
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: 0,
      status: "active",
      created_by_actor_ref: "system:test",
      metadata: {},
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  selectedWorldlineId: "worldline-1",
  exportPreview: {
    request_id: null,
    world_id: "world-1",
    worldline_id: "worldline-1",
    user_id: "user-1",
    generated_at: "2026-04-17T00:00:00.000Z",
    profile: {
      user_id: "user-1",
      email: "member@example.test",
      display_name: "Member",
      world_role: "human_user",
    },
    counts: {
      player_actors: 1,
      choices: 1,
      journal_entries: 1,
      notifications: 1,
      interventions: 0,
      conversation_references: 1,
    },
    player_actors: [],
    choices: [
      {
        id: "choice-1",
        worldline_id: "worldline-1",
        player_actor_id: "actor-1",
        choice_key: "help-festival",
        choice_kind: "route",
        selected_option: "Stay after school.",
        applied_event_id: "event-1",
        created_at: "2026-04-17T00:00:00.000Z",
        updated_at: "2026-04-17T00:00:00.000Z",
      },
    ],
    journal_entries: [],
    notifications: [],
    interventions: [],
    conversation_references: [
      {
        id: "conversation-1",
        worldline_id: "worldline-1",
        session_key: "opening",
        title: "Opening",
        scope_type: "world",
        mode: "manual_chain",
        status: "completed",
        scene_id: null,
        created_at: "2026-04-17T00:00:00.000Z",
        updated_at: "2026-04-17T00:00:00.000Z",
      },
    ],
    safeguards: [
      "raw prompts and raw outputs are excluded",
      "storage paths and encoded data are excluded",
      "shared canonical world history is not deleted by privacy workflows",
    ],
  },
  privacyRequests: [
    {
      id: "request-delete-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      request_kind: "delete",
      status: "requested",
      target_ref_kind: "all_player_data",
      target_ref_id: null,
      reason: "Review player data.",
      summary: { counts: { choices: 1 } },
      redaction_plan: { automatic_delete: false },
      created_by_actor_ref: "user:user-1",
      reviewed_by_actor_ref: null,
      reviewed_at: null,
      review_note: null,
      metadata: {},
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  loadError: null,
};
