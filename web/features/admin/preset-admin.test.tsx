import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", () => ({
  createAgentPreset: vi.fn(),
  getAgentPresetUpdatePreview: vi.fn(),
  updateAgentPreset: vi.fn(),
  deactivateAgentPreset: vi.fn(),
}));

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import { PresetAdmin } from "@/features/admin/preset-admin";
import {
  createAgentPreset,
  deactivateAgentPreset,
  getAgentPresetUpdatePreview,
  updateAgentPreset,
} from "@/lib/worlds/client";
import type { AgentPreset } from "@/lib/worlds/types";

describe("PresetAdmin", () => {
  afterEach(() => {
    vi.clearAllMocks();
    refresh.mockReset();
  });


  it("redacts sensitive preset JSON and submit payloads", async () => {
    const dirtyPresets: AgentPreset[] = [
      {
        ...presets[0],
        behavior_policy: {
          tone: "clean",
          clientSecret: "sk-preset-secret",
          nested: { storageUri: "media://preset-secret" },
        },
        calendar_blueprint: [
          {
            title: "Office hours",
            description: null,
            starts_at: "2030-01-01T09:00:00.000Z",
            ends_at: null,
            recurrence_rule: null,
            metadata: { room: "club", rawPrompt: "system prompt", filePath: "/tmp/preset-calendar.json" },
          },
        ],
        advanced_config: {
          safeMode: true,
          bearerToken: "Bearer preset-token",
          promptSnapshotId: "snapshot-preset",
        },
      },
    ];
    vi.mocked(createAgentPreset).mockResolvedValue(dirtyPresets[0]);
    vi.mocked(updateAgentPreset).mockResolvedValue(dirtyPresets[0]);

    render(<PresetAdmin presets={dirtyPresets} loadError={null} />);

    expect(screen.getByDisplayValue(/tone/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/Office hours/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/safeMode/)).toBeInTheDocument();
    expect(
      screen.queryAllByDisplayValue(
        /clientSecret|sk-preset-secret|storageUri|media:\/\/preset-secret|rawPrompt|filePath|\/tmp\/preset-calendar|bearerToken|Bearer preset-token|promptSnapshotId|snapshot-preset/i,
      ),
    ).toHaveLength(0);

    const createForm = screen.getAllByRole("button", { name: "Create preset" })[0].closest("form") as HTMLFormElement;
    setFormValue(createForm, "preset_key", "safe-preset");
    setFormValue(createForm, "name", "Safe preset");
    setFormValue(createForm, "persona_text", "Safe persona");
    setFormValue(createForm, "behavior_policy", JSON.stringify({ tone: "create", clientSecret: "sk-create" }));
    setFormValue(
      createForm,
      "calendar_blueprint",
      JSON.stringify([
        {
          title: "Create office hours",
          description: null,
          starts_at: "2030-01-01T10:00:00.000Z",
          ends_at: null,
          recurrence_rule: null,
          metadata: { room: "library", storageUri: "media://create-secret" },
        },
      ]),
    );
    setFormValue(createForm, "advanced_config", JSON.stringify({ safeMode: true, rawOutput: "model output" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Create preset" })[0]);

    await waitFor(() => {
      expect(createAgentPreset).toHaveBeenCalledWith(
        expect.objectContaining({
          behavior_policy: { tone: "create" },
          calendar_blueprint: [
            expect.objectContaining({ title: "Create office hours", metadata: { room: "library" } }),
          ],
          advanced_config: { safeMode: true },
        }),
      );
    });
    expect(JSON.stringify(vi.mocked(createAgentPreset).mock.calls[0][0])).not.toMatch(
      /clientSecret|sk-create|storageUri|media:\/\/create-secret|rawOutput/i,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save preset" }));

    await waitFor(() => {
      expect(updateAgentPreset).toHaveBeenCalledWith(
        "preset-1",
        expect.objectContaining({
          behavior_policy: { tone: "clean", nested: {} },
          calendar_blueprint: [expect.objectContaining({ title: "Office hours", metadata: { room: "club" } })],
          advanced_config: { safeMode: true },
        }),
      );
    });
    expect(JSON.stringify(vi.mocked(updateAgentPreset).mock.calls[0][1])).not.toMatch(
      /clientSecret|sk-preset-secret|storageUri|media:\/\/preset-secret|rawPrompt|filePath|\/tmp\/preset-calendar|bearerToken|Bearer preset-token|promptSnapshotId|snapshot-preset/i,
    );
  });

  it("creates and updates presets", async () => {
    vi.mocked(createAgentPreset).mockResolvedValue(presets[0]);
    vi.mocked(updateAgentPreset).mockResolvedValue(presets[0]);

    render(<PresetAdmin presets={presets} loadError={null} />);

    fireEvent.change(screen.getByPlaceholderText("preset-key"), {
      target: { value: "scout" },
    });
    fireEvent.change(screen.getByPlaceholderText("Preset name"), {
      target: { value: "Scout" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Create preset" })[0]);

    await waitFor(() => {
      expect(createAgentPreset).toHaveBeenCalledWith(
        expect.objectContaining({
          preset_key: "scout",
          name: "Scout",
        }),
      );
    });

    fireEvent.change(screen.getAllByDisplayValue("storyteller")[0], {
      target: { value: "storyteller-v2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save preset" }));

    await waitFor(() => {
      expect(updateAgentPreset).toHaveBeenCalledWith(
        "preset-1",
        expect.objectContaining({
          preset_key: "storyteller-v2",
        }),
      );
    });
    expect(refresh).toHaveBeenCalled();
  });

  it("disables presets", async () => {
    vi.mocked(deactivateAgentPreset).mockResolvedValue(undefined);

    render(<PresetAdmin presets={presets} loadError={null} />);
    fireEvent.click(screen.getByRole("button", { name: "Disable preset" }));

    await waitFor(() => {
      expect(deactivateAgentPreset).toHaveBeenCalledWith("preset-1");
    });
  });

  it("loads preset update previews", async () => {
    vi.mocked(getAgentPresetUpdatePreview).mockResolvedValue({
      preset_id: "preset-1",
      preset_key: "storyteller",
      current_version: 2,
      stale_agent_count: 1,
      current_agent_count: 0,
      unversioned_agent_count: 1,
      agents: [
        {
          agent_id: "agent-1",
          world_id: "world-1",
          agent_key: "guide",
          display_name: "Guide",
          source_preset_version: 1,
          status: "stale",
          changed_fields: ["config.style"],
        },
      ],
    });

    render(<PresetAdmin presets={presets} loadError={null} />);
    fireEvent.click(screen.getByRole("button", { name: "Preview updates" }));

    await waitFor(() => {
      expect(getAgentPresetUpdatePreview).toHaveBeenCalledWith("preset-1");
    });
    expect(screen.getByRole("heading", { name: "Preset update preview" })).toBeVisible();
    expect(screen.getByText(/1 stale/)).toBeVisible();
    expect(screen.getByText("Changed fields: config.style")).toBeVisible();
  });
});


function setFormValue(form: HTMLFormElement, name: string, value: string) {
  const field = form.elements.namedItem(name) as HTMLInputElement | HTMLTextAreaElement | null;
  if (field === null) {
    throw new Error(`Missing form field: ${name}`);
  }
  fireEvent.change(field, { target: { value } });
}

const presets: AgentPreset[] = [
  {
    id: "preset-1",
    preset_key: "storyteller",
    name: "Storyteller",
    description: "Narrative preset",
    default_kind: "narrative_agent",
    default_provider_profile_key: "openai-local",
    persona_text: "Writes clearly.",
    behavior_policy: { tone: "clean" },
    calendar_blueprint: [],
    advanced_config: {},
    version: 1,
    is_active: true,
    created_at: "2026-04-22T00:00:00.000Z",
    updated_at: "2026-04-22T00:00:00.000Z",
  },
];
