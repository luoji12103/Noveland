import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WorldlineBrowser } from "@/features/worlds/worldline-browser";
import type { WorldlineBrowserData } from "@/lib/worlds/server";

describe("WorldlineBrowser", () => {
  it("renders read-only branch inventory and safe comparison counts", () => {
    render(<WorldlineBrowser data={worldlineData} />);

    expect(screen.getByRole("heading", { name: "Worldline browser" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Primary Worldline" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Empty Fork" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Compare worldlines" })).toBeVisible();
    expect(screen.getByText("Divergent events")).toBeVisible();
    expect(screen.getByText("Choice deltas")).toBeVisible();
    expect(screen.queryByRole("button", { name: /rollback|merge|switch|fork/i })).toBeNull();
    expect(serializedDocument()).not.toMatch(
      /storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret|payload|\/var\/|\/tmp\//i,
    );
  });

  it("shows safe empty and unavailable states", () => {
    render(
      <WorldlineBrowser
        data={{
          ...worldlineData,
          worldlines: [],
          baseWorldlineId: null,
          compareWorldlineId: null,
          comparison: null,
          comparisonError: null,
        }}
      />,
    );

    expect(screen.getByText("No worldlines are available.")).toBeVisible();
    expect(screen.getByText("Select two branches to compare safe summaries.")).toBeVisible();
  });

  it("handles comparison authorization gaps without leaking details", () => {
    render(
      <WorldlineBrowser
        data={{
          ...worldlineData,
          comparison: null,
          comparisonError: "Comparison is unavailable for the selected branches.",
        }}
      />,
    );

    expect(screen.getByText("Comparison is unavailable for the selected branches.")).toBeVisible();
    expect(serializedDocument()).not.toMatch(/payload|raw_prompt|raw_output|storage_uri|secret/i);
  });
});

function serializedDocument(): string {
  return document.body.textContent ?? "";
}

const worldlineData: WorldlineBrowserData = {
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
      name: "Primary Worldline",
      description: null,
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: null,
      status: "active",
      created_by_actor_ref: "system:test",
      metadata: {},
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
    {
      id: "worldline-2",
      world_id: "world-1",
      worldline_key: "empty-fork",
      name: "Empty Fork",
      description: null,
      parent_worldline_id: "worldline-1",
      forked_from_snapshot_id: null,
      fork_event_sequence: 42,
      status: "active",
      created_by_actor_ref: "user:test",
      metadata: {},
      created_at: "2026-04-18T00:00:00.000Z",
      updated_at: "2026-04-18T00:00:00.000Z",
    },
  ],
  baseWorldlineId: "worldline-1",
  compareWorldlineId: "worldline-2",
  comparison: {
    base_worldline_id: "worldline-1",
    compare_worldline_id: "worldline-2",
    fork_event_sequence: 42,
    divergent_event_count: 3,
    relationship_delta_count: 1,
    faction_delta_count: 0,
    choice_delta_count: 2,
  },
  comparisonError: null,
  loadError: null,
};
