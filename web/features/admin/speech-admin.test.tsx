import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SpeechAdmin } from "@/features/admin/speech-admin";
import {
  createAgentVoiceBinding,
  createStyleMapping,
  createVoiceProfile,
  listAgentVoiceBindings,
  listTranscripts,
  listVoiceProfiles,
  runSTT,
  runTTS,
  updateStyleMapping,
  updateVoiceProfile,
} from "@/lib/worlds/speech";
import type { STTResult, TTSResult } from "@/lib/worlds/speech";
import type { SpeechAdminData } from "@/lib/worlds/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/worlds/speech", async () => {
  const actual = await vi.importActual<typeof import("@/lib/worlds/speech")>("@/lib/worlds/speech");
  return {
    ...actual,
    createAgentVoiceBinding: vi.fn(),
    createStyleMapping: vi.fn(),
    createVoiceProfile: vi.fn(),
    deleteAgentVoiceBinding: vi.fn(),
    deleteStyleMapping: vi.fn(),
    deleteVoiceProfile: vi.fn(),
    listAgentVoiceBindings: vi.fn(),
    listTranscripts: vi.fn(),
    listVoiceProfiles: vi.fn(),
    runSTT: vi.fn(),
    runTTS: vi.fn(),
    updateStyleMapping: vi.fn(),
    updateVoiceProfile: vi.fn(),
  };
});

describe("SpeechAdmin", () => {
  it("renders speech records without audio paths, secrets, or raw media payloads", () => {
    render(<SpeechAdmin worldId="world-1" data={speechData} />);

    expect(screen.getByRole("heading", { name: "Speech overview" })).toBeInTheDocument();
    expect(screen.getByText("Akari voice")).toBeInTheDocument();
    expect(screen.getByText("hello transcript")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Agent voice bindings" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Speech style mappings" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Speech transcripts" })).toBeInTheDocument();
    expect(screen.queryByText(/media:\/\//)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/var\/noveland/)).not.toBeInTheDocument();
    expect(screen.queryByText(/base64/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sk-live-secret/)).not.toBeInTheDocument();
  });

  it("loads worldline speech records and manages profiles, bindings, and style mappings", async () => {
    vi.mocked(listVoiceProfiles).mockResolvedValue([speechData.voiceProfiles[0]]);
    vi.mocked(listAgentVoiceBindings).mockResolvedValue([speechData.bindingsByAgentId["agent-1"][0]]);
    vi.mocked(listTranscripts).mockResolvedValue([speechData.transcripts[0]]);
    vi.mocked(createVoiceProfile).mockResolvedValue(speechData.voiceProfiles[0]);
    vi.mocked(updateVoiceProfile).mockResolvedValue(speechData.voiceProfiles[0]);
    vi.mocked(createAgentVoiceBinding).mockResolvedValue(speechData.bindingsByAgentId["agent-1"][0]);
    vi.mocked(createStyleMapping).mockResolvedValue(speechData.styleMappings[0]);
    vi.mocked(updateStyleMapping).mockResolvedValue(speechData.styleMappings[0]);
    render(<SpeechAdmin worldId="world-1" data={speechData} />);

    fireEvent.click(screen.getByRole("button", { name: "Load speech records" }));

    await waitFor(() => {
      expect(listVoiceProfiles).toHaveBeenCalledWith("world-1", { worldline_id: "worldline-1" });
    });

    fireEvent.change(screen.getByPlaceholderText("profile key"), {
      target: { value: "akari_alt" },
    });
    fireEvent.change(screen.getByPlaceholderText("Display name"), {
      target: { value: "Akari alternate" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create voice profile" }));

    await waitFor(() => {
      expect(createVoiceProfile).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          profile_key: "akari_alt",
          display_name: "Akari alternate",
        }),
      );
    });

    fireEvent.change(screen.getByDisplayValue("Akari voice"), {
      target: { value: "Akari saved" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save voice profile" }));

    await waitFor(() => {
      expect(updateVoiceProfile).toHaveBeenCalledWith(
        "world-1",
        "voice-1",
        expect.objectContaining({ display_name: "Akari saved" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Bind voice profile" }));

    await waitFor(() => {
      expect(createAgentVoiceBinding).toHaveBeenCalledWith(
        "world-1",
        "agent-1",
        expect.objectContaining({ voice_profile_id: "voice-1", worldline_id: "worldline-1" }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("mapping key"), {
      target: { value: "openai-sad" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create style mapping" }));

    await waitFor(() => {
      expect(createStyleMapping).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({ mapping_key: "openai-sad" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Save style" }));

    await waitFor(() => {
      expect(updateStyleMapping).toHaveBeenCalledWith(
        "world-1",
        "mapping-1",
        expect.objectContaining({ style_json: expect.objectContaining({ voice: "alloy" }) }),
      );
    });
  });

  it("runs explicit TTS/STT tests and shows safe result references", async () => {
    vi.mocked(runTTS).mockResolvedValue(ttsResult);
    vi.mocked(runSTT).mockResolvedValue(sttResult);
    render(<SpeechAdmin worldId="world-1" data={speechData} />);

    fireEvent.click(screen.getByRole("button", { name: "Run TTS test" }));

    await waitFor(() => {
      expect(runTTS).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          provider_id: "provider-tts",
        }),
      );
    });
    expect(await screen.findByText("Output asset")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "object-1" })).toHaveAttribute(
      "href",
      "/api/worlds/world-1/media/objects/object-1/download",
    );

    fireEvent.click(screen.getByRole("button", { name: "Run STT test" }));

    await waitFor(() => {
      expect(runSTT).toHaveBeenCalledWith(
        "world-1",
        expect.objectContaining({
          worldline_id: "worldline-1",
          provider_id: "provider-stt",
          source_asset_id: "audio-1",
        }),
      );
    });
    expect(await screen.findByText("Memory write")).toBeInTheDocument();
    expect(screen.getByText("not automatic")).toBeInTheDocument();
  });

  it("shows an ACL state when world management data is unavailable", () => {
    render(
      <SpeechAdmin
        worldId="world-1"
        data={{
          ...speechData,
          canManageSelectedWorld: false,
          voiceProfiles: [],
          bindingsByAgentId: {},
          styleMappings: [],
          transcripts: [],
        }}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Speech administration requires world admin access.",
    );
  });
});

const audioAsset = {
  id: "audio-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  asset_kind: "audio",
  asset_role: "speech_audio",
  source_kind: "provider_generated",
  status: "available",
  visibility: "world_admin",
  mime_type: "audio/wav",
  file_ext: "wav",
  size_bytes: 12,
  checksum_sha256: "a".repeat(64),
  width: null,
  height: null,
  duration_ms: 1200,
  sample_rate_hz: 24000,
  audio_channels: 1,
  has_alpha: null,
  color_mode: null,
  provider_kind: "text_to_speech",
  source_job_id: "job-1",
  source_event_id: null,
  source_invocation_id: "invocation-1",
  title: "Akari sample",
  description: null,
  created_by_actor_ref: "user:admin",
  metadata: { storage_uri: "media://hidden-audio", token: "sk-live-secret" },
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
} as const;

const speechData: SpeechAdminData = {
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
  selectedWorldlineId: "worldline-1",
  agents: [
    {
      id: "agent-1",
      world_id: "world-1",
      home_scene_id: null,
      source_preset_id: null,
      source_preset_version: null,
      agent_key: "akari",
      display_name: "Akari",
      kind: "role_agent",
      provider_profile_id: null,
      config: {},
      is_enabled: true,
    },
  ],
  providers: [
    {
      id: "provider-tts",
      world_id: "world-1",
      scope_kind: "world",
      scope_key: "world-1",
      provider_kind: "text_to_speech",
      adapter_kind: "fake",
      provider_key: "fake-tts",
      display_name: "Fake TTS",
      base_url: null,
      auth_ref: "env:OPENAI_API_KEY",
      auth_ref_configured: true,
      config_json: {},
      default_params_json: {},
      status: "active",
      visibility: "world_admin",
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
    {
      id: "provider-stt",
      world_id: "world-1",
      scope_kind: "world",
      scope_key: "world-1",
      provider_kind: "speech_to_text",
      adapter_kind: "fake",
      provider_key: "fake-stt",
      display_name: "Fake STT",
      base_url: null,
      auth_ref: null,
      auth_ref_configured: false,
      config_json: {},
      default_params_json: {},
      status: "active",
      visibility: "world_admin",
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  audioAssets: [audioAsset],
  voiceProfiles: [
    {
      id: "voice-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      profile_key: "akari",
      display_name: "Akari voice",
      description: null,
      status: "active",
      visibility: "world_admin",
      owner_kind: "agent",
      owner_agent_id: "agent-1",
      provider_integration_id: "provider-tts",
      provider_voice_id: "voice-provider-id",
      default_language: "ja",
      supported_languages: ["ja"],
      voice_kind: "preset",
      reference_asset_id: "audio-1",
      consent_status: "not_required",
      usage_policy_json: { path: "/var/noveland/voice" },
      metadata_json: { base64_sample: "base64-secret" },
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  bindingsByAgentId: {
    "agent-1": [
      {
        id: "binding-1",
        world_id: "world-1",
        worldline_id: "worldline-1",
        agent_id: "agent-1",
        voice_profile_id: "voice-1",
        binding_role: "default",
        priority: 100,
        is_default: true,
        style_overrides_json: { emotion: "calm" },
        created_at: "2026-05-13T00:00:00.000Z",
        updated_at: "2026-05-13T00:00:00.000Z",
      },
    ],
  },
  styleMappings: [
    {
      id: "mapping-1",
      world_id: "world-1",
      mapping_key: "openai-happy",
      provider_kind: "openai",
      emotion_key: "happy",
      style_json: { voice: "alloy" },
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  transcripts: [
    {
      id: "transcript-1",
      world_id: "world-1",
      worldline_id: "worldline-1",
      source_asset_id: "audio-1",
      media_job_id: "job-2",
      model_invocation_id: "invocation-2",
      conversation_id: null,
      turn_id: null,
      speaker_actor_ref: "agent:akari",
      language: "ja",
      transcript_text: "hello transcript",
      segments_json: null,
      confidence_json: null,
      status: "available",
      visibility: "world_admin",
      created_at: "2026-05-13T00:00:00.000Z",
      updated_at: "2026-05-13T00:00:00.000Z",
    },
  ],
  canManageSelectedWorld: true,
  isPlatformAdmin: false,
  loadError: null,
};

const mediaJob = {
  id: "job-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  conversation_id: null,
  turn_id: null,
  agent_id: "agent-1",
  job_kind: "speech_generation",
  provider_kind: "text_to_speech",
  priority: 100,
  cancel_policy: null,
  deadline_hint: null,
  dedupe_key: null,
  invalidation_key: null,
  source_event_id: null,
  source_invocation_id: "invocation-1",
  provider_config_json: {},
  request_json: {},
  status: "succeeded",
  result_json: {},
  error_text: null,
  created_by_actor_ref: "user:admin",
  started_at: null,
  finished_at: "2026-05-13T00:00:00.000Z",
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
} as const;

const mediaObject = {
  id: "object-1",
  asset_id: "audio-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  object_role: "primary",
  filename: "tts.wav",
  mime_type: "audio/wav",
  size_bytes: 12,
  checksum_sha256: "a".repeat(64),
  width: null,
  height: null,
  duration_ms: 1200,
  sample_rate_hz: 24000,
  audio_channels: 1,
  frame_rate: null,
  metadata: {},
  created_at: "2026-05-13T00:00:00.000Z",
} as const;

const ttsResult: TTSResult = {
  media_job: mediaJob,
  output_asset: audioAsset,
  output_objects: [mediaObject],
  model_invocation: {
    id: "invocation-1",
    status: "succeeded",
    latency_ms: 25,
    request_params_json: {},
    response_metadata_json: {},
  },
  model_invocation_id: "invocation-1",
};

const sttResult: STTResult = {
  media_job: { ...mediaJob, id: "job-2", job_kind: "speech_transcription", provider_kind: "speech_to_text" },
  transcript: speechData.transcripts[0],
  model_invocation: {
    id: "invocation-2",
    status: "succeeded",
    latency_ms: 30,
    request_params_json: {},
    response_metadata_json: {},
  },
  model_invocation_id: "invocation-2",
};
