import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/worlds/client", () => ({
  createAgent: vi.fn(),
  deactivateAgent: vi.fn(),
}));

const refresh = vi.fn();
const assign = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import { AgentList } from "@/features/agents/agent-list";
import { createAgent } from "@/lib/worlds/client";
import type { AgentWorkspaceData } from "@/lib/worlds/server";

describe("AgentList", () => {
  afterEach(() => {
    vi.clearAllMocks();
    refresh.mockReset();
    assign.mockReset();
  });

  it("shows preset preview and sends preset_id when creating an agent", async () => {
    vi.mocked(createAgent).mockResolvedValue({
      ...workspaceData.agents[0],
      id: RESERVED_AGENT_ID,
      agent_key: "scribe",
      display_name: "Scribe",
      source_preset_id: "preset-1",
      source_preset_version: 1,
    });
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { assign },
    });

    render(<AgentList worldId={RESERVED_WORLD_ID} data={workspaceData} />);

    fireEvent.change(screen.getAllByRole("combobox")[0], {
      target: { value: "preset-1" },
    });

    expect(screen.getByText("Preset preview")).toBeInTheDocument();
    expect(screen.getByText("Provider key: openai-local")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("agent-key"), {
      target: { value: "scribe" },
    });
    fireEvent.change(screen.getByPlaceholderText("Display name"), {
      target: { value: "Scribe" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create agent" }));

    await waitFor(() => {
      expect(createAgent).toHaveBeenCalledWith(RESERVED_WORLD_ID, expect.objectContaining({
        agent_key: "scribe",
        display_name: "Scribe",
        preset_id: "preset-1",
      }));
    });
    expect(assign).toHaveBeenCalledWith(
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/agents/${encodeURIComponent(RESERVED_AGENT_ID)}`,
    );
  });

  it("encodes local builder links for reserved route characters", () => {
    render(
      <AgentList
        worldId={RESERVED_WORLD_ID}
        data={{
          ...workspaceData,
          agents: [{ ...workspaceData.agents[0], id: RESERVED_AGENT_ID }],
        }}
      />,
    );

    expect(screen.getByRole("link", { name: "Open builder" })).toHaveAttribute(
      "href",
      `/worlds/${encodeURIComponent(RESERVED_WORLD_ID)}/agents/${encodeURIComponent(RESERVED_AGENT_ID)}`,
    );
  });

  it("renders source preset labels and hides write controls for read-only users", () => {
    render(
      <AgentList
        worldId="world-1"
        data={{
          ...workspaceData,
          canManageSelectedWorld: false,
        }}
      />,
    );

    expect(screen.getByText("Read-only agent catalog access.")).toBeInTheDocument();
    expect(screen.getByText("Source preset: Storyteller (storyteller v1)")).toBeInTheDocument();
    expect(screen.getByText("Source preset version: 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create agent" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Disable agent" })).not.toBeInTheDocument();
  });
});

const RESERVED_WORLD_ID = "world/admin?scope=true#frag";
const RESERVED_AGENT_ID = "agent/detail?mode=edit#frag";

const workspaceData: AgentWorkspaceData = {
  worlds: [
    {
      id: "world-1",
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
    },
  ],
  selectedWorld: {
    id: "world-1",
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
  },
  scenes: [
    {
      id: "scene-1",
      world_id: "world-1",
      scene_key: "home",
      name: "Home",
      description: null,
      region_key: null,
      location_tags: [],
      opening_rules: {},
      is_active: true,
    },
  ],
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: "scene-1",
      source_preset_id: "preset-1",
      source_preset_version: 1,
      agent_key: "guide",
      display_name: "Guide",
      kind: "role_agent",
      provider_profile_id: "profile-1",
      config: { provider_profile_id: "profile-1" },
      is_enabled: true,
    },
  ],
  providerProfiles: [
    {
      id: "profile-1",
      profile_key: "openai-local",
      name: "OpenAI Local",
      provider_type: "openai_compatible",
      plugin_identifier: "builtin.openai_compatible",
      plugin_config: {},
      base_url: "https://api.example.test/v1",
      model_name: "gpt-test",
      capabilities: {},
      api_key_ref: "openai-local",
      timeout_seconds: 20,
      retry_attempts: 1,
      rate_limit_per_minute: null,
      last_tested_at: null,
      last_test_status: null,
      last_test_error: null,
      is_enabled: true,
    },
  ],
  agentPresets: [
    {
      id: "preset-1",
      preset_key: "storyteller",
      name: "Storyteller",
      description: "Long-form narrative preset.",
      default_kind: "narrative_agent",
      default_provider_profile_key: "openai-local",
      persona_text: "Writes well.",
      behavior_policy: {},
      calendar_blueprint: [],
      advanced_config: {},
      version: 1,
      is_active: true,
      created_at: "2026-04-22T00:00:00.000Z",
      updated_at: "2026-04-22T00:00:00.000Z",
    },
  ],
  personaPolicyPlugins: [],
  canManageSelectedWorld: true,
  isPlatformAdmin: true,
  loadError: null,
};
