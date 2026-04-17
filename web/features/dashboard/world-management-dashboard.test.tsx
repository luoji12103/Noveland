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
    expect(screen.getByRole("button", { name: "Create scene" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create agent" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Owner" })).toBeInTheDocument();
  });

  it("hides management controls for read-only world members", () => {
    render(<WorldManagementDashboard subject={humanUser} initialData={readOnlyData} />);

    expect(screen.getByText("Read-only world access.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save world" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume clock" })).not.toBeInTheDocument();
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
  agents: [],
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
  canManageSelectedWorld: false,
  loadError: null,
};
