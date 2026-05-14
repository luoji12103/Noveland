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
        worldId="world-1"
      >
        <p>Content</p>
      </WorkspaceShell>,
    );

    expect(screen.getAllByRole("link", { name: "Providers" })[0]).toHaveAttribute(
      "href",
      "/worlds/world-1/providers",
    );
    expect(screen.getByRole("link", { name: "Media" })).toHaveAttribute(
      "href",
      "/worlds/world-1/media",
    );
    expect(screen.getByRole("link", { name: "Visual" })).toHaveAttribute(
      "href",
      "/worlds/world-1/visual",
    );
    expect(screen.getByRole("link", { name: "Speech" })).toHaveAttribute(
      "href",
      "/worlds/world-1/speech",
    );
  });
});
