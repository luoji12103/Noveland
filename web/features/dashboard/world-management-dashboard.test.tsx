import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorldManagementDashboard } from "@/features/dashboard/world-management-dashboard";
import type { AuthSubject } from "@/lib/auth/types";
import type { WorldDashboardData } from "@/lib/worlds/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("WorldManagementDashboard", () => {
  it("renders an empty platform admin state with create controls", () => {
    render(<WorldManagementDashboard subject={platformAdmin} initialData={emptyData} />);

    expect(screen.getByRole("heading", { name: "Create world" })).toBeInTheDocument();
    expect(screen.getByText("0 visible")).toBeInTheDocument();
    expect(screen.getByText("No worlds yet")).toBeInTheDocument();
  });

  it("renders admin management controls for a selected world", () => {
    render(<WorldManagementDashboard subject={platformAdmin} initialData={adminData} />);

    expect(screen.getByRole("heading", { name: "First World" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save world" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "World clock" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resume clock" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Replay and snapshots" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create snapshot" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Schedule rules" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent calendar" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent memory" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create scene" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create agent" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Owner" })).toBeInTheDocument();
  });

  it("hides management controls for read-only world members", () => {
    render(<WorldManagementDashboard subject={humanUser} initialData={readOnlyData} />);

    expect(screen.getByText("Read-only world access.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save world" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume clock" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create snapshot" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Home" })).toBeInTheDocument();
  });
});

const platformAdmin: AuthSubject = {
  user_id: "00000000-0000-4000-8000-000000000001",
  email: "admin@example.test",
  display_name: "Admin",
  roles: ["platform_admin"],
};

const humanUser: AuthSubject = {
  user_id: "00000000-0000-4000-8000-000000000002",
  email: "member@example.test",
  display_name: "Member",
  roles: [],
};

const emptyData: WorldDashboardData = {
  worlds: [],
  selectedWorldId: null,
  scenes: [],
  agents: [],
  memberships: [],
  clock: null,
  replayState: null,
  latestSnapshot: null,
  selectedAgentId: null,
  calendarEntries: [],
  scheduleRules: [],
  memoryItems: [],
  canManageSelectedWorld: false,
  loadError: null,
};

const adminData: WorldDashboardData = {
  worlds: [
    {
      id: "world-1",
      owner_user_id: platformAdmin.user_id,
      slug: "first-world",
      name: "First World",
      description: null,
      rules_config: {},
      is_active: true,
    },
  ],
  selectedWorldId: "world-1",
  scenes: [],
  agents: [],
  memberships: [
    {
      id: "membership-1",
      world_id: "world-1",
      user_id: platformAdmin.user_id,
      role: "world_admin",
      user: {
        id: platformAdmin.user_id,
        email: platformAdmin.email,
        display_name: "Owner",
        is_active: true,
      },
    },
  ],
  clock: {
    world_id: "world-1",
    status: "paused",
    current_world_time: "2026-04-17T00:00:00.000Z",
    effective_world_time: "2026-04-17T00:00:00.000Z",
    wall_time_anchor: null,
    speed_multiplier: "1",
    revision: 0,
  },
  replayState: {
    world_id: "world-1",
    schema_version: "world_state.v1",
    source_sequence: 0,
    clock: null,
    applied_event_count: 0,
    unhandled_event_count: 0,
  },
  latestSnapshot: null,
  selectedAgentId: null,
  calendarEntries: [],
  scheduleRules: [
    {
      id: "rule-1",
      world_id: "world-1",
      rule_key: "weekday",
      name: "Weekday",
      kind: "weekday",
      config: {},
      is_enabled: true,
    },
  ],
  memoryItems: [
    {
      id: "memory-1",
      world_id: "world-1",
      agent_id: "agent-1",
      content: "Memory content",
      metadata: { source: "test" },
      embedding: [1, 0, 0],
      visibility: "private",
      is_active: true,
      source_event_id: null,
      score: null,
    },
  ],
  canManageSelectedWorld: true,
  loadError: null,
};

const readOnlyData: WorldDashboardData = {
  worlds: adminData.worlds,
  selectedWorldId: "world-1",
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "home",
      name: "Home",
      description: null,
      is_active: true,
    },
  ],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      agent_key: "guide",
      display_name: "Guide",
      kind: "role_agent",
      config: {},
      is_enabled: true,
    },
  ],
  memberships: [],
  clock: {
    world_id: "world-1",
    status: "running",
    current_world_time: "2026-04-17T00:00:00.000Z",
    effective_world_time: "2026-04-17T00:01:00.000Z",
    wall_time_anchor: "2026-04-17T00:00:00.000Z",
    speed_multiplier: "1",
    revision: 1,
  },
  replayState: {
    world_id: "world-1",
    schema_version: "world_state.v1",
    source_sequence: 1,
    clock: {
      status: "running",
      current_world_time: "2026-04-17T00:01:00.000Z",
      effective_world_time: "2026-04-17T00:01:00.000Z",
      wall_time_anchor: "2026-04-17T00:00:00.000Z",
      speed_multiplier: "1",
      revision: 1,
      last_event_id: "event-1",
      last_event_sequence: 1,
    },
    applied_event_count: 1,
    unhandled_event_count: 0,
  },
  latestSnapshot: {
    id: "snapshot-1",
    world_id: "world-1",
    covers_event_sequence: 1,
    schema_version: "world_state.v1",
    status: "valid",
    payload: {},
    payload_uri: null,
    metadata: {},
    created_by_event_id: "event-2",
    created_at: "2026-04-17T00:02:00.000Z",
  },
  selectedAgentId: "agent-1",
  calendarEntries: [
    {
      id: "entry-1",
      world_id: "world-1",
      agent_id: "agent-1",
      title: "Morning scene",
      description: null,
      starts_at: "2030-01-01T08:00:00.000Z",
      ends_at: null,
      recurrence_rule: null,
      status: "active",
      metadata: {},
    },
  ],
  scheduleRules: [],
  memoryItems: [
    {
      id: "memory-1",
      world_id: "world-1",
      agent_id: "agent-1",
      content: "Read-only memory",
      metadata: {},
      embedding: [1, 0, 0],
      visibility: "private",
      is_active: true,
      source_event_id: null,
      score: 0.91,
    },
  ],
  canManageSelectedWorld: false,
  loadError: null,
};
