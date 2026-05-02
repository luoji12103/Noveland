import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MemoryBackendAdmin } from "@/features/admin/memory-backend-admin";
import type { MemoryBackendAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/client", () => ({
  createMemoryBackendProfile: vi.fn(),
  deleteMemoryBackendProfile: vi.fn(),
  retryMemoryWriteJob: vi.fn(),
  runMemoryBackendProfileEvalSmoke: vi.fn(),
  updateMemoryBackendProfile: vi.fn(),
}));

describe("MemoryBackendAdmin", () => {
  it("renders backfill dry-run counts and retry metadata", () => {
    render(<MemoryBackendAdmin data={memoryData} />);

    expect(screen.getByText("Memory backfill dry-run")).toBeInTheDocument();
    expect(screen.getByText("Planning only. This dry-run does not enqueue memory write jobs.")).toBeInTheDocument();
    expect(screen.getByText("conversation_turn")).toBeInTheDocument();
    expect(screen.getByText("Retry: retryable / age 300s / last log failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry job" })).toBeEnabled();
  });
});

const memoryData: MemoryBackendAdminData = {
  profiles: [
    {
      id: "memory-profile-1",
      profile_key: "primary-mem0",
      name: "Primary Mem0",
      backend_kind: "mem0_oss",
      vector_store_config: {},
      llm_config: {},
      embedder_config: {},
      reranker_config: {},
      secret_refs: {},
      is_enabled: true,
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  profileHealth: {
    "memory-profile-1": { backend: "mem0_oss", status: "ok", details: {} },
  },
  profileLogs: {
    "memory-profile-1": { write_logs: [], retrieval_logs: [] },
  },
  profileJobs: {
    "memory-profile-1": {
      jobs: [
        {
          id: "job-1",
          world_id: "world-1",
          agent_id: "agent-1",
          backend_profile_id: "memory-profile-1",
          backend_profile_key: "primary-mem0",
          backend_profile_name: "Primary Mem0",
          backend_kind: "mem0_oss",
          source_kind: "conversation_turn",
          source_id: "turn-1",
          dedupe_key: "conversation-turn:turn-1",
          status: "failed",
          attempt_count: 2,
          next_attempt_at: "2026-04-17T00:10:00.000Z",
          last_error: "backend timeout",
          processed_at: null,
          is_retryable: true,
          terminal_reason: null,
          last_log_success: false,
          age_seconds: 300,
          created_at: "2026-04-17T00:00:00.000Z",
          updated_at: "2026-04-17T00:05:00.000Z",
        },
      ],
    },
  },
  backfillDryRun: {
    candidate_count: 1,
    skipped_existing_count: 0,
    skipped_no_profile_count: 0,
    skipped_disabled_profile_count: 0,
    source_summaries: [
      {
        source_kind: "conversation_turn",
        candidate_count: 1,
        skipped_existing_count: 0,
        skipped_no_profile_count: 0,
        skipped_disabled_profile_count: 0,
      },
    ],
    world_summaries: [],
  },
  loadError: null,
};
