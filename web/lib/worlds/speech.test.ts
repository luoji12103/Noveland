import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createAgentVoiceBinding,
  createStyleMapping,
  createVoiceProfile,
  deleteAgentVoiceBinding,
  deleteStyleMapping,
  deleteVoiceProfile,
  listAgentVoiceBindings,
  listStyleMappings,
  listTranscripts,
  listVoiceProfiles,
  runSTT,
  runTTS,
  updateStyleMapping,
  updateVoiceProfile,
} from "@/lib/worlds/speech";

describe("speech admin client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("lists speech records through world proxy paths", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse([])));
    vi.stubGlobal("fetch", fetchMock);

    await listVoiceProfiles("world-1", { worldline_id: "worldline-1" });
    await listAgentVoiceBindings("world-1", "agent-1", { worldline_id: "worldline-1" });
    await listStyleMappings("world-1", { provider_kind: "openai", emotion_key: "happy" });
    await listTranscripts("world-1", { source_asset_id: "audio-1" });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/speech/voice-profiles?worldline_id=worldline-1",
      "/api/worlds/world-1/agents/agent-1/voice-profiles?worldline_id=worldline-1",
      "/api/worlds/world-1/speech/style-mappings?provider_kind=openai&emotion_key=happy",
      "/api/worlds/world-1/speech/transcripts?source_asset_id=audio-1",
    ]);
  });

  it("uses csrf for profile, binding, mapping, TTS, and STT writes", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(voiceProfile))
      .mockResolvedValueOnce(jsonResponse(voiceProfile))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(agentBinding))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(styleMapping))
      .mockResolvedValueOnce(jsonResponse(styleMapping))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(ttsResult))
      .mockResolvedValueOnce(jsonResponse(sttResult));
    vi.stubGlobal("fetch", fetchMock);

    await createVoiceProfile("world-1", {
      worldline_id: "worldline-1",
      profile_key: "akari",
      display_name: "Akari voice",
      status: "active",
      visibility: "world_admin",
      owner_kind: "agent",
      owner_agent_id: "agent-1",
      supported_languages: ["ja"],
      voice_kind: "preset",
      consent_status: "not_required",
      usage_policy_json: {},
      metadata_json: {},
    });
    await updateVoiceProfile("world-1", "voice-1", { display_name: "Akari saved" });
    await deleteVoiceProfile("world-1", "voice-1");
    await createAgentVoiceBinding("world-1", "agent-1", {
      worldline_id: "worldline-1",
      voice_profile_id: "voice-1",
      binding_role: "default",
      priority: 100,
      is_default: true,
      style_overrides_json: {},
    });
    await deleteAgentVoiceBinding("world-1", "agent-1", "binding-1");
    await createStyleMapping("world-1", {
      mapping_key: "openai-happy",
      provider_kind: "openai",
      emotion_key: "happy",
      style_json: { voice: "alloy" },
    });
    await updateStyleMapping("world-1", "mapping-1", { style_json: { voice: "verse" } });
    await deleteStyleMapping("world-1", "mapping-1");
    await runTTS("world-1", {
      worldline_id: "worldline-1",
      provider_id: "provider-tts",
      voice_profile_id: "voice-1",
      text: "hello",
      style_overrides_json: {},
      output_format: "wav",
    });
    await runSTT("world-1", {
      worldline_id: "worldline-1",
      provider_id: "provider-stt",
      source_asset_id: "audio-1",
      diarization: false,
      timestamps: false,
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/speech/voice-profiles",
      "/api/worlds/world-1/speech/voice-profiles/voice-1",
      "/api/worlds/world-1/speech/voice-profiles/voice-1",
      "/api/worlds/world-1/agents/agent-1/voice-profiles",
      "/api/worlds/world-1/agents/agent-1/voice-profiles/binding-1",
      "/api/worlds/world-1/speech/style-mappings",
      "/api/worlds/world-1/speech/style-mappings/mapping-1",
      "/api/worlds/world-1/speech/style-mappings/mapping-1",
      "/api/worlds/world-1/speech/tts",
      "/api/worlds/world-1/speech/stt",
    ]);
    for (const call of fetchMock.mock.calls) {
      expect((call[1].headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    }
  });

  it("encodes speech admin API identifier path segments", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(voiceProfile))
      .mockResolvedValueOnce(jsonResponse(voiceProfile))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(agentBinding))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(styleMapping))
      .mockResolvedValueOnce(jsonResponse(styleMapping))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse([transcript]))
      .mockResolvedValueOnce(jsonResponse(ttsResult))
      .mockResolvedValueOnce(jsonResponse(sttResult));
    vi.stubGlobal("fetch", fetchMock);

    const worldId = "world/live?tab=speech#frag";
    const agentId = "agent/main?voice=true#frag";
    const voiceProfileId = "voice/main?kind=tts#frag";
    const bindingId = "binding/default?role=voice#frag";
    const mappingId = "mapping/happy?provider=openai#frag";

    await listVoiceProfiles(worldId, { worldline_id: "worldline/live?branch=1#frag" });
    await createVoiceProfile(worldId, {
      worldline_id: "worldline-1",
      profile_key: "akari",
      display_name: "Akari voice",
      status: "active",
      visibility: "world_admin",
      owner_kind: "agent",
      owner_agent_id: agentId,
      supported_languages: ["ja"],
      voice_kind: "preset",
      consent_status: "not_required",
      usage_policy_json: {},
      metadata_json: {},
    });
    await updateVoiceProfile(worldId, voiceProfileId, { display_name: "Akari saved" });
    await deleteVoiceProfile(worldId, voiceProfileId);
    await listAgentVoiceBindings(worldId, agentId, { worldline_id: "worldline/live?branch=1#frag" });
    await createAgentVoiceBinding(worldId, agentId, {
      worldline_id: "worldline-1",
      voice_profile_id: voiceProfileId,
      binding_role: "default",
      priority: 100,
      is_default: true,
      style_overrides_json: {},
    });
    await deleteAgentVoiceBinding(worldId, agentId, bindingId);
    await listStyleMappings(worldId, { provider_kind: "openai", emotion_key: "happy" });
    await createStyleMapping(worldId, {
      mapping_key: "openai-happy",
      provider_kind: "openai",
      emotion_key: "happy",
      style_json: { voice: "alloy" },
    });
    await updateStyleMapping(worldId, mappingId, { style_json: { voice: "verse" } });
    await deleteStyleMapping(worldId, mappingId);
    await listTranscripts(worldId, { source_asset_id: "audio/live?take=1#frag" });
    await runTTS(worldId, {
      worldline_id: "worldline-1",
      provider_id: "provider-tts",
      voice_profile_id: voiceProfileId,
      text: "hello",
      style_overrides_json: {},
      output_format: "wav",
    });
    await runSTT(worldId, {
      worldline_id: "worldline-1",
      provider_id: "provider-stt",
      source_asset_id: "audio-1",
      diarization: false,
      timestamps: false,
    });

    const worldSegment = encodeURIComponent(worldId);
    const agentSegment = encodeURIComponent(agentId);
    const voiceSegment = encodeURIComponent(voiceProfileId);
    const bindingSegment = encodeURIComponent(bindingId);
    const mappingSegment = encodeURIComponent(mappingId);
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/" + worldSegment + "/speech/voice-profiles?worldline_id=worldline%2Flive%3Fbranch%3D1%23frag",
      "/api/worlds/" + worldSegment + "/speech/voice-profiles",
      "/api/worlds/" + worldSegment + "/speech/voice-profiles/" + voiceSegment,
      "/api/worlds/" + worldSegment + "/speech/voice-profiles/" + voiceSegment,
      "/api/worlds/" + worldSegment + "/agents/" + agentSegment + "/voice-profiles?worldline_id=worldline%2Flive%3Fbranch%3D1%23frag",
      "/api/worlds/" + worldSegment + "/agents/" + agentSegment + "/voice-profiles",
      "/api/worlds/" + worldSegment + "/agents/" + agentSegment + "/voice-profiles/" + bindingSegment,
      "/api/worlds/" + worldSegment + "/speech/style-mappings?provider_kind=openai&emotion_key=happy",
      "/api/worlds/" + worldSegment + "/speech/style-mappings",
      "/api/worlds/" + worldSegment + "/speech/style-mappings/" + mappingSegment,
      "/api/worlds/" + worldSegment + "/speech/style-mappings/" + mappingSegment,
      "/api/worlds/" + worldSegment + "/speech/transcripts?source_asset_id=audio%2Flive%3Ftake%3D1%23frag",
      "/api/worlds/" + worldSegment + "/speech/tts",
      "/api/worlds/" + worldSegment + "/speech/stt",
    ]);
  });
});

const voiceProfile = {
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
  usage_policy_json: {},
  metadata_json: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const agentBinding = {
  id: "binding-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  agent_id: "agent-1",
  voice_profile_id: "voice-1",
  binding_role: "default",
  priority: 100,
  is_default: true,
  style_overrides_json: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const styleMapping = {
  id: "mapping-1",
  world_id: "world-1",
  mapping_key: "openai-happy",
  provider_kind: "openai",
  emotion_key: "happy",
  style_json: { voice: "alloy" },
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
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
};

const mediaAsset = {
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
  title: "TTS output",
  description: null,
  created_by_actor_ref: "user:admin",
  metadata: {},
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

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
};

const transcript = {
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
  transcript_text: "hello",
  segments_json: null,
  confidence_json: null,
  status: "available",
  visibility: "world_admin",
  created_at: "2026-05-13T00:00:00.000Z",
  updated_at: "2026-05-13T00:00:00.000Z",
};

const invocation = {
  id: "invocation-1",
  status: "succeeded",
  latency_ms: 25,
  request_params_json: {},
  response_metadata_json: {},
};

const ttsResult = {
  media_job: mediaJob,
  output_asset: mediaAsset,
  output_objects: [mediaObject],
  model_invocation: invocation,
  model_invocation_id: "invocation-1",
};

const sttResult = {
  media_job: { ...mediaJob, id: "job-2", job_kind: "speech_transcription", provider_kind: "speech_to_text" },
  transcript,
  model_invocation: { ...invocation, id: "invocation-2" },
  model_invocation_id: "invocation-2",
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
