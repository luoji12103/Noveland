import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InvocationLedgerAdmin } from "@/features/admin/invocation-ledger-admin";
import {
  createInvocationTag,
  deleteInvocationTag,
  getInvocation,
  getPromptSnapshot,
  listInvocationTags,
  listInvocations,
  redactInvocation,
} from "@/lib/worlds/invocations";
import type { InvocationRecord, InvocationTag, PromptSnapshot } from "@/lib/worlds/invocations";
import type { InvocationLedgerAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/invocations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/invocations")>(
    "@/lib/worlds/invocations",
  );
  return {
    ...actual,
    createInvocationTag: vi.fn(),
    deleteInvocationTag: vi.fn(),
    getInvocation: vi.fn(),
    getPromptSnapshot: vi.fn(),
    listInvocationTags: vi.fn(),
    listInvocations: vi.fn(),
    redactInvocation: vi.fn(),
  };
});

describe("InvocationLedgerAdmin", () => {
  it("renders ledger records and redacts path, secret, and base64-like evidence", () => {
    render(<InvocationLedgerAdmin worldId="world-1" data={ledgerData} />);

    expect(screen.getByRole("heading", { name: "Invocation ledger overview" })).toBeInTheDocument();
    expect(screen.getByText("text_to_speech - openai_audio - succeeded")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Invocation tags" })).toBeInTheDocument();
    expect(screen.getByText("Prompt snapshot")).toBeInTheDocument();
    expect(screen.getAllByText(/\[redacted\]/).length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText(/media:\/\//)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/var\/noveland/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sk-live-secret/)).not.toBeInTheDocument();
    expect(screen.queryByText(/YmFzZTY0/)).not.toBeInTheDocument();
  });

  it("filters, selects, tags, deletes tags, and redacts invocations through client helpers", async () => {
    vi.mocked(listInvocations).mockResolvedValue([nextInvocation]);
    vi.mocked(listInvocationTags).mockResolvedValue([tag]);
    vi.mocked(getPromptSnapshot).mockResolvedValue(promptSnapshot);
    vi.mocked(getInvocation).mockResolvedValue(nextInvocation);
    vi.mocked(createInvocationTag).mockResolvedValue({ ...tag, id: "tag-2" });
    vi.mocked(deleteInvocationTag).mockResolvedValue(undefined);
    vi.mocked(redactInvocation).mockResolvedValue({ ...nextInvocation, redaction_status: "redacted" });
    render(<InvocationLedgerAdmin worldId="world-1" data={ledgerData} />);

    fireEvent.change(screen.getByPlaceholderText("safe text search"), {
      target: { value: "hello" },
    });
    fireEvent.change(screen.getByPlaceholderText("tag_type:tag_key:tag_value"), {
      target: { value: "audit:phase:v0.4" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply invocation filters" }));

    await waitFor(() => {
      expect(listInvocations).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          contains_text: "hello",
          tag: ["audit:phase:v0.4"],
          include_hidden: true,
          limit: 100,
        }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Selected" }));

    await waitFor(() => {
      expect(getInvocation).toHaveBeenCalledWith("world-1", "invocation-2");
    });

    fireEvent.change(screen.getByPlaceholderText("audit"), {
      target: { value: "review" },
    });
    fireEvent.change(screen.getByPlaceholderText("phase"), {
      target: { value: "scope" },
    });
    fireEvent.change(screen.getByPlaceholderText("v0.4"), {
      target: { value: "phase-6" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create invocation tag" }));

    await waitFor(() => {
      expect(createInvocationTag).toHaveBeenCalledWith(
        "world-1",
        "invocation-2",
        expect.objectContaining({
          tag_type: "review",
          tag_key: "scope",
          tag_value: "phase-6",
        }),
      );
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    await waitFor(() => {
      expect(deleteInvocationTag).toHaveBeenCalledWith("world-1", "invocation-2", "tag-1");
    });

    fireEvent.change(screen.getByPlaceholderText("redaction reason"), {
      target: { value: "safe evidence test" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Redact invocation" }));

    await waitFor(() => {
      expect(redactInvocation).toHaveBeenCalledWith(
        "world-1",
        "invocation-2",
        expect.objectContaining({
          redaction_status: "redacted",
          mode: "clear_raw_payloads",
          reason: "safe evidence test",
        }),
      );
    });
  });

  it("shows an ACL state when world management data is unavailable", () => {
    render(
      <InvocationLedgerAdmin
        worldId="world-1"
        data={{
          ...ledgerData,
          canManageSelectedWorld: false,
          invocations: [],
          selectedInvocation: null,
          tagsByInvocationId: {},
          promptSnapshot: null,
        }}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Invocation ledger access requires world admin access.",
    );
  });
});

const invocation: InvocationRecord = {
  id: "invocation-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  trace_id: "trace-1",
  parent_invocation_id: null,
  invocation_kind: "text_to_speech",
  actor_kind: "world_admin",
  actor_ref: "user:admin",
  agent_id: "agent-1",
  conversation_id: null,
  turn_id: null,
  world_event_id: null,
  media_job_id: "job-1",
  media_asset_id: "asset-1",
  memory_write_job_id: null,
  provider_kind: "openai_audio",
  provider_profile_id: "provider-1",
  model_name: "tts-1",
  model_version: null,
  prompt_template_key: null,
  prompt_template_version: null,
  input_text: "hello world",
  output_text: "audio asset created",
  input_json: { source: "admin" },
  output_json: { storage_uri: "media://hidden-object" },
  request_params_json: { Authorization: "Bearer sk-live-secret", nested: { file_path: "/var/noveland/object" } },
  response_metadata_json: { result: "ok", preview: "YmFzZTY0" },
  usage_json: { total_tokens: 1 },
  latency_ms: 321,
  estimated_cost: "0.01",
  status: "succeeded",
  error_text: null,
  visibility: "world_admin",
  redaction_status: "raw",
  retention_policy: "local_debug",
  contains_sensitive_context: true,
  purge_after: null,
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const nextInvocation: InvocationRecord = {
  ...invocation,
  id: "invocation-2",
  trace_id: "trace-2",
  status: "failed",
  error_text: "provider timeout",
};

const promptSnapshot: PromptSnapshot = {
  id: "snapshot-1",
  invocation_id: "invocation-1",
  template_id: null,
  template_key: "speech-test",
  template_version: 1,
  raw_prompt_text: "hello world",
  raw_messages_json: [{ role: "user", content: "hello world" }],
  raw_request_json: { Authorization: "Bearer sk-live-secret", storage_uri: "media://hidden-object" },
  raw_response_json: { file_path: "/var/noveland/object" },
  raw_output_text: "audio asset created",
  normalized_output_json: { base64: "YmFzZTY0" },
  prompt_context_snapshot_json: {},
  tool_definitions_json: {},
  context_pack_refs_json: {},
  input_asset_refs_json: [],
  prompt_checksum_sha256: "a".repeat(64),
  request_checksum_sha256: "b".repeat(64),
  response_checksum_sha256: "c".repeat(64),
  output_checksum_sha256: "d".repeat(64),
  visibility: "world_admin",
  redaction_status: "raw",
  contains_sensitive_context: true,
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const tag: InvocationTag = {
  id: "tag-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  invocation_id: "invocation-1",
  tag_type: "audit",
  tag_key: "phase",
  tag_value: "v0.4",
  created_at: "2026-05-13T00:00:00.000Z",
};

const ledgerData: InvocationLedgerAdminData = {
  worlds: [],
  selectedWorld: null,
  memberships: [],
  worldlines: [
    {
      id: "worldline-1",
      world_id: "world-1",
      worldline_key: "main",
      name: "Main",
      description: null,
      parent_worldline_id: null,
      forked_from_snapshot_id: null,
      fork_event_sequence: null,
      status: "active",
      created_by_actor_ref: "user:admin",
      metadata: {},
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  invocations: [invocation],
  selectedInvocation: invocation,
  tagsByInvocationId: { "invocation-1": [tag] },
  promptSnapshot,
  canManageSelectedWorld: true,
  isPlatformAdmin: true,
  loadError: null,
};
