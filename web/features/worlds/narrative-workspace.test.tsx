import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/client")>("@/lib/worlds/client");
  return {
    ...actual,
    createNarrativeArtifact: vi.fn(),
    publishNarrativeArtifact: vi.fn(),
    unpublishNarrativeArtifact: vi.fn(),
  };
});

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import { NarrativeWorkspace } from "@/features/worlds/narrative-workspace";
import {
  publishNarrativeArtifact,
  unpublishNarrativeArtifact,
} from "@/lib/worlds/client";
import type { NarrativeWorkspaceData } from "@/lib/worlds/server";

describe("NarrativeWorkspace", () => {
  afterEach(() => {
    vi.clearAllMocks();
    refresh.mockReset();
  });

  it("renders draft and published artifacts with publish controls", async () => {
    vi.mocked(publishNarrativeArtifact).mockResolvedValue(publication);
    vi.mocked(unpublishNarrativeArtifact).mockResolvedValue({
      ...publication,
      status: "unpublished",
      reader_visible: false,
    });

    render(<NarrativeWorkspace worldId="world-1" data={workspaceData} />);

    expect(screen.getByRole("heading", { name: "Draft artifacts" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Published artifacts" })).toBeVisible();
    expect(screen.getByText(/Draft chapter/)).toBeVisible();
    expect(screen.getByText(/Published chapter/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => {
      expect(publishNarrativeArtifact).toHaveBeenCalledWith("world-1", "artifact-draft", {
        reader_visible: true,
        metadata: { channel: "reader" },
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Unpublish" }));
    await waitFor(() => {
      expect(unpublishNarrativeArtifact).toHaveBeenCalledWith("world-1", "artifact-published", {
        metadata: { reason: "operator_unpublished" },
      });
    });
  });
});

const publication = {
  id: "publication-1",
  world_id: "world-1",
  artifact_id: "artifact-published",
  source_draft_id: "artifact-published",
  status: "published" as const,
  reader_visible: true,
  metadata: { channel: "reader" },
  published_at: "2026-04-21T00:03:00.000Z",
  unpublished_at: null,
  published_by_user_id: "user-1",
  created_at: "2026-04-21T00:03:00.000Z",
  updated_at: "2026-04-21T00:03:00.000Z",
};

const workspaceData: NarrativeWorkspaceData = {
  worlds: [],
  selectedWorld: null,
  agents: [],
  narrativeArtifacts: [
    {
      id: "artifact-draft",
      world_id: "world-1",
      agent_id: null,
      source_run_id: null,
      source_conversation_id: null,
      title: "Draft chapter",
      content: "Draft body",
      artifact_kind: "chapter_draft",
      metadata: {},
      created_at: "2026-04-21T00:02:00.000Z",
      publication: null,
    },
    {
      id: "artifact-published",
      world_id: "world-1",
      agent_id: null,
      source_run_id: null,
      source_conversation_id: null,
      title: "Published chapter",
      content: "Published body",
      artifact_kind: "chapter_draft",
      metadata: {},
      created_at: "2026-04-21T00:03:00.000Z",
      publication,
    },
  ],
  canManageSelectedWorld: true,
  loadError: null,
};
