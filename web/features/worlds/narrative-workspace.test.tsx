import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { subscribeToEventStream as subscribeToEventStreamFn } from "@/lib/realtime";
import type { WorldStreamPayload } from "@/lib/worlds/types";

const { subscribeToEventStream } = vi.hoisted(() => ({
  subscribeToEventStream: vi.fn<typeof subscribeToEventStreamFn>(() => () => {}),
}));

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

vi.mock("@/lib/realtime", async () => {
  const actual = await vi.importActual<typeof import("@/lib/realtime")>("@/lib/realtime");
  return {
    ...actual,
    subscribeToEventStream,
  };
});

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
    expect(screen.getByText("Publication gate: warning (1 issue)")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => {
      expect(publishNarrativeArtifact).toHaveBeenCalledWith("world-1", "artifact-draft", {
        reader_visible: true,
        metadata: { channel: "reader" },
        override_style_warning: true,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Unpublish" }));
    await waitFor(() => {
      expect(unpublishNarrativeArtifact).toHaveBeenCalledWith("world-1", "artifact-published", {
        metadata: { reason: "operator_unpublished" },
      });
    });
  });

  it("merges narrative stream updates", async () => {
    subscribeToEventStream.mockImplementation(
      ((_, handler) => {
        handler({
          cursor: "cursor-streamed",
          event_type: "world.delta",
          occurred_at: "2026-04-21T00:04:00.000Z",
          world_id: "world-1",
          conversation_id: null,
          payload: {
            diagnostics: [],
            agent_runs: [],
            narrative_artifacts: [
              {
                ...workspaceData.narrativeArtifacts[0],
                id: "artifact-streamed",
                title: "Streamed draft",
              },
            ],
            conversations: [],
          },
        });
        return () => {};
      }) satisfies typeof subscribeToEventStreamFn<WorldStreamPayload>,
    );

    render(<NarrativeWorkspace worldId="world-1" data={workspaceData} />);

    expect(screen.getByText(/Streamed draft/)).toBeVisible();
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
  publication_gate: {
    review_id: "review-1",
    status: "warning",
    override_style_warning: true,
    issue_count: 1,
  },
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
