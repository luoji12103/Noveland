import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PlayerInteractions } from "@/features/worlds/player-interactions";
import {
  bindPlayerActor,
  createIntervention,
  previewPlayerChoiceConsequences,
  recordPlayerChoice,
  upsertPlayerSessionResume,
} from "@/lib/worlds/client";
import type { PlayerInteractionData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>(
    "@/lib/worlds/client",
  );
  return {
    ...actual,
    bindPlayerActor: vi.fn(),
    createIntervention: vi.fn(),
    previewPlayerChoiceConsequences: vi.fn(),
    recordPlayerChoice: vi.fn(),
    upsertPlayerSessionResume: vi.fn(),
  };
});

describe("PlayerInteractions", () => {
  it("renders player records without hidden evidence", () => {
    const data = {
      ...playerData,
      resume: { ...playerData.resume!, conversation_session_id: RESERVED_CONVERSATION_ID },
    };

    render(<PlayerInteractions worldId={RESERVED_WORLD_ID} data={data} />);

    expect(screen.getByRole("heading", { name: "Player interactions" })).toBeVisible();
    expect(screen.getAllByText("Member Player").length).toBeGreaterThan(0);
    expect(screen.getByText("Festival prep")).toBeVisible();
    expect(screen.getByText("Club room notice")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Resume" })).toBeVisible();
    expect(screen.getAllByText("Ready to resume.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("active").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/player/privacy`,
    );
    expect(screen.getByRole("link", { name: "Restore scene" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/reader/conversations/${encodeURIComponent(
        RESERVED_CONVERSATION_ID,
      )}/scene`,
    );
    expect(screen.getByText("0 relationship update(s)")).toBeVisible();
    expect(serializedDocument()).not.toMatch(
      /storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret|\/var\/|\/tmp\//i,
    );
  });

  it("records choices and interventions through existing client helpers", async () => {
    vi.mocked(previewPlayerChoiceConsequences).mockResolvedValue({
      relationship_updates: [],
      faction_updates: [],
      offscreen_events: [],
      diagnostics: ["0 relationship update(s)"],
    });
    vi.mocked(recordPlayerChoice).mockResolvedValue(playerData.playerChoices[0]);
    vi.mocked(createIntervention).mockResolvedValue({
      ...playerData.interventions[0],
      id: "intervention-2",
    });
    render(<PlayerInteractions worldId="world-1" data={playerData} />);

    fireEvent.change(screen.getByPlaceholderText("choice-key"), {
      target: { value: "festival-follow-up" },
    });
    fireEvent.change(screen.getByPlaceholderText("Choice prompt"), {
      target: { value: "Follow up after school?" },
    });
    fireEvent.change(screen.getByPlaceholderText("Selected option"), {
      target: { value: "Send a message." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview choice" }));

    await waitFor(() => {
      expect(previewPlayerChoiceConsequences).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          player_actor_id: "actor-1",
          choice_key: "festival-follow-up",
          apply: false,
        }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Record choice" }));
    await waitFor(() => {
      expect(recordPlayerChoice).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ selected_option: "Send a message.", apply: true }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("Intervention prompt"), {
      target: { value: "Contact the guide." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit intervention" }));
    await waitFor(() => {
      expect(createIntervention).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          player_actor_id: "actor-1",
          intervention_kind: "contact",
          prompt: "Contact the guide.",
        }),
      );
    });
  });

  it("binds a player actor when none exists", async () => {
    vi.mocked(bindPlayerActor).mockResolvedValue(playerData.playerActors[0]);
    render(<PlayerInteractions worldId="world-1" data={{ ...playerData, playerActors: [] }} />);

    fireEvent.change(screen.getByPlaceholderText("Player display name"), {
      target: { value: "New Player" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Bind player actor" }));

    await waitFor(() => {
      expect(bindPlayerActor).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ display_name: "New Player", worldline_id: "worldline-1" }),
      );
    });
  });

  it("saves server-owned resume state without leaking hidden evidence", async () => {
    vi.mocked(upsertPlayerSessionResume).mockResolvedValue(playerData.resume!);
    render(<PlayerInteractions worldId="world-1" data={playerData} />);

    fireEvent.change(screen.getByPlaceholderText("Conversation id"), {
      target: { value: "conversation-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save resume" }));

    await waitFor(() => {
      expect(upsertPlayerSessionResume).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          player_actor_id: "actor-1",
          conversation_session_id: "conversation-2",
          recovery_status: "ready",
        }),
      );
    });
    expect(serializedDocument()).not.toMatch(/storage_uri|raw_prompt|raw_output|prompt_snapshot|secret/i);
  });

  it("explains missing resume state without exposing diagnostics", () => {
    render(<PlayerInteractions worldId="world-1" data={{ ...playerData, resume: null }} />);

    expect(
      screen.getByText("No resume state stored yet. Save a server-owned recovery point before external testing."),
    ).toBeVisible();
    expect(serializedDocument()).not.toMatch(/storage_uri|raw_prompt|raw_output|prompt_snapshot|secret/i);
  });
});

function serializedDocument(): string {
  return document.body.textContent ?? "";
}

const RESERVED_WORLD_ID = "world/player?mode=resume#frag";
const RESERVED_CONVERSATION_ID = "conversation/live?resume=true#frag";

const playerData: PlayerInteractionData = {
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
  playerActors: [
    {
      id: "actor-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      actor_ref: "player:user-1:primary",
      display_name: "Member Player",
      current_scene_id: "scene-1",
      profile: {},
      is_active: true,
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  playerChoices: [
    {
      id: "choice-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      player_actor_id: "actor-1",
      choice_key: "festival-prep",
      choice_kind: "route",
      prompt: "Hidden from event payload assertions.",
      selected_option: "Stay after school.",
      context: {},
      consequence_preview: { diagnostics: ["0 relationship update(s)"] },
      applied_event_id: "event-1",
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  playerJournal: [
    {
      id: "journal-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      player_actor_id: "actor-1",
      entry_kind: "choice",
      title: "Festival prep",
      body: "The player helped with festival preparations.",
      source_event_id: "event-1",
      source_ref: "choice-1",
      visibility: "player_private",
      metadata: {},
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  notifications: [
    {
      id: "notification-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      notification_kind: "rumor",
      title: "Club room notice",
      body: "Someone mentioned the hidden letter.",
      source_event_id: null,
      source_ref: null,
      status: "unread",
      metadata: {},
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  interventions: [
    {
      id: "intervention-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      user_id: "user-1",
      player_actor_id: "actor-1",
      intervention_kind: "contact",
      target_agent_id: "agent-1",
      target_scene_id: null,
      prompt: "Do not render this prompt in history.",
      choice_id: "choice-2",
      event_id: "event-2",
      status: "recorded",
      metadata: {},
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  resume: {
    id: "resume-1",
    world_id: "world-1",
    worldline_id: "worldline-1",
    user_id: "user-1",
    player_actor_id: "actor-1",
    conversation_session_id: "conversation-1",
    scene_id: "scene-1",
    last_turn_id: "turn-1",
    last_presentation_id: "presentation-1",
    route_state: { source: "player_resume_panel" },
    resume_state: { surface: "player" },
    recovery_status: "ready",
    recovery_label: "Ready to resume.",
    available_actions: ["open_player_surface", "open_reader_playback"],
    status: "active",
    last_seen_at: "2026-04-17T00:00:00.000Z",
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "club-room",
      name: "Club room",
      description: null,
      region_key: null,
      location_tags: [],
      opening_rules: {},
      is_active: true,
    },
  ],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      source_preset_id: null,
      source_preset_version: null,
      agent_key: "guide",
      display_name: "Guide",
      kind: "narrative_agent",
      provider_profile_id: null,
      narrative_role: "main_character",
      importance: "lead",
      canon_status: "canon",
      character_category: "main_character",
      character_profile: {},
      config: {},
      is_enabled: true,
    },
  ],
  selectedWorldlineId: "worldline-1",
  loadError: null,
};
