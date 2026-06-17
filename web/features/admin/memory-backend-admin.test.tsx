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
    expect(screen.queryByText(/sk-live-secret/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/sk-live-secret/)).not.toBeInTheDocument();
    expect(screen.queryByText(/clientSecret/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/clientSecret/)).not.toBeInTheDocument();
    expect(screen.queryByText(/bearerToken/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/bearerToken/)).not.toBeInTheDocument();
    expect(screen.queryByText(/rawPrompt/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/rawPrompt/)).not.toBeInTheDocument();
    expect(screen.queryByText(/storageUri/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/storageUri/)).not.toBeInTheDocument();
    expect(screen.queryByText(/promptSnapshotId/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/promptSnapshotId/)).not.toBeInTheDocument();
    expect(screen.queryByText(/hidden memory prompt/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/hidden memory prompt/)).not.toBeInTheDocument();
    expect(screen.queryByText(/opaque-memory-storage/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/opaque-memory-storage/)).not.toBeInTheDocument();
    expect(screen.getByDisplayValue(/collection_name/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/env:MEMORY_OPENAI_API_KEY/)).toBeInTheDocument();
    expect(screen.getByText(/safe_metric/)).toBeInTheDocument();
  });
});

const memoryData: MemoryBackendAdminData = {
  profiles: [
    {
      id: "memory-profile-1",
      profile_key: "primary-mem0",
      name: "Primary Mem0",
      backend_kind: "mem0_oss",
      vector_store_config: {
        collection_name: "agent_memory",
        storageUri: "opaque-memory-storage",
        nested: { filePath: "/var/noveland/memory" },
      },
      llm_config: {
        model: "safe-model",
        clientSecret: "sk-live-secret",
        rawPrompt: "hidden memory prompt",
      },
      embedder_config: { dimensions: 1536, bearerToken: "Bearer sk-live-secret" },
      reranker_config: { promptSnapshotId: "snapshot-hidden" },
      secret_refs: {
        openai_api_key: "env:MEMORY_OPENAI_API_KEY",
        dirty_ref: "sk-live-secret",
      },
      is_enabled: true,
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
  profileHealth: {
    "memory-profile-1": {
      backend: "mem0_oss",
      status: "ok",
      details: { safe_metric: "ok", clientSecret: "sk-live-secret" },
    },
  },
  profileLogs: {
    "memory-profile-1": {
      write_logs: [
        {
          id: "write-log-1",
          job_id: "job-1",
          backend: "mem0_oss",
          success: false,
          latency_ms: 5,
          request_summary: { rawPrompt: "hidden memory prompt", safe_request: "ok" },
          response_summary: { storageUri: "opaque-memory-storage" },
          correlation_ids: { promptSnapshotId: "snapshot-hidden" },
          occurred_at: "2026-04-17T00:05:00.000Z",
        },
      ],
      retrieval_logs: [
        {
          id: "retrieval-log-1",
          world_id: "world-1",
          worldline_id: "worldline-1",
          agent_id: "agent-1",
          backend_profile_id: "memory-profile-1",
          backend: "mem0_oss",
          query_text: "safe query",
          hit_count: 1,
          selected_item_ids: ["item-1"],
          latency_ms: 4,
          context_item_count: 1,
          occurred_at: "2026-04-17T00:06:00.000Z",
        },
      ],
    },
  },
  profileJobs: {
    "memory-profile-1": {
      jobs: [
        {
          id: "job-1",
          world_id: "world-1",
          worldline_id: "worldline-1",
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
