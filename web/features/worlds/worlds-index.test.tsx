import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", () => ({
  createWorld: vi.fn(),
}));

const assign = vi.fn();

import { WorldsIndex } from "@/features/worlds/worlds-index";
import { createWorld } from "@/lib/worlds/client";
import type { World } from "@/lib/worlds/types";

describe("WorldsIndex", () => {
  afterEach(() => {
    vi.clearAllMocks();
    assign.mockReset();
  });

  it("encodes workspace links and create redirects for reserved route characters", async () => {
    vi.mocked(createWorld).mockResolvedValue(worldWithId(CREATED_WORLD_ID));
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { assign },
    });

    render(<WorldsIndex worlds={[worldWithId(RESERVED_WORLD_ID)]} canCreateWorld />);

    expect(screen.getByRole("link", { name: "Open workspace" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}`,
    );

    fireEvent.change(screen.getByPlaceholderText("world-slug"), {
      target: { value: "new-world" },
    });
    fireEvent.change(screen.getByPlaceholderText("World name"), {
      target: { value: "New World" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create world" }));

    await waitFor(() => {
      expect(createWorld).toHaveBeenCalledWith(
        expect.objectContaining({ slug: "new-world", name: "New World" }),
      );
    });
    expect(assign).toHaveBeenCalledWith(`/worlds/${encodeURIComponent(CREATED_WORLD_ID)}`);
  });
});

const RESERVED_WORLD_ID = "world/index?scope=true#frag";
const CREATED_WORLD_ID = "world/created?scope=true#frag";

function worldWithId(id: string): World {
  return {
    id,
    owner_user_id: "user-1",
    slug: "first-world",
    name: "First World",
    description: null,
    rules_config: {},
    memory_backend_profile_id: null,
    memory_plugin_identifier: "builtin.local_pgvector_memory",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.default_world_rules",
    world_rules_plugin_config: {},
    is_active: true,
  };
}
