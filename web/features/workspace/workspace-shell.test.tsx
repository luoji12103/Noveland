import { createElement, type ComponentProps } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "@/features/workspace/workspace-shell";

vi.mock("next/image", () => ({
  default: ({ priority, ...props }: ComponentProps<"img"> & { priority?: boolean }) => {
    void priority;
    return createElement("img", props);
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

describe("WorkspaceShell", () => {
  it("includes v0.4 world admin navigation links", () => {
    render(
      <WorkspaceShell
        subject={{
          user_id: "user-1",
          email: "admin@example.com",
          display_name: "Admin",
          roles: ["platform_admin"],
        }}
        title="World"
        intro="Workspace"
        worldId={RESERVED_WORLD_ID}
      >
        <p>Content</p>
      </WorkspaceShell>,
    );

    const worldPath = `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}`;

    expect(screen.getAllByRole("link", { name: "Providers" })[0]).toHaveAttribute(
      "href",
      `${worldPath}/providers`,
    );
    expect(screen.getByRole("link", { name: "Media" })).toHaveAttribute(
      "href",
      `${worldPath}/media`,
    );
    expect(screen.getByRole("link", { name: "Visual" })).toHaveAttribute(
      "href",
      `${worldPath}/visual`,
    );
    expect(screen.getByRole("link", { name: "Speech" })).toHaveAttribute(
      "href",
      `${worldPath}/speech`,
    );
    expect(screen.getByRole("link", { name: "Invocations" })).toHaveAttribute(
      "href",
      `${worldPath}/invocations`,
    );
    expect(screen.getByRole("link", { name: "Diagnostics" })).toHaveAttribute(
      "href",
      `${worldPath}/diagnostics`,
    );
  });

const RESERVED_WORLD_ID = "world/admin?scope=true#frag";
});
