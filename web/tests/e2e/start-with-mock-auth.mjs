import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const mockPort = 3207;
const nextPort = 3107;
const validCsrf = "valid-csrf";
const adminSession = "admin-session";
const memberSession = "member-session";
const adminUserId = "00000000-0000-4000-8000-000000000001";
const memberUserId = "00000000-0000-4000-8000-000000000002";
const candidateUserId = "00000000-0000-4000-8000-000000000003";
const worldOneId = "10000000-0000-4000-8000-000000000001";
const sceneHomeId = "20000000-0000-4000-8000-000000000001";
const agentGuideId = "30000000-0000-4000-8000-000000000001";
const membershipOwnerId = "40000000-0000-4000-8000-000000000001";
const membershipMemberId = "40000000-0000-4000-8000-000000000002";
const providerOpenAiId = "71000000-0000-4000-8000-000000000001";
const memoryProfilePrimaryId = "71500000-0000-4000-8000-000000000001";
const seedConversationId = "76000000-0000-4000-8000-000000000001";

const users = [
  user(adminUserId, "admin@example.test", "Admin"),
  user(memberUserId, "member@example.test", "Member"),
  user(candidateUserId, "candidate@example.test", "Candidate"),
];
const sessionSubjects = new Map([
  [adminSession, subject(adminUserId, "admin@example.test", "Admin", ["platform_admin"])],
  [memberSession, subject(memberUserId, "member@example.test", "Member", [])],
]);
const worlds = [
  {
    id: worldOneId,
    owner_user_id: adminUserId,
    slug: "first-world",
    name: "First World",
    description: "A managed world",
    rules_config: {},
    memory_backend_profile_id: memoryProfilePrimaryId,
    memory_plugin_identifier: "builtin.local_pgvector_memory",
    memory_plugin_config: {},
    world_rules_plugin_identifier: "builtin.default_world_rules",
    world_rules_plugin_config: {},
    is_active: true,
  },
];
const scenes = [
  {
    id: sceneHomeId,
    world_id: worldOneId,
    scene_key: "home",
    name: "Home",
    description: null,
    is_active: true,
  },
];
const agents = [
  {
    id: agentGuideId,
    world_id: worldOneId,
    home_scene_id: sceneHomeId,
    source_preset_id: null,
    source_preset_version: null,
    agent_key: "guide",
    display_name: "Guide",
    kind: "role_agent",
    provider_profile_id: providerOpenAiId,
    config: { provider_profile_id: providerOpenAiId },
    is_enabled: true,
  },
];
const agentPresets = [];
const memberships = [
  membership(membershipOwnerId, worldOneId, adminUserId, "world_admin"),
  membership(membershipMemberId, worldOneId, memberUserId, "human_user"),
];
const clocks = new Map([
  [
    worldOneId,
    {
      world_id: worldOneId,
      status: "paused",
      current_world_time: "2026-04-17T00:00:00.000Z",
      effective_world_time: "2026-04-17T00:00:00.000Z",
      wall_time_anchor: null,
      speed_multiplier: "1",
      revision: 0,
    },
  ],
]);
const scheduleRules = [
  {
    id: "50000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    rule_key: "weekday",
    name: "Weekday",
    kind: "weekday",
    config: {},
    is_enabled: true,
  },
];
const calendarEntries = [
  {
    id: "60000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    agent_id: agentGuideId,
    title: "Morning scene",
    description: null,
    starts_at: "2030-01-01T08:00:00.000Z",
    ends_at: null,
    recurrence_rule: null,
    status: "active",
    metadata: {},
  },
];
const memoryItems = [
  {
    id: "70000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    agent_id: agentGuideId,
    content: "Guide memory",
    metadata: { source: "mock" },
    backend: "builtin.mem0_oss_memory",
    created_at: "2026-04-17T00:03:05.000Z",
    score: null,
  },
];
const memoryProfileSnapshots = new Map([
  [
    agentGuideId,
    {
      id: "71700000-0000-4000-8000-000000000001",
      world_id: worldOneId,
      agent_id: agentGuideId,
      aliases: ["Guide"],
      identity_notes: ["Resident guide for the first world."],
      durable_preferences: ["Keeps replies concise."],
      long_lived_goals: ["Help operators move the scene forward."],
      language_style_preferences: ["Direct and calm."],
      refreshed_at: "2026-04-17T00:04:00.000Z",
      created_at: "2026-04-17T00:04:00.000Z",
      updated_at: "2026-04-17T00:04:00.000Z",
    },
  ],
]);
const memoryBackendProfiles = [
  {
    id: memoryProfilePrimaryId,
    profile_key: "primary-mem0",
    name: "Primary Mem0",
    backend_kind: "mem0_oss",
    vector_store_config: { provider: "memory" },
    llm_config: { provider: "mock-llm" },
    embedder_config: { provider: "mock-embedder" },
    reranker_config: {},
    secret_refs: { api_key: "mem0-primary" },
    is_enabled: true,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const memoryWriteLogs = [
  {
    id: "71800000-0000-4000-8000-000000000001",
    job_id: "71900000-0000-4000-8000-000000000001",
    backend: "builtin.mem0_oss_memory",
    success: true,
    latency_ms: 7,
    request_summary: { source: "conversation_turn" },
    response_summary: { stored: 1 },
    correlation_ids: { world_id: worldOneId, agent_id: agentGuideId },
    occurred_at: "2026-04-17T00:05:00.000Z",
  },
];
const memoryWriteJobs = [
  {
    id: "71900000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    agent_id: agentGuideId,
    backend_profile_id: memoryProfilePrimaryId,
    backend_profile_key: "primary-mem0",
    backend_profile_name: "Primary Mem0",
    backend_kind: "mem0_oss",
    source_kind: "conversation_turn",
    source_id: "72000000-0000-4000-8000-000000000001",
    dedupe_key: "mock-memory-job-1",
    status: "failed",
    attempt_count: 2,
    next_attempt_at: "2026-04-17T00:10:00.000Z",
    last_error: "mock backend timeout",
    processed_at: null,
    is_retryable: true,
    terminal_reason: null,
    last_log_success: true,
    age_seconds: 300,
    created_at: "2026-04-17T00:04:30.000Z",
    updated_at: "2026-04-17T00:05:30.000Z",
  },
];
const memoryRetrievalLogs = [
  {
    id: "71800000-0000-4000-8000-000000000002",
    world_id: worldOneId,
    agent_id: agentGuideId,
    backend_profile_id: memoryProfilePrimaryId,
    backend: "builtin.mem0_oss_memory",
    query_text: "guide context",
    hit_count: 1,
    selected_item_ids: [memoryItems[0].id],
    latency_ms: 3,
    context_item_count: 1,
    occurred_at: "2026-04-17T00:05:05.000Z",
  },
];
const agentPersonas = new Map([
  [
    agentGuideId,
    {
      id: "70500000-0000-4000-8000-000000000001",
      world_id: worldOneId,
      agent_id: agentGuideId,
      persona_text: "Careful guide.",
      behavior_policy: { tone: "direct" },
      policy_plugin_identifier: "builtin.default_persona_policy",
      policy_plugin_config: {},
      is_enabled: true,
      created_at: "2026-04-17T00:02:00.000Z",
      updated_at: "2026-04-17T00:02:00.000Z",
    },
  ],
]);
const agentObservations = [
  {
    id: "70600000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    agent_id: agentGuideId,
    source_event_id: null,
    observation_type: "manual",
    content: "Initial observation",
    metadata: {},
    observed_at: "2026-04-17T00:02:00.000Z",
    consumed_at: null,
    created_at: "2026-04-17T00:02:00.000Z",
  },
];
const providerProfiles = [
  {
    id: providerOpenAiId,
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
];
const runtimeControl = {
  desired_state: "stopped",
  last_heartbeat_at: null,
  last_run_started_at: null,
  last_run_finished_at: null,
  last_error: null,
};
const runtimeDiagnostics = [
  {
    id: "74000000-0000-4000-8000-000000000001",
    severity: "info",
    component: "runtime",
    event_type: "runtime.iteration_skipped",
    message: "Runtime iteration skipped because desired state is stopped.",
    details: {},
    occurred_at: "2026-04-17T00:00:00.000Z",
    world_id: null,
    agent_id: null,
    run_id: null,
    provider_profile_id: null,
    created_at: "2026-04-17T00:00:00.000Z",
  },
];
const worldDiagnostics = [
  {
    id: "74000000-0000-4000-8000-000000000002",
    severity: "info",
    component: "agent",
    event_type: "agent.run_succeeded",
    message: "Agent runtime run succeeded.",
    details: {},
    occurred_at: "2026-04-17T00:03:01.000Z",
    world_id: worldOneId,
    agent_id: agentGuideId,
    run_id: "72000000-0000-4000-8000-000000000001",
    provider_profile_id: providerProfiles[0].id,
    created_at: "2026-04-17T00:03:01.000Z",
  },
];
const agentRuns = [
  {
    run_id: "72000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    agent_id: agentGuideId,
    status: "succeeded",
    prompt_text: "Initial prompt",
    response_text: "Initial response",
    provider_profile_id: providerProfiles[0].id,
    diagnostics: { persona_enabled: true, observation_count: 1 },
    started_at: "2026-04-17T00:03:00.000Z",
    finished_at: "2026-04-17T00:03:01.000Z",
  },
];
const narrativeArtifacts = [
  {
    id: "73000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    agent_id: agentGuideId,
    source_run_id: agentRuns[0].run_id,
    source_conversation_id: null,
    title: "Initial artifact",
    content: "Initial artifact content",
    artifact_kind: "agent_note",
    metadata: {},
    created_at: "2026-04-17T00:03:02.000Z",
    publication: null,
  },
  {
    id: "73000000-0000-4000-8000-000000000002",
    world_id: worldOneId,
    agent_id: null,
    source_run_id: null,
    source_conversation_id: seedConversationId,
    title: "Seed conversation summary",
    content: "Summary for the seeded conversation.",
    artifact_kind: "conversation_summary",
    metadata: { generation_mode: "manual", scope_type: "world" },
    created_at: "2026-04-17T00:03:03.000Z",
    publication: {
      id: "73500000-0000-4000-8000-000000000001",
      world_id: worldOneId,
      artifact_id: "73000000-0000-4000-8000-000000000002",
      source_draft_id: "73000000-0000-4000-8000-000000000002",
      status: "published",
      reader_visible: true,
      metadata: { channel: "reader" },
      published_at: "2026-04-17T00:03:03.000Z",
      unpublished_at: null,
      published_by_user_id: adminUserId,
      created_at: "2026-04-17T00:03:03.000Z",
      updated_at: "2026-04-17T00:03:03.000Z",
    },
  },
  {
    id: "73000000-0000-4000-8000-000000000003",
    world_id: worldOneId,
    agent_id: null,
    source_run_id: null,
    source_conversation_id: seedConversationId,
    title: "Seed chapter draft",
    content: "Chapter draft for the seeded conversation.",
    artifact_kind: "chapter_draft",
    metadata: { generation_mode: "manual", scope_type: "world" },
    created_at: "2026-04-17T00:03:04.000Z",
    publication: null,
  },
];
const replaySequences = new Map([[worldOneId, 1]]);
const snapshots = new Map();
const clockTransitions = new Map([
  [
    worldOneId,
    [
      {
        id: "75000000-0000-4000-8000-000000000001",
        world_id: worldOneId,
        transition_type: "initialize",
        previous_status: null,
        new_status: "paused",
        previous_world_time: null,
        new_world_time: "2026-04-17T00:00:00.000Z",
        wall_time: "2026-04-17T00:00:00.000Z",
        previous_revision: null,
        new_revision: 0,
        actor_ref: "system:mock",
        correlation_id: null,
        reason: "mock init",
        created_at: "2026-04-17T00:00:00.000Z",
      },
    ],
  ],
]);
const worldEvents = new Map([
  [
    worldOneId,
    [
      {
        id: "76000000-0000-4000-8000-000000000001",
        world_id: worldOneId,
        sequence: 1,
        event_name: "world.clock_advanced",
        payload: { revision: 1, status: "running" },
        wall_time: "2026-04-17T00:02:00.000Z",
        world_time: "2030-01-01T00:00:00.000Z",
        actor_ref: "system:runtime",
        causation_event_id: null,
        correlation_id: null,
        created_at: "2026-04-17T00:02:00.000Z",
      },
    ],
  ],
]);
const pluginCatalog = [
  {
    identifier: "builtin.openai_compatible",
    category: "model_provider",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["chat_completion"],
    built_in: true,
  },
  {
    identifier: "builtin.anthropic_compatible",
    category: "model_provider",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["messages"],
    built_in: true,
  },
  {
    identifier: "builtin.local_pgvector_memory",
    category: "memory_backend",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["vector_search"],
    built_in: true,
  },
  {
    identifier: "builtin.mem0_oss_memory",
    category: "memory_backend",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["long_term_memory"],
    built_in: true,
  },
  {
    identifier: "builtin.default_world_rules",
    category: "world_rules",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["due_rules"],
    built_in: true,
  },
  {
    identifier: "builtin.default_persona_policy",
    category: "persona_policy",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["build_prompt"],
    built_in: true,
  },
  {
    identifier: "builtin.default_narrative_writer",
    category: "narrative_writer",
    version: "0.1.0",
    config_schema: {},
    capabilities: ["summary", "chapter"],
    built_in: true,
  },
];
const conversations = [
  {
    id: seedConversationId,
    world_id: worldOneId,
    scene_id: null,
    session_key: "seed-reader",
    title: "Seed Reader Conversation",
    scope_type: "world",
    mode: "manual_chain",
    status: "completed",
    objective: "Seed the narrative reader.",
    opening_prompt: "Start the seed conversation.",
    max_turns: 2,
    next_turn_index: 2,
    policy: {
      error_policy: "fail_session",
      max_consecutive_failed_turns: 1,
      loop_guard_window: 4,
      repeat_output_threshold: 2,
    },
    writer_config: {
      provider_profile_id: null,
      writer_plugin_identifier: "builtin.default_narrative_writer",
      writer_plugin_config: {},
      auto_generate_on_complete: true,
      generate_summary: true,
      generate_chapter: true,
    },
    memory_config: {
      write_turn_memory: true,
      retrieve_memory: true,
      max_context_items: 5,
      query_window: 4,
    },
    terminal_reason: "max_turns_reached",
    created_at: "2026-04-17T00:02:00.000Z",
    updated_at: "2026-04-17T00:03:04.000Z",
  },
];
const conversationParticipants = [
  {
    id: "76100000-0000-4000-8000-000000000001",
    session_id: seedConversationId,
    agent_id: agentGuideId,
    turn_order: 0,
    is_enabled: true,
    created_at: "2026-04-17T00:02:00.000Z",
    updated_at: "2026-04-17T00:02:00.000Z",
  },
];
const conversationTurns = [
  {
    id: "76200000-0000-4000-8000-000000000001",
    session_id: seedConversationId,
    turn_index: 0,
    speaker_kind: "operator",
    speaker_agent_id: null,
    input_text: "Seed the conversation.",
    output_text: "Seed the conversation.",
    status: "succeeded",
    run_id: null,
    error_text: null,
    created_at: "2026-04-17T00:02:30.000Z",
    updated_at: "2026-04-17T00:02:30.000Z",
  },
  {
    id: "76200000-0000-4000-8000-000000000002",
    session_id: seedConversationId,
    turn_index: 1,
    speaker_kind: "agent",
    speaker_agent_id: agentGuideId,
    input_text: "Seed the conversation.",
    output_text: "Guide replies to seed the conversation.",
    status: "succeeded",
    run_id: null,
    error_text: null,
    created_at: "2026-04-17T00:02:31.000Z",
    updated_at: "2026-04-17T00:02:31.000Z",
  },
];

const mockServer = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://${request.headers.host}`);
  if (request.method === "GET" && url.pathname === "/auth/csrf") {
    sendJson(response, 200, { csrf_token: validCsrf }, [csrfCookie()]);
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await readJson(request);
    if (body.email === "admin@example.test" && body.password === "correct-password") {
      sendJson(response, 200, sessionSubjects.get(adminSession), [
        sessionCookie(adminSession),
        csrfCookie(),
      ]);
      return;
    }
    if (body.email === "member@example.test" && body.password === "correct-password") {
      sendJson(response, 200, sessionSubjects.get(memberSession), [
        sessionCookie(memberSession),
        csrfCookie(),
      ]);
      return;
    }
    sendJson(response, 401, { detail: "Invalid email or password" });
    return;
  }

  if (request.method === "GET" && url.pathname === "/auth/me") {
    const currentSubject = subjectForRequest(request);
    if (currentSubject !== null) {
      sendJson(response, 200, currentSubject);
      return;
    }
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/logout") {
    if (subjectForRequest(request) === null) {
      sendJson(response, 401, { detail: "Invalid or missing session" });
      return;
    }
    if (!hasValidCsrf(request)) {
      sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
      return;
    }
    response.writeHead(204, {
      "set-cookie": [
        "noveland_session=; Max-Age=0; Path=/; SameSite=Lax; HttpOnly",
        "noveland_csrf=; Max-Age=0; Path=/; SameSite=Lax",
      ],
    });
    response.end();
    return;
  }

  if (url.pathname === "/runtime/control") {
    await handleRuntimeControl(request, response);
    return;
  }

  if (url.pathname === "/runtime/status") {
    handleRuntimeStatus(response);
    return;
  }

  if (url.pathname === "/runtime/diagnostics") {
    handleRuntimeDiagnostics(request, response);
    return;
  }

  if (url.pathname === "/plugins/catalog") {
    handlePluginCatalog(url, response);
    return;
  }

  if (url.pathname === "/provider-profiles") {
    await handleProviderProfiles(request, response);
    return;
  }

  if (url.pathname === "/provider-profiles/health") {
    handleProviderProfileHealth(request, response);
    return;
  }

  if (url.pathname === "/memory-backfill/dry-run") {
    handleMemoryBackfillDryRun(request, response);
    return;
  }

  if (url.pathname === "/memory-backend-profiles") {
    await handleMemoryBackendProfiles(request, response);
    return;
  }

  if (url.pathname === "/agent-presets") {
    await handleAgentPresets(request, response);
    return;
  }

  if (url.pathname.startsWith("/agent-presets/")) {
    const presetSegments = url.pathname.split("/");
    await handleAgentPresetItem(request, response, presetSegments[2]);
    return;
  }

  if (url.pathname === "/world-compositions/import") {
    await handleWorldCompositionImport(request, response);
    return;
  }

  if (url.pathname === "/world-compositions/validate") {
    await handleWorldCompositionValidate(request, response);
    return;
  }

  if (url.pathname.startsWith("/provider-profiles/")) {
    const providerSegments = url.pathname.split("/");
    await handleProviderProfileItem(request, response, providerSegments[2], providerSegments[3]);
    return;
  }

  if (url.pathname.startsWith("/memory-backend-profiles/")) {
    const memorySegments = url.pathname.split("/");
    await handleMemoryBackendProfileItem(
      request,
      response,
      memorySegments[2],
      memorySegments[3],
    );
    return;
  }

  if (url.pathname.startsWith("/memory-write-jobs/")) {
    const memoryJobSegments = url.pathname.split("/");
    await handleMemoryWriteJobItem(request, response, memoryJobSegments[2], memoryJobSegments[3]);
    return;
  }

  if (url.pathname === "/worlds") {
    await handleWorldCollection(request, response);
    return;
  }

  if (url.pathname.startsWith("/worlds/")) {
    await handleWorldResource(request, response, url);
    return;
  }

  sendJson(response, 404, { detail: "not found" });
});

mockServer.listen(mockPort, "127.0.0.1", () => {
  const nextProcess = spawn(
    "npm",
    ["run", "dev", "--", "--hostname", "127.0.0.1", "--port", String(nextPort)],
    {
      stdio: "inherit",
      env: {
        ...process.env,
        NOVELAND_API_BASE_URL: `http://127.0.0.1:${mockPort}`,
      },
    },
  );

  const shutdown = () => {
    nextProcess.kill("SIGTERM");
    mockServer.close(() => process.exit(0));
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
  nextProcess.on("exit", (code) => {
    mockServer.close(() => process.exit(code ?? 0));
  });
});

async function handleWorldCollection(request, response) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  if (request.method === "GET") {
    const visibleWorlds = isPlatformAdmin(currentSubject)
      ? worlds
      : worlds.filter((world) => membershipFor(world.id, currentSubject.user_id) !== undefined);
    sendJson(response, 200, visibleWorlds);
    return;
  }
  if (request.method === "POST") {
    if (!isPlatformAdmin(currentSubject)) {
      sendJson(response, 403, { detail: "Forbidden" });
      return;
    }
    if (!hasValidCsrf(request)) {
      sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
      return;
    }
    const body = await readJson(request);
    if (worlds.some((world) => world.slug === body.slug)) {
      sendJson(response, 409, { detail: "World slug already exists" });
      return;
    }
    const world = {
      id: randomUUID(),
      owner_user_id: currentSubject.user_id,
      slug: body.slug,
      name: body.name,
      description: body.description ?? null,
      rules_config: body.rules_config ?? {},
      memory_backend_profile_id: body.memory_backend_profile_id ?? memoryProfilePrimaryId,
      memory_plugin_identifier:
        body.memory_plugin_identifier ?? "builtin.local_pgvector_memory",
      memory_plugin_config: body.memory_plugin_config ?? {},
      world_rules_plugin_identifier:
        body.world_rules_plugin_identifier ?? "builtin.default_world_rules",
      world_rules_plugin_config: body.world_rules_plugin_config ?? {},
      is_active: true,
    };
    worlds.push(world);
    memberships.push(membership(randomUUID(), world.id, currentSubject.user_id, "world_admin"));
    clocks.set(world.id, clockForWorld(world.id));
    replaySequences.set(world.id, 0);
    worldEvents.set(world.id, []);
    clockTransitions.set(world.id, []);
    sendJson(response, 201, world);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleWorldResource(request, response, url) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  const segments = url.pathname.split("/").filter(Boolean);
  const worldId = segments[1];
  const world = worlds.find((item) => item.id === worldId);
  if (world === undefined || !canReadWorld(currentSubject, worldId)) {
    sendJson(response, 404, { detail: "World not found" });
    return;
  }

  if (segments.length === 2) {
    await handleWorldItem(request, response, currentSubject, world);
    return;
  }

  const resource = segments[2];
  if (resource === "scenes") {
    await handleScenes(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "agents") {
    await handleAgents(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "memberships") {
    await handleMemberships(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "member-candidates") {
    handleMemberCandidates(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "schedule-rules") {
    await handleScheduleRules(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "narrative-artifacts") {
    await handleNarrativeArtifacts(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "clock") {
    await handleClock(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "replay") {
    handleReplay(request, response, worldId, segments[3]);
    return;
  }
  if (resource === "snapshots") {
    await handleSnapshots(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "events") {
    handleWorldEvents(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "diagnostics") {
    handleWorldDiagnostics(request, response, currentSubject, worldId);
    return;
  }
  if (resource === "composition-export") {
    handleWorldCompositionExport(request, response, currentSubject, worldId);
    return;
  }
  if (resource === "conversations") {
    await handleConversations(request, response, currentSubject, worldId, segments[3], segments[4]);
    return;
  }
  sendJson(response, 404, { detail: "not found" });
}

async function handleWorldItem(request, response, currentSubject, world) {
  if (request.method === "GET") {
    sendJson(response, 200, world);
    return;
  }
  if (!canManageWorld(currentSubject, world.id)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(world, await readJson(request));
    sendJson(response, 200, world);
    return;
  }
  if (request.method === "DELETE") {
    world.is_active = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleScenes(request, response, currentSubject, worldId, sceneId) {
  if (request.method === "GET" && sceneId === undefined) {
    sendJson(response, 200, scenes.filter((scene) => scene.world_id === worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && sceneId === undefined) {
    const body = await readJson(request);
    if (scenes.some((scene) => scene.world_id === worldId && scene.scene_key === body.scene_key)) {
      sendJson(response, 409, { detail: "Scene key already exists" });
      return;
    }
    const scene = {
      id: randomUUID(),
      world_id: worldId,
      scene_key: body.scene_key,
      name: body.name,
      description: body.description ?? null,
      is_active: true,
    };
    scenes.push(scene);
    sendJson(response, 201, scene);
    return;
  }
  const scene = scenes.find((item) => item.id === sceneId && item.world_id === worldId);
  if (scene === undefined) {
    sendJson(response, 404, { detail: "Scene not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(scene, await readJson(request));
    sendJson(response, 200, scene);
    return;
  }
  if (request.method === "DELETE") {
    scene.is_active = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAgents(request, response, currentSubject, worldId, agentId) {
  if (agentId !== undefined && arguments.length >= 5) {
    const segments = new URL(request.url ?? "/", `http://${request.headers.host}`).pathname
      .split("/")
      .filter(Boolean);
    if (segments[4] === "calendar") {
      await handleCalendar(request, response, currentSubject, worldId, agentId, segments[5]);
      return;
    }
    if (segments[4] === "memory") {
      await handleMemory(
        request,
        response,
        currentSubject,
        worldId,
        agentId,
        segments[5],
        segments[6],
      );
      return;
    }
    if (segments[4] === "persona") {
      await handlePersona(request, response, currentSubject, worldId, agentId);
      return;
    }
    if (segments[4] === "observations") {
      await handleObservations(request, response, currentSubject, worldId, agentId, segments[5]);
      return;
    }
    if (segments[4] === "runs") {
      handleAgentRuns(request, response, currentSubject, worldId, agentId);
      return;
    }
    if (segments[4] === "run") {
      await handleAgentRun(request, response, currentSubject, worldId, agentId);
      return;
    }
  }
  if (request.method === "GET" && agentId === undefined) {
    sendJson(response, 200, agents.filter((agent) => agent.world_id === worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && agentId === undefined) {
    const body = await readJson(request);
    if (agents.some((agent) => agent.world_id === worldId && agent.agent_key === body.agent_key)) {
      sendJson(response, 409, { detail: "Agent key already exists" });
      return;
    }
    const preset =
      body.preset_id == null
        ? null
        : agentPresets.find((item) => item.id === body.preset_id && item.is_active) ?? null;
    if (body.preset_id != null && preset === null) {
      sendJson(response, 404, { detail: "Not found" });
      return;
    }
    const presetProviderProfile =
      preset?.default_provider_profile_key == null
        ? null
        : providerProfiles.find((item) => item.profile_key === preset.default_provider_profile_key) ?? null;
    const providerProfileId = body.provider_profile_id ?? presetProviderProfile?.id ?? null;
    const agent = {
      id: randomUUID(),
      world_id: worldId,
      home_scene_id: body.home_scene_id ?? null,
      source_preset_id: preset?.id ?? null,
      source_preset_version: preset?.version ?? null,
      agent_key: body.agent_key,
      display_name: body.display_name,
      kind: body.kind ?? preset?.default_kind ?? "role_agent",
      provider_profile_id: providerProfileId,
      config: {
        ...(preset?.advanced_config ?? {}),
        ...(body.config ?? {}),
        ...(providerProfileId === undefined || providerProfileId === null
          ? {}
          : { provider_profile_id: providerProfileId }),
      },
      is_enabled: true,
    };
    agents.push(agent);
    materializePresetForAgent(worldId, agent.id, preset);
    sendJson(response, 201, agent);
    return;
  }
  const agent = agents.find((item) => item.id === agentId && item.world_id === worldId);
  if (agent === undefined) {
    sendJson(response, 404, { detail: "Agent not found" });
    return;
  }
  if (request.method === "PATCH") {
    const body = await readJson(request);
    Object.assign(agent, body);
    if (Object.hasOwn(body, "provider_profile_id")) {
      agent.provider_profile_id = body.provider_profile_id;
      agent.config = {
        ...(agent.config ?? {}),
        ...(body.provider_profile_id === null ? {} : { provider_profile_id: body.provider_profile_id }),
      };
      if (body.provider_profile_id === null) {
        delete agent.config.provider_profile_id;
      }
    }
    sendJson(response, 200, agent);
    return;
  }
  if (request.method === "DELETE") {
    agent.is_enabled = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleWorldCompositionExport(request, response, currentSubject, worldId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method !== "GET") {
    sendJson(response, 405, { detail: "method not allowed" });
    return;
  }
  const world = worlds.find((item) => item.id === worldId);
  sendJson(response, 200, {
    world: {
      slug: world.slug,
      name: world.name,
      description: world.description,
      rules_config: world.rules_config,
      is_active: world.is_active,
    },
    scenes: scenes
      .filter((scene) => scene.world_id === worldId)
      .map((scene) => ({
        scene_key: scene.scene_key,
        name: scene.name,
        description: scene.description,
        is_active: scene.is_active,
      })),
    agents: agents
      .filter((agent) => agent.world_id === worldId)
      .map((agent) => ({
        agent_key: agent.agent_key,
        display_name: agent.display_name,
        kind: agent.kind,
        home_scene_key:
          agent.home_scene_id == null
            ? null
            : scenes.find((scene) => scene.id === agent.home_scene_id)?.scene_key ?? null,
        source_preset_key:
          agent.source_preset_id == null
            ? null
            : agentPresets.find((preset) => preset.id === agent.source_preset_id)?.preset_key ?? null,
        source_preset_version: agent.source_preset_version ?? null,
        provider_profile_key:
          agent.provider_profile_id == null
            ? null
            : providerProfiles.find((profile) => profile.id === agent.provider_profile_id)?.profile_key ?? null,
        config: agent.config,
        is_enabled: agent.is_enabled,
      })),
    schedule_rules: scheduleRules
      .filter((rule) => rule.world_id === worldId)
      .map((rule) => ({
        rule_key: rule.rule_key,
        name: rule.name,
        kind: rule.kind,
        config: rule.config,
        is_enabled: rule.is_enabled,
      })),
    preset_references: Array.from(
      new Map(
        agents
          .filter((agent) => agent.world_id === worldId && agent.source_preset_id !== null)
          .map((agent) => {
            const preset = agentPresets.find((item) => item.id === agent.source_preset_id);
            return [
              preset?.preset_key,
              preset == null
                ? null
                : {
                    preset_key: preset.preset_key,
                    name: preset.name,
                    default_kind: preset.default_kind,
                    default_provider_profile_key: preset.default_provider_profile_key,
                    version: preset.version,
                    is_active: preset.is_active,
                  },
            ];
          })
          .filter((entry) => entry[1] !== null),
      ).values(),
    ),
  });
}

async function handleRuntimeControl(request, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, runtimeControl);
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PATCH") {
    const body = await readJson(request);
    runtimeControl.desired_state = body.desired_state;
    runtimeControl.last_heartbeat_at = new Date().toISOString();
    sendJson(response, 200, runtimeControl);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleRuntimeStatus(response) {
  sendJson(response, 200, {
    ...runtimeControl,
    runtime_loop_interval_seconds: 5,
    runtime_batch_limit: 20,
    memory_write_jobs: {
      pending_count: memoryWriteJobs.filter((job) => job.status === "pending").length,
      processing_count: memoryWriteJobs.filter((job) => job.status === "processing").length,
      succeeded_count: memoryWriteJobs.filter((job) => job.status === "succeeded").length,
      failed_count: memoryWriteJobs.filter((job) => job.status === "failed").length,
      due_count: memoryWriteJobs.filter((job) => ["pending", "failed"].includes(job.status))
        .length,
      retryable_failed_count: memoryWriteJobs.filter(
        (job) => job.status === "failed" && job.is_retryable,
      ).length,
      terminal_failed_count: memoryWriteJobs.filter(
        (job) => job.status === "failed" && !job.is_retryable,
      ).length,
      stalled_processing_count: 0,
    },
    runtime_health: {
      status: runtimeControl.desired_state === "running" ? "healthy" : "stopped",
      reason:
        runtimeControl.desired_state === "running"
          ? "Runtime is running without recent blocking errors."
          : "Runtime desired state is stopped.",
      recent_diagnostic_count: runtimeDiagnostics.length,
      recent_error_count: runtimeDiagnostics.filter((item) => item.severity === "error").length,
      heartbeat_age_seconds: runtimeControl.last_heartbeat_at === null ? null : 1,
    },
  });
}

function handleRuntimeDiagnostics(request, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  sendJson(response, 200, runtimeDiagnostics);
}

function handlePluginCatalog(url, response) {
  const category = url.searchParams.get("category");
  sendJson(
    response,
    200,
    category === null
      ? pluginCatalog
      : pluginCatalog.filter((plugin) => plugin.category === category),
  );
}

function handleWorldDiagnostics(request, response, currentSubject, worldId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  sendJson(response, 200, worldDiagnostics.filter((item) => item.world_id === worldId));
}

async function handleProviderProfiles(request, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, providerProfiles);
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST") {
    const body = await readJson(request);
    const profile = {
      id: randomUUID(),
      profile_key: body.profile_key,
      name: body.name,
      provider_type: body.provider_type,
      plugin_identifier:
        body.plugin_identifier
        ?? (body.provider_type === "anthropic_compatible"
          ? "builtin.anthropic_compatible"
          : "builtin.openai_compatible"),
      plugin_config: body.plugin_config ?? {},
      base_url: body.base_url,
      model_name: body.model_name,
      capabilities: body.capabilities ?? {},
      api_key_ref: body.api_key_ref,
      timeout_seconds: body.timeout_seconds ?? 20,
      retry_attempts: body.retry_attempts ?? 1,
      rate_limit_per_minute: body.rate_limit_per_minute ?? null,
      last_tested_at: null,
      last_test_status: null,
      last_test_error: null,
      is_enabled: true,
    };
    providerProfiles.push(profile);
    sendJson(response, 201, profile);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleProviderProfileHealth(request, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  sendJson(
    response,
    200,
    providerProfiles.map((profile) => {
      const diagnostics = runtimeDiagnostics.filter(
        (item) => item.provider_profile_id === profile.id,
      );
      const errorCount = diagnostics.filter((item) => item.severity === "error").length;
      return {
        id: profile.id,
        profile_key: profile.profile_key,
        name: profile.name,
        provider_type: profile.provider_type,
        is_enabled: profile.is_enabled,
        health: profile.is_enabled
          ? profile.last_test_status === null
            ? "untested"
            : errorCount > 0 || profile.last_test_status === "failed"
              ? "degraded"
              : "ok"
          : "disabled",
        api_key_ref: profile.api_key_ref,
        secret_ref_status: "configured",
        secret_ref_message: null,
        last_tested_at: profile.last_tested_at,
        last_test_status: profile.last_test_status,
        last_test_error: profile.last_test_error,
        missing_secret_ref: false,
        recent_diagnostic_count: diagnostics.length,
        recent_error_count: errorCount,
      };
    }),
  );
}

function handleMemoryBackfillDryRun(request, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  sendJson(response, 200, {
    candidate_count: 3,
    skipped_existing_count: 1,
    skipped_no_profile_count: 0,
    skipped_disabled_profile_count: 0,
    source_summaries: [
      {
        source_kind: "agent_run",
        candidate_count: 1,
        skipped_existing_count: 1,
        skipped_no_profile_count: 0,
        skipped_disabled_profile_count: 0,
      },
      {
        source_kind: "conversation_turn",
        candidate_count: 1,
        skipped_existing_count: 0,
        skipped_no_profile_count: 0,
        skipped_disabled_profile_count: 0,
      },
      {
        source_kind: "world_event",
        candidate_count: 1,
        skipped_existing_count: 0,
        skipped_no_profile_count: 0,
        skipped_disabled_profile_count: 0,
      },
    ],
    world_summaries: [
      {
        world_id: worldOneId,
        backend_profile_id: memoryProfilePrimaryId,
        backend_profile_key: "primary-mem0",
        candidate_count: 3,
        skipped_existing_count: 1,
        skipped_no_profile_count: 0,
        skipped_disabled_profile_count: 0,
      },
    ],
  });
}

async function handleMemoryBackendProfiles(request, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, memoryBackendProfiles);
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST") {
    const body = await readJson(request);
    const profile = {
      id: randomUUID(),
      profile_key: body.profile_key,
      name: body.name,
      backend_kind: body.backend_kind ?? "mem0_oss",
      vector_store_config: body.vector_store_config ?? {},
      llm_config: body.llm_config ?? {},
      embedder_config: body.embedder_config ?? {},
      reranker_config: body.reranker_config ?? {},
      secret_refs: body.secret_refs ?? {},
      is_enabled: body.is_enabled ?? true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    memoryBackendProfiles.unshift(profile);
    sendJson(response, 201, profile);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAgentPresets(request, response) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  if (request.method === "GET") {
    sendJson(
      response,
      200,
      isPlatformAdmin(currentSubject)
        ? agentPresets
        : agentPresets.filter((preset) => preset.is_active),
    );
    return;
  }
  if (!isPlatformAdmin(currentSubject)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST") {
    const body = await readJson(request);
    if (agentPresets.some((preset) => preset.preset_key === body.preset_key)) {
      sendJson(response, 409, { detail: "Preset key already exists" });
      return;
    }
    const now = new Date().toISOString();
    const preset = {
      id: randomUUID(),
      preset_key: body.preset_key,
      name: body.name,
      description: body.description ?? null,
      default_kind: body.default_kind,
      default_provider_profile_key: body.default_provider_profile_key ?? null,
      persona_text: body.persona_text ?? "",
      behavior_policy: body.behavior_policy ?? {},
      calendar_blueprint: body.calendar_blueprint ?? [],
      advanced_config: body.advanced_config ?? {},
      version: 1,
      is_active: body.is_active ?? true,
      created_at: now,
      updated_at: now,
    };
    agentPresets.push(preset);
    sendJson(response, 201, preset);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAgentPresetItem(request, response, presetId) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const preset = agentPresets.find((item) => item.id === presetId);
  if (preset === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PATCH") {
    const body = await readJson(request);
    const materialChange = [
      "preset_key",
      "name",
      "description",
      "default_kind",
      "default_provider_profile_key",
      "persona_text",
      "behavior_policy",
      "calendar_blueprint",
      "advanced_config",
    ].some((key) => Object.hasOwn(body, key));
    Object.assign(preset, body, {
      version: materialChange ? preset.version + 1 : preset.version,
      updated_at: new Date().toISOString(),
    });
    sendJson(response, 200, preset);
    return;
  }
  if (request.method === "DELETE") {
    preset.is_active = false;
    preset.updated_at = new Date().toISOString();
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleWorldCompositionImport(request, response) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  if (!isPlatformAdmin(currentSubject)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method !== "POST") {
    sendJson(response, 405, { detail: "method not allowed" });
    return;
  }

  const body = await readJson(request);
  const owner = users.find((user) => user.id === body.owner_user_id && user.is_active);
  if (owner === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (worlds.some((world) => world.slug === body.slug)) {
    sendJson(response, 409, { detail: "World slug already exists" });
    return;
  }

  const composition = body.composition;
  for (const presetReference of composition.preset_references ?? []) {
    if (!agentPresets.some((preset) => preset.preset_key === presetReference.preset_key)) {
      sendJson(response, 422, { detail: `Unknown agent preset: ${presetReference.preset_key}` });
      return;
    }
  }

  const world = {
    id: randomUUID(),
    owner_user_id: owner.id,
    slug: body.slug,
    name: body.name,
    description: body.description ?? composition.world.description ?? null,
    rules_config: body.rules_config ?? composition.world.rules_config ?? {},
    memory_backend_profile_id: body.memory_backend_profile_id ?? memoryProfilePrimaryId,
    memory_plugin_identifier:
      composition.world.memory_plugin_identifier ?? "builtin.local_pgvector_memory",
    memory_plugin_config: composition.world.memory_plugin_config ?? {},
    world_rules_plugin_identifier:
      composition.world.world_rules_plugin_identifier ?? "builtin.default_world_rules",
    world_rules_plugin_config: composition.world.world_rules_plugin_config ?? {},
    is_active: composition.world.is_active,
  };
  worlds.push(world);
  memberships.push(membership(randomUUID(), world.id, owner.id, "world_admin"));
  clocks.set(world.id, clockForWorld(world.id));
  replaySequences.set(world.id, 0);
  worldEvents.set(world.id, []);
  clockTransitions.set(world.id, []);

  const sceneKeyToId = new Map();
  for (const scene of composition.scenes ?? []) {
    const createdScene = {
      id: randomUUID(),
      world_id: world.id,
      scene_key: scene.scene_key,
      name: scene.name,
      description: scene.description ?? null,
      is_active: scene.is_active,
    };
    scenes.push(createdScene);
    sceneKeyToId.set(scene.scene_key, createdScene.id);
  }

  for (const rule of composition.schedule_rules ?? []) {
    scheduleRules.push({
      id: randomUUID(),
      world_id: world.id,
      rule_key: rule.rule_key,
      name: rule.name,
      kind: rule.kind,
      config: rule.config ?? {},
      is_enabled: rule.is_enabled,
    });
  }

  for (const exportedAgent of composition.agents ?? []) {
    const preset =
      exportedAgent.source_preset_key === null
        ? null
        : agentPresets.find((item) => item.preset_key === exportedAgent.source_preset_key) ?? null;
    const providerProfile =
      exportedAgent.provider_profile_key === null
        ? null
        : providerProfiles.find((item) => item.profile_key === exportedAgent.provider_profile_key) ?? null;
    const presetProviderProfile =
      preset?.default_provider_profile_key == null
        ? null
        : providerProfiles.find((item) => item.profile_key === preset.default_provider_profile_key) ?? null;
    const providerProfileId = providerProfile?.id ?? presetProviderProfile?.id ?? null;
    const config = {
      ...(preset?.advanced_config ?? {}),
      ...(exportedAgent.config ?? {}),
      ...(providerProfileId === null ? {} : { provider_profile_id: providerProfileId }),
    };
    const agent = {
      id: randomUUID(),
      world_id: world.id,
      home_scene_id:
        exportedAgent.home_scene_key === null
          ? null
          : (sceneKeyToId.get(exportedAgent.home_scene_key) ?? null),
      source_preset_id: preset?.id ?? null,
      source_preset_version: preset?.version ?? null,
      agent_key: exportedAgent.agent_key,
      display_name: exportedAgent.display_name,
      kind: exportedAgent.kind ?? preset?.default_kind ?? "role_agent",
      provider_profile_id: providerProfileId,
      config,
      is_enabled: exportedAgent.is_enabled,
    };
    agents.push(agent);
    materializePresetForAgent(world.id, agent.id, preset);
  }

  sendJson(response, 201, world);
}

async function handleWorldCompositionValidate(request, response) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  if (!isPlatformAdmin(currentSubject)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method !== "POST") {
    sendJson(response, 405, { detail: "method not allowed" });
    return;
  }

  const body = await readJson(request);
  const issues = [];
  if (worlds.some((world) => world.slug === body.slug)) {
    issues.push({
      severity: "blocking",
      code: "slug_collision",
      field: "slug",
      message: "World slug already exists.",
    });
  }
  for (const presetReference of body.composition?.preset_references ?? []) {
    if (!agentPresets.some((preset) => preset.preset_key === presetReference.preset_key)) {
      issues.push({
        severity: "blocking",
        code: "missing_preset",
        field: "composition.preset_references",
        message: `Unknown agent preset: ${presetReference.preset_key}.`,
      });
    }
  }
  sendJson(response, 200, {
    valid: issues.length === 0,
    blocking_issue_count: issues.length,
    warning_issue_count: 0,
    issues,
  });
}

async function handleProviderProfileItem(request, response, profileId, action) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const profile = providerProfiles.find((item) => item.id === profileId);
  if (profile === undefined) {
    sendJson(response, 404, { detail: "Provider profile not found" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === "test-call") {
    profile.last_tested_at = new Date().toISOString();
    profile.last_test_status = "success";
    profile.last_test_error = null;
    sendJson(response, 200, {
      status: "success",
      latency_ms: 5,
      text_preview: "OK",
      error_code: null,
      error_message: null,
    });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(profile, await readJson(request));
    sendJson(response, 200, profile);
    return;
  }
  if (request.method === "DELETE") {
    profile.is_enabled = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleMemoryBackendProfileItem(request, response, profileId, action) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const profile = memoryBackendProfiles.find((item) => item.id === profileId);
  if (profile === undefined) {
    sendJson(response, 404, { detail: "Memory backend profile not found" });
    return;
  }
  if (request.method === "GET" && action === "health") {
    sendJson(response, 200, {
      backend: "builtin.mem0_oss_memory",
      status: "ok",
      details: { profile_key: profile.profile_key },
    });
    return;
  }
  if (request.method === "GET" && action === "logs") {
    sendJson(response, 200, {
      write_logs: memoryWriteLogs.filter(
        (entry) => entry.correlation_ids.world_id === worldOneId,
      ),
      retrieval_logs: memoryRetrievalLogs.filter(
        (entry) => entry.backend_profile_id === profile.id,
      ),
    });
    return;
  }
  if (request.method === "GET" && action === "jobs") {
    sendJson(response, 200, {
      jobs: memoryWriteJobs.filter((entry) => entry.backend_profile_id === profile.id),
    });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === "eval-smoke") {
    sendJson(response, 200, {
      backend: "builtin.mem0_oss_memory",
      case_count: 1,
      hit_case_count: 1,
      average_latency_ms: 5,
      average_context_items: 1,
      cases: [
        {
          label: "smoke",
          query_text: "guide context",
          backend: "builtin.mem0_oss_memory",
          hit_count: 1,
          context_item_count: 1,
          latency_ms: 5,
        },
      ],
    });
    return;
  }
  if (request.method === "PATCH" && action === undefined) {
    Object.assign(profile, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, profile);
    return;
  }
  if (request.method === "DELETE" && action === undefined) {
    profile.is_enabled = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleMemoryWriteJobItem(request, response, jobId, action) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const job = memoryWriteJobs.find((item) => item.id === jobId);
  if (job === undefined) {
    sendJson(response, 404, { detail: "Memory write job not found" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === "retry") {
    job.status = "pending";
    job.next_attempt_at = new Date().toISOString();
    job.last_error = null;
    job.processed_at = null;
    job.updated_at = new Date().toISOString();
    sendJson(response, 200, job);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleMemory(request, response, currentSubject, worldId, agentId, memoryId, action) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && memoryId === undefined) {
    sendJson(
      response,
      200,
      memoryItems.filter((item) => item.world_id === worldId && item.agent_id === agentId),
    );
    return;
  }
  if (request.method === "POST" && memoryId === "search") {
    const body = await readJson(request);
    const limit = Number.isFinite(Number(body.limit)) ? Number(body.limit) : 10;
    sendJson(
      response,
      200,
      memoryItems
        .filter((item) => item.world_id === worldId && item.agent_id === agentId)
        .filter((item) =>
          typeof body.query_text === "string" && body.query_text.trim() !== ""
            ? item.content.toLowerCase().includes(body.query_text.toLowerCase())
            : true,
        )
        .map((item, index) => ({ ...item, score: 1 - index * 0.1 }))
        .slice(0, limit),
    );
    return;
  }
  if (request.method === "GET" && memoryId === "profile-snapshot") {
    sendJson(response, 200, memoryProfileSnapshots.get(agentId) ?? null);
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && memoryId === "profile-snapshot" && action === "refresh") {
    const snapshot = {
      id: memoryProfileSnapshots.get(agentId)?.id ?? randomUUID(),
      world_id: worldId,
      agent_id: agentId,
      aliases: ["Guide"],
      identity_notes: ["Resident guide for the first world."],
      durable_preferences: ["Keeps replies concise."],
      long_lived_goals: ["Help operators move the scene forward."],
      language_style_preferences: ["Direct and calm."],
      refreshed_at: new Date().toISOString(),
      created_at: memoryProfileSnapshots.get(agentId)?.created_at ?? new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    memoryProfileSnapshots.set(agentId, snapshot);
    sendJson(response, 200, snapshot);
    return;
  }
  if (request.method === "POST" && memoryId === "forget") {
    const retained = memoryItems.filter(
      (item) => !(item.world_id === worldId && item.agent_id === agentId),
    );
    memoryItems.length = 0;
    memoryItems.push(...retained);
    memoryProfileSnapshots.delete(agentId);
    sendJson(response, 200, {
      backend: "builtin.mem0_oss_memory",
      deleted_count: null,
    });
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handlePersona(request, response, currentSubject, worldId, agentId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, agentPersonas.get(agentId) ?? null);
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PATCH") {
    const body = await readJson(request);
    const persona = {
      id: agentPersonas.get(agentId)?.id ?? randomUUID(),
      world_id: worldId,
      agent_id: agentId,
      persona_text: body.persona_text ?? "",
      behavior_policy: body.behavior_policy ?? {},
      policy_plugin_identifier: body.policy_plugin_identifier ?? "builtin.default_persona_policy",
      policy_plugin_config: body.policy_plugin_config ?? {},
      is_enabled: body.is_enabled ?? true,
      created_at: agentPersonas.get(agentId)?.created_at ?? new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    agentPersonas.set(agentId, persona);
    sendJson(response, 200, persona);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleObservations(request, response, currentSubject, worldId, agentId, action) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && action === undefined) {
    sendJson(response, 200, observationsFor(worldId, agentId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === undefined) {
    const body = await readJson(request);
    const observation = {
      id: randomUUID(),
      world_id: worldId,
      agent_id: agentId,
      source_event_id: null,
      observation_type: body.observation_type ?? "manual",
      content: body.content,
      metadata: body.metadata ?? {},
      observed_at: body.observed_at ?? new Date().toISOString(),
      consumed_at: null,
      created_at: new Date().toISOString(),
    };
    agentObservations.unshift(observation);
    sendJson(response, 201, observation);
    return;
  }
  if (request.method === "POST" && action === "refresh") {
    if (!agentObservations.some((item) => item.agent_id === agentId && item.source_event_id === "event-clock-1")) {
      agentObservations.unshift({
        id: randomUUID(),
        world_id: worldId,
        agent_id: agentId,
        source_event_id: "event-clock-1",
        observation_type: "world.clock_advanced",
        content: "World clock advanced.",
        metadata: {},
        observed_at: new Date().toISOString(),
        consumed_at: null,
        created_at: new Date().toISOString(),
      });
    }
    sendJson(response, 200, observationsFor(worldId, agentId));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleAgentRuns(request, response, currentSubject, worldId, agentId) {
  if (!canReadWorld(currentSubject, worldId)) {
    sendJson(response, 404, { detail: "World not found" });
    return;
  }
  if (request.method === "GET") {
    sendJson(
      response,
      200,
      agentRuns.filter((run) => run.world_id === worldId && run.agent_id === agentId),
    );
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAgentRun(request, response, currentSubject, worldId, agentId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST") {
    const body = await readJson(request);
    const run = {
      run_id: randomUUID(),
      world_id: worldId,
      agent_id: agentId,
      status: "succeeded",
      prompt_text: body.prompt ?? "Manual run",
      response_text: `Run output for ${agentId}`,
      provider_profile_id: body.provider_profile_id ?? providerProfiles[0]?.id ?? null,
      diagnostics: {
        persona_enabled: agentPersonas.get(agentId)?.is_enabled ?? false,
        observation_count: observationsFor(worldId, agentId).length,
      },
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
    };
    agentRuns.unshift(run);
    if (body.create_memory !== false) {
      memoryItems.unshift({
        id: randomUUID(),
        world_id: worldId,
        agent_id: agentId,
        content: run.response_text,
        metadata: { run_id: run.run_id },
        backend: "builtin.mem0_oss_memory",
        created_at: new Date().toISOString(),
        score: null,
      });
    }
    if (body.create_narrative_artifact !== false) {
      narrativeArtifacts.unshift({
        id: randomUUID(),
        world_id: worldId,
        agent_id: agentId,
        source_run_id: run.run_id,
        source_conversation_id: null,
        title: "Runtime note",
        content: run.response_text,
        artifact_kind: "agent_note",
        metadata: {},
        created_at: new Date().toISOString(),
        publication: null,
      });
    }
    sendJson(response, 201, run);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleCalendar(request, response, currentSubject, worldId, agentId, entryId) {
  if (request.method === "GET" && entryId === undefined) {
    sendJson(
      response,
      200,
      calendarEntries.filter((entry) => entry.world_id === worldId && entry.agent_id === agentId),
    );
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && entryId === undefined) {
    const body = await readJson(request);
    const entry = {
      id: randomUUID(),
      world_id: worldId,
      agent_id: agentId,
      title: body.title,
      description: body.description ?? null,
      starts_at: new Date(body.starts_at).toISOString(),
      ends_at: body.ends_at === undefined || body.ends_at === null ? null : new Date(body.ends_at).toISOString(),
      recurrence_rule: body.recurrence_rule ?? null,
      status: "active",
      metadata: body.metadata ?? {},
    };
    calendarEntries.push(entry);
    sendJson(response, 201, entry);
    return;
  }
  const entry = calendarEntries.find((item) => item.id === entryId && item.world_id === worldId);
  if (entry === undefined) {
    sendJson(response, 404, { detail: "Calendar entry not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(entry, await readJson(request));
    sendJson(response, 200, entry);
    return;
  }
  if (request.method === "DELETE") {
    entry.status = "cancelled";
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleScheduleRules(request, response, currentSubject, worldId, ruleId) {
  if (request.method === "GET" && ruleId === undefined) {
    sendJson(response, 200, scheduleRules.filter((rule) => rule.world_id === worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && ruleId === "preview") {
    const body = await readJson(request);
    sendJson(response, 200, scheduleRulePreview(worldId, body));
    return;
  }
  if (request.method === "POST" && ruleId === undefined) {
    const body = await readJson(request);
    if (scheduleRules.some((rule) => rule.world_id === worldId && rule.rule_key === body.rule_key)) {
      sendJson(response, 409, { detail: "Schedule rule key already exists" });
      return;
    }
    const rule = {
      id: randomUUID(),
      world_id: worldId,
      rule_key: body.rule_key,
      name: body.name,
      kind: body.kind,
      config: body.config ?? {},
      is_enabled: true,
    };
    scheduleRules.push(rule);
    sendJson(response, 201, rule);
    return;
  }
  const rule = scheduleRules.find((item) => item.id === ruleId && item.world_id === worldId);
  if (rule === undefined) {
    sendJson(response, 404, { detail: "Schedule rule not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(rule, await readJson(request));
    sendJson(response, 200, rule);
    return;
  }
  if (request.method === "DELETE") {
    rule.is_enabled = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function scheduleRulePreview(worldId, body) {
  const baseTime = new Date(body.start_world_time ?? projectClock(clocks.get(worldId) ?? clockForWorld(worldId)).effective_world_time);
  const horizonHours = Number(body.horizon_hours ?? 48);
  const limit = Number(body.limit ?? 10);
  const affectedAgentIds = agents
    .filter((agent) => agent.world_id === worldId && agent.is_enabled)
    .map((agent) => agent.id);
  const matches = [];
  let matchCount = 0;
  for (let offset = 0; offset <= horizonHours; offset += 1) {
    const worldTime = new Date(baseTime.getTime() + offset * 60 * 60 * 1000);
    const reason = scheduleRuleMatchReason(body.kind, body.config ?? {}, worldTime);
    if (reason === null) {
      continue;
    }
    matchCount += 1;
    if (matches.length < limit) {
      matches.push({
        world_time: worldTime.toISOString(),
        reason,
        affected_agent_count: affectedAgentIds.length,
        affected_agent_ids: affectedAgentIds,
      });
    }
  }
  return {
    world_id: worldId,
    kind: body.kind,
    config: body.config ?? {},
    start_world_time: baseTime.toISOString(),
    horizon_hours: horizonHours,
    match_count: matchCount,
    affected_agent_count: affectedAgentIds.length,
    affected_agent_ids: affectedAgentIds,
    matches,
  };
}

function scheduleRuleMatchReason(kind, config, worldTime) {
  if (kind === "weekday" && worldTime.getUTCDay() >= 1 && worldTime.getUTCDay() <= 5) {
    return "weekday";
  }
  if (kind === "weekend" && (worldTime.getUTCDay() === 0 || worldTime.getUTCDay() === 6)) {
    return "weekend";
  }
  if (kind === "timetable" && Array.isArray(config.hours) && config.hours.includes(worldTime.getUTCHours())) {
    return `hour ${worldTime.getUTCHours()}`;
  }
  return null;
}

async function handleMemberships(request, response, currentSubject, worldId, userId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && userId === undefined) {
    sendJson(response, 200, memberships.filter((item) => item.world_id === worldId).map(expandMembership));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PUT" && userId !== undefined) {
    const body = await readJson(request);
    let currentMembership = membershipFor(worldId, userId);
    if (currentMembership === undefined) {
      currentMembership = membership(randomUUID(), worldId, userId, body.role);
      memberships.push(currentMembership);
    } else {
      currentMembership.role = body.role;
    }
    sendJson(response, 200, expandMembership(currentMembership));
    return;
  }
  if (request.method === "DELETE" && userId !== undefined) {
    const currentMembership = membershipFor(worldId, userId);
    if (currentMembership === undefined) {
      sendJson(response, 404, { detail: "Membership not found" });
      return;
    }
    const adminCount = memberships.filter(
      (item) => item.world_id === worldId && item.role === "world_admin",
    ).length;
    if (currentMembership.role === "world_admin" && adminCount <= 1) {
      sendJson(response, 409, { detail: "Cannot remove the final world admin" });
      return;
    }
    memberships.splice(memberships.indexOf(currentMembership), 1);
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleMemberCandidates(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const query = (url.searchParams.get("query") ?? "").toLowerCase();
  const limit = Math.min(Number(url.searchParams.get("limit") ?? "20"), 50);
  const candidates = users
    .filter((item) => item.is_active)
    .filter(
      (item) =>
        query === ""
        || item.email.toLowerCase().includes(query)
        || item.display_name.toLowerCase().includes(query),
    )
    .slice(0, limit)
    .map((item) => ({ ...item, role: membershipFor(worldId, item.id)?.role ?? null }));
  sendJson(response, 200, candidates);
}

async function handleClock(request, response, currentSubject, worldId, action) {
  const currentClock = clocks.get(worldId) ?? clockForWorld(worldId);
  clocks.set(worldId, currentClock);
  if (request.method === "GET" && action === undefined) {
    sendJson(response, 200, projectClock(currentClock));
    return;
  }
  if (request.method === "GET" && action === "transitions") {
    if (!canManageWorld(currentSubject, worldId)) {
      sendJson(response, 403, { detail: "Forbidden" });
      return;
    }
    sendJson(response, 200, clockTransitionsForWorld(worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  const body = await readJson(request);
  const nextClock = projectClock(currentClock);
  nextClock.revision += 1;
  if (action === "pause") {
    nextClock.status = "paused";
    nextClock.current_world_time = nextClock.effective_world_time;
    nextClock.wall_time_anchor = null;
  } else if (action === "resume") {
    nextClock.status = "running";
    nextClock.wall_time_anchor = new Date().toISOString();
    nextClock.speed_multiplier = String(body.speed_multiplier ?? nextClock.speed_multiplier);
  } else if (action === "advance") {
    nextClock.current_world_time = nextClock.effective_world_time;
    nextClock.wall_time_anchor = nextClock.status === "running" ? new Date().toISOString() : null;
  } else if (action === "skip") {
    nextClock.current_world_time = new Date(body.target_world_time).toISOString();
    nextClock.effective_world_time = nextClock.current_world_time;
    nextClock.wall_time_anchor = nextClock.status === "running" ? new Date().toISOString() : null;
  } else {
    sendJson(response, 404, { detail: "not found" });
    return;
  }
  clocks.set(worldId, nextClock);
  appendClockTransition(worldId, currentClock, nextClock, action, currentSubject, body.reason);
  sendJson(response, 200, nextClock);
}

function handleReplay(request, response, worldId, action) {
  if (request.method === "GET" && action === "state") {
    sendJson(response, 200, replayForWorld(worldId));
    return;
  }
  sendJson(response, 404, { detail: "not found" });
}

async function handleSnapshots(request, response, currentSubject, worldId, action) {
  if (request.method === "GET" && action === "latest") {
    sendJson(response, 200, snapshots.get(worldId) ?? null);
    return;
  }
  if (request.method === "GET" && action === "integrity") {
    if (!canManageWorld(currentSubject, worldId)) {
      sendJson(response, 403, { detail: "Forbidden" });
      return;
    }
    sendJson(response, 200, snapshotIntegrityForWorld(worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === undefined) {
    const replay = replayForWorld(worldId);
    const snapshot = {
      id: randomUUID(),
      world_id: worldId,
      covers_event_sequence: replay.source_sequence,
      schema_version: "world_state.v1",
      status: "valid",
      payload: replay,
      payload_uri: null,
      metadata: { source: "mock" },
      created_by_event_id: randomUUID(),
      created_at: new Date().toISOString(),
    };
    snapshots.set(worldId, snapshot);
    replaySequences.set(worldId, replay.source_sequence + 1);
    appendWorldEvent(worldId, {
      event_name: "world.snapshot_created",
      payload: {
        covers_event_sequence: snapshot.covers_event_sequence,
        schema_version: snapshot.schema_version,
        status: snapshot.status,
        payload_uri: snapshot.payload_uri,
      },
      actor_ref: `user:${currentSubject.user_id}`,
    });
    sendJson(response, 201, snapshot);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleWorldEvents(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method !== "GET") {
    sendJson(response, 405, { detail: "method not allowed" });
    return;
  }
  const limit = Math.min(Number(url.searchParams.get("limit") ?? "50"), 100);
  let events = [...(worldEvents.get(worldId) ?? [])];
  const eventName = url.searchParams.get("event_name");
  const actorRef = url.searchParams.get("actor_ref");
  const sequenceAfter = url.searchParams.get("sequence_after");
  const sequenceBefore = url.searchParams.get("sequence_before");
  const wallTimeFrom = url.searchParams.get("wall_time_from");
  const wallTimeTo = url.searchParams.get("wall_time_to");
  if (eventName !== null) {
    events = events.filter((event) => event.event_name === eventName);
  }
  if (actorRef !== null) {
    events = events.filter((event) => event.actor_ref === actorRef);
  }
  if (sequenceAfter !== null) {
    events = events.filter((event) => event.sequence > Number(sequenceAfter));
  }
  if (sequenceBefore !== null) {
    events = events.filter((event) => event.sequence < Number(sequenceBefore));
  }
  if (wallTimeFrom !== null) {
    events = events.filter((event) => event.wall_time >= wallTimeFrom);
  }
  if (wallTimeTo !== null) {
    events = events.filter((event) => event.wall_time <= wallTimeTo);
  }
  sendJson(
    response,
    200,
    events.sort((left, right) => right.sequence - left.sequence).slice(0, limit),
  );
}

async function handleNarrativeArtifacts(request, response, currentSubject, worldId, artifactId, url) {
  if (!canReadWorld(currentSubject, worldId)) {
    sendJson(response, 404, { detail: "World not found" });
    return;
  }
  if (request.method === "GET" && artifactId !== undefined) {
    const artifact = narrativeArtifacts.find(
      (item) => item.id === artifactId && item.world_id === worldId,
    );
    if (
      artifact === undefined
      || (!canManageWorld(currentSubject, worldId) && !isReaderVisibleArtifact(artifact))
    ) {
      sendJson(response, 404, { detail: "Narrative artifact not found" });
      return;
    }
    sendJson(response, 200, artifact);
    return;
  }
  if (request.method === "GET") {
    const artifactKind = url.searchParams.get("artifact_kind");
    const sourceConversationId = url.searchParams.get("source_conversation_id");
    const limitValue = Number.parseInt(url.searchParams.get("limit") ?? "", 10);
    let items = narrativeArtifacts
      .filter((artifact) => artifact.world_id === worldId)
      .sort((left, right) => right.created_at.localeCompare(left.created_at));
    if (!canManageWorld(currentSubject, worldId)) {
      items = items.filter(isReaderVisibleArtifact);
    }
    if (artifactKind !== null && artifactKind !== "") {
      items = items.filter((artifact) => artifact.artifact_kind === artifactKind);
    }
    if (sourceConversationId !== null && sourceConversationId !== "") {
      items = items.filter((artifact) => artifact.source_conversation_id === sourceConversationId);
    }
    if (Number.isFinite(limitValue) && limitValue > 0) {
      items = items.slice(0, limitValue);
    }
    sendJson(response, 200, items);
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (artifactId !== undefined && segmentsForArtifactAction(url).includes("publish")) {
    const artifact = narrativeArtifacts.find(
      (item) => item.id === artifactId && item.world_id === worldId,
    );
    if (artifact === undefined) {
      sendJson(response, 404, { detail: "Narrative artifact not found" });
      return;
    }
    const body = await readJson(request);
    const now = new Date().toISOString();
    artifact.publication = {
      id: artifact.publication?.id ?? randomUUID(),
      world_id: worldId,
      artifact_id: artifact.id,
      source_draft_id: artifact.id,
      status: "published",
      reader_visible: body.reader_visible ?? true,
      metadata: body.metadata ?? artifact.publication?.metadata ?? {},
      published_at: now,
      unpublished_at: null,
      published_by_user_id: currentSubject.user_id,
      created_at: artifact.publication?.created_at ?? now,
      updated_at: now,
    };
    sendJson(response, 200, artifact.publication);
    return;
  }
  if (artifactId !== undefined && segmentsForArtifactAction(url).includes("unpublish")) {
    const artifact = narrativeArtifacts.find(
      (item) => item.id === artifactId && item.world_id === worldId,
    );
    if (artifact === undefined || artifact.publication === null) {
      sendJson(response, 404, { detail: "Narrative publication not found" });
      return;
    }
    const body = await readJson(request);
    artifact.publication = {
      ...artifact.publication,
      status: "unpublished",
      reader_visible: false,
      metadata: { ...artifact.publication.metadata, ...(body.metadata ?? {}) },
      unpublished_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    sendJson(response, 200, artifact.publication);
    return;
  }
  if (request.method === "POST") {
    const body = await readJson(request);
    const artifact = {
      id: randomUUID(),
      world_id: worldId,
      agent_id: body.agent_id ?? null,
      source_run_id: null,
      source_conversation_id: null,
      title: body.title,
      content: body.content,
      artifact_kind: body.artifact_kind ?? "world_summary",
      metadata: {},
      created_at: new Date().toISOString(),
      publication: null,
    };
    narrativeArtifacts.unshift(artifact);
    sendJson(response, 201, artifact);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleConversations(request, response, currentSubject, worldId, conversationId, action) {
  if (request.method === "GET" && conversationId === undefined) {
    sendJson(response, 200, conversations.filter((item) => item.world_id === worldId));
    return;
  }

  if (conversationId === undefined) {
    if (!canManageWorld(currentSubject, worldId)) {
      sendJson(response, 403, { detail: "Forbidden" });
      return;
    }
    if (!hasValidCsrf(request)) {
      sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
      return;
    }
    if (request.method === "POST") {
      const body = await readJson(request);
      const now = new Date().toISOString();
      const session = {
        id: randomUUID(),
        world_id: worldId,
        scene_id: body.scene_id ?? null,
        session_key: body.session_key,
        title: body.title,
        scope_type: body.scope_type,
        mode: body.mode,
        status: "draft",
        objective: body.objective ?? "",
        opening_prompt: body.opening_prompt ?? "",
        max_turns: body.max_turns ?? 12,
        next_turn_index: 0,
        policy: body.policy,
        writer_config: body.writer_config ?? {
          provider_profile_id: null,
          writer_plugin_identifier: "builtin.default_narrative_writer",
          writer_plugin_config: {},
          auto_generate_on_complete: false,
          generate_summary: true,
          generate_chapter: true,
        },
        memory_config: body.memory_config ?? {
          write_turn_memory: true,
          retrieve_memory: true,
          max_context_items: 5,
          query_window: 4,
        },
        terminal_reason: null,
        created_at: now,
        updated_at: now,
      };
      conversations.push(session);
      sendJson(response, 201, session);
      return;
    }
    sendJson(response, 405, { detail: "method not allowed" });
    return;
  }

  const session = conversations.find((item) => item.id === conversationId && item.world_id === worldId);
  if (session === undefined) {
    sendJson(response, 404, { detail: "Conversation not found" });
    return;
  }

  if (action === undefined && request.method === "GET") {
    sendJson(response, 200, session);
    return;
  }
  if (action === "participants" && request.method === "GET") {
    sendJson(response, 200, participantsForSession(conversationId));
    return;
  }
  if (action === "turns" && request.method === "GET") {
    sendJson(response, 200, turnsForSession(conversationId));
    return;
  }
  if (action === "narrative" && request.method === "GET") {
    sendJson(
      response,
      200,
      narrativeArtifacts
        .filter((item) => item.world_id === worldId && item.source_conversation_id === conversationId)
        .sort((left, right) => right.created_at.localeCompare(left.created_at)),
    );
    return;
  }

  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }

  if (action === undefined && request.method === "PATCH") {
    Object.assign(session, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, session);
    return;
  }
  if (action === "participants" && request.method === "PUT") {
    const body = await readJson(request);
    for (const existing of [...participantsForSession(conversationId)]) {
      conversationParticipants.splice(conversationParticipants.indexOf(existing), 1);
    }
    const now = new Date().toISOString();
    const participants = body.map((item) => ({
      id: randomUUID(),
      session_id: conversationId,
      agent_id: item.agent_id,
      turn_order: item.turn_order,
      is_enabled: item.is_enabled ?? true,
      created_at: now,
      updated_at: now,
    }));
    conversationParticipants.push(...participants);
    sendJson(response, 200, participants);
    return;
  }
  if (action === "seed" && request.method === "POST") {
    const body = await readJson(request);
    const turn = appendConversationTurn(session, {
      speaker_kind: "operator",
      speaker_agent_id: null,
      input_text: body.input_text,
      output_text: body.input_text,
      status: "succeeded",
      run_id: null,
      error_text: null,
    });
    sendJson(response, 201, turn);
    return;
  }
  if (action === "advance" && request.method === "POST") {
    const turn = appendAgentConversationTurn(session);
    if (turn === null) {
      sendJson(response, 409, { detail: "Conversation has no enabled participants" });
      return;
    }
    sendJson(response, 200, { session, turn });
    return;
  }
  if (action === "start" && request.method === "POST") {
    session.status = "running";
    session.updated_at = new Date().toISOString();
    if (session.mode === "auto_dialogue") {
      appendAgentConversationTurn(session);
    }
    sendJson(response, 200, session);
    return;
  }
  if (action === "pause" && request.method === "POST") {
    session.status = "paused";
    session.updated_at = new Date().toISOString();
    sendJson(response, 200, session);
    return;
  }
  if (action === "resume" && request.method === "POST") {
    session.status = "running";
    session.updated_at = new Date().toISOString();
    sendJson(response, 200, session);
    return;
  }
  if (action === "stop" && request.method === "POST") {
    session.status = "stopped";
    session.terminal_reason = "operator_stopped";
    session.updated_at = new Date().toISOString();
    sendJson(response, 200, session);
    return;
  }
  if (action === "narrative" && request.method === "POST") {
    const body = await readJson(request);
    sendJson(response, 200, generateConversationNarrative(session, body.artifact_set));
    return;
  }

  sendJson(response, 405, { detail: "method not allowed" });
}

function appendAgentConversationTurn(session) {
  const participants = participantsForSession(session.id)
    .filter((participant) => participant.is_enabled)
    .sort((left, right) => left.turn_order - right.turn_order);
  if (participants.length === 0) {
    session.status = "failed";
    session.updated_at = new Date().toISOString();
    return null;
  }
  const participant = participants[session.next_turn_index % participants.length];
  const agent = agents.find((item) => item.id === participant.agent_id);
  const previousTurn = turnsForSession(session.id).at(-1);
  const inputText = previousTurn?.output_text ?? session.opening_prompt ?? "Begin.";
  const outputText = `${agent?.display_name ?? "Agent"} replies to: ${inputText}`;
  const runId = randomUUID();
  const run = {
    run_id: runId,
    world_id: session.world_id,
    agent_id: participant.agent_id,
    status: "succeeded",
    prompt_text: inputText,
    response_text: outputText,
    provider_profile_id: agent?.provider_profile_id ?? providerProfiles[0]?.id ?? null,
    diagnostics: { conversation_id: session.id },
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
  };
  agentRuns.unshift(run);
  const turn = appendConversationTurn(session, {
    speaker_kind: "agent",
    speaker_agent_id: participant.agent_id,
    input_text: inputText,
    output_text: outputText,
    status: "succeeded",
    run_id: runId,
    error_text: null,
  });
  if (session.next_turn_index >= session.max_turns) {
    session.status = "completed";
    session.terminal_reason = "max_turns_reached";
    if (session.writer_config?.auto_generate_on_complete) {
      generateConversationNarrative(session, writerArtifactSet(session.writer_config));
    }
  }
  return turn;
}

function appendConversationTurn(session, fields) {
  const now = new Date().toISOString();
  const turn = {
    id: randomUUID(),
    session_id: session.id,
    turn_index: session.next_turn_index,
    created_at: now,
    updated_at: now,
    ...fields,
  };
  conversationTurns.push(turn);
  session.next_turn_index += 1;
  session.updated_at = now;
  return turn;
}

function participantsForSession(sessionId) {
  return conversationParticipants.filter((item) => item.session_id === sessionId);
}

function turnsForSession(sessionId) {
  return conversationTurns
    .filter((item) => item.session_id === sessionId)
    .sort((left, right) => left.turn_index - right.turn_index);
}

function generateConversationNarrative(session, artifactSet) {
  const generated = [];
  const summaryArtifact = findConversationArtifact(session.id, "conversation_summary");
  const chapterArtifact = findConversationArtifact(session.id, "chapter_draft");
  const summaryEnabled = artifactSet === "summary_and_chapter" || artifactSet === "summary_only";
  const chapterEnabled = artifactSet === "summary_and_chapter" || artifactSet === "chapter_only";

  if (summaryEnabled) {
    if (summaryArtifact === undefined) {
      generated.push(
        pushNarrativeArtifact({
          world_id: session.world_id,
          agent_id: null,
          source_run_id: null,
          source_conversation_id: session.id,
          title: `${session.title} summary`,
          content: `Summary for ${session.title}`,
          artifact_kind: "conversation_summary",
          metadata: { generation_mode: "manual" },
        }),
      );
    } else {
      generated.push(summaryArtifact);
    }
  }

  if (chapterEnabled) {
    if (chapterArtifact === undefined) {
      generated.push(
        pushNarrativeArtifact({
          world_id: session.world_id,
          agent_id: null,
          source_run_id: null,
          source_conversation_id: session.id,
          title: `${session.title} chapter draft`,
          content: `Chapter draft for ${session.title}`,
          artifact_kind: "chapter_draft",
          metadata: { generation_mode: "manual" },
        }),
      );
    } else {
      generated.push(chapterArtifact);
    }
  }

  return generated.sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function pushNarrativeArtifact(fields) {
  const artifact = {
    id: randomUUID(),
    created_at: new Date().toISOString(),
    publication: null,
    ...fields,
  };
  narrativeArtifacts.unshift(artifact);
  return artifact;
}

function findConversationArtifact(conversationId, artifactKind) {
  return narrativeArtifacts.find(
    (item) =>
      item.source_conversation_id === conversationId && item.artifact_kind === artifactKind,
  );
}

function writerArtifactSet(writerConfig) {
  if (writerConfig.generate_summary && writerConfig.generate_chapter) {
    return "summary_and_chapter";
  }
  if (writerConfig.generate_summary) {
    return "summary_only";
  }
  if (writerConfig.generate_chapter) {
    return "chapter_only";
  }
  return "summary_only";
}

function materializePresetForAgent(worldId, agentId, preset) {
  if (preset == null) {
    return;
  }
  const currentPersona = agentPersonas.get(agentId);
  agentPersonas.set(agentId, {
    id: currentPersona?.id ?? randomUUID(),
    world_id: worldId,
    agent_id: agentId,
    persona_text: preset.persona_text ?? "",
    behavior_policy: preset.behavior_policy ?? {},
    policy_plugin_identifier:
      currentPersona?.policy_plugin_identifier ?? "builtin.default_persona_policy",
    policy_plugin_config: currentPersona?.policy_plugin_config ?? {},
    is_enabled: true,
    created_at: currentPersona?.created_at ?? new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });
  for (const blueprintEntry of preset.calendar_blueprint ?? []) {
    calendarEntries.push({
      id: randomUUID(),
      world_id: worldId,
      agent_id: agentId,
      title: blueprintEntry.title,
      description: blueprintEntry.description ?? null,
      starts_at: new Date(blueprintEntry.starts_at).toISOString(),
      ends_at:
        blueprintEntry.ends_at == null ? null : new Date(blueprintEntry.ends_at).toISOString(),
      recurrence_rule: blueprintEntry.recurrence_rule ?? null,
      status: "active",
      metadata: blueprintEntry.metadata ?? {},
    });
  }
}

function clockForWorld(worldId) {
  const now = new Date().toISOString();
  return {
    world_id: worldId,
    status: "paused",
    current_world_time: now,
    effective_world_time: now,
    wall_time_anchor: null,
    speed_multiplier: "1",
    revision: 0,
  };
}

function replayForWorld(worldId) {
  const sourceSequence = replaySequences.get(worldId) ?? 0;
  const projectedClock = projectClock(clocks.get(worldId) ?? clockForWorld(worldId));
  return {
    world_id: worldId,
    schema_version: "world_state.v1",
    source_sequence: sourceSequence,
    clock:
      sourceSequence === 0
        ? null
        : {
            status: projectedClock.status,
            current_world_time: projectedClock.current_world_time,
            effective_world_time: projectedClock.effective_world_time,
            wall_time_anchor: projectedClock.wall_time_anchor,
            speed_multiplier: projectedClock.speed_multiplier,
            revision: projectedClock.revision,
            last_event_id: "mock-clock-event",
            last_event_sequence: sourceSequence,
          },
    applied_event_count: sourceSequence === 0 ? 0 : 1,
    unhandled_event_count: 0,
  };
}

function appendWorldEvent(worldId, input) {
  const events = worldEvents.get(worldId) ?? [];
  const event = {
    id: randomUUID(),
    world_id: worldId,
    sequence: events.length + 1,
    event_name: input.event_name,
    payload: input.payload ?? {},
    wall_time: new Date().toISOString(),
    world_time: input.world_time ?? null,
    actor_ref: input.actor_ref ?? "system:mock",
    causation_event_id: null,
    correlation_id: null,
    created_at: new Date().toISOString(),
  };
  events.push(event);
  worldEvents.set(worldId, events);
  return event;
}

function snapshotIntegrityForWorld(worldId) {
  const events = worldEvents.get(worldId) ?? [];
  const latestEventSequence = events.at(-1)?.sequence ?? 0;
  const latestSnapshot = snapshots.get(worldId) ?? null;
  if (latestSnapshot === null) {
    return {
      world_id: worldId,
      status: "warning",
      latest_event_sequence: latestEventSequence,
      latest_snapshot_id: null,
      covers_event_sequence: null,
      schema_version: null,
      event_gap: null,
      issues: ["No valid snapshot exists."],
    };
  }
  const latestReplayEvent = [...events]
    .reverse()
    .find((event) => event.event_name !== "world.snapshot_created");
  const latestReplaySequence =
    latestReplayEvent === undefined
      ? latestSnapshot.covers_event_sequence
      : latestReplayEvent.sequence;
  const eventGap = Math.max(latestReplaySequence - latestSnapshot.covers_event_sequence, 0);
  return {
    world_id: worldId,
    status: eventGap > 0 ? "warning" : "ok",
    latest_event_sequence: latestEventSequence,
    latest_snapshot_id: latestSnapshot.id,
    covers_event_sequence: latestSnapshot.covers_event_sequence,
    schema_version: latestSnapshot.schema_version,
    event_gap: eventGap,
    issues: eventGap > 0 ? ["Snapshot is stale relative to the latest event."] : [],
  };
}

function clockTransitionsForWorld(worldId) {
  return [...(clockTransitions.get(worldId) ?? [])].sort(
    (left, right) => right.new_revision - left.new_revision,
  );
}

function appendClockTransition(worldId, previousClock, nextClock, action, currentSubject, reason) {
  const transitions = clockTransitions.get(worldId) ?? [];
  transitions.push({
    id: randomUUID(),
    world_id: worldId,
    transition_type: action,
    previous_status: previousClock.status,
    new_status: nextClock.status,
    previous_world_time: previousClock.effective_world_time ?? previousClock.current_world_time,
    new_world_time: nextClock.effective_world_time ?? nextClock.current_world_time,
    wall_time: new Date().toISOString(),
    previous_revision: previousClock.revision,
    new_revision: nextClock.revision,
    actor_ref: `user:${currentSubject.user_id}`,
    correlation_id: null,
    reason: reason ?? null,
    created_at: new Date().toISOString(),
  });
  clockTransitions.set(worldId, transitions);
}

function projectClock(clock) {
  if (clock.status !== "running" || clock.wall_time_anchor === null) {
    return { ...clock, effective_world_time: clock.current_world_time };
  }
  const elapsed = Date.now() - new Date(clock.wall_time_anchor).getTime();
  const effectiveTime = new Date(
    new Date(clock.current_world_time).getTime() + elapsed * Number(clock.speed_multiplier),
  ).toISOString();
  return { ...clock, effective_world_time: effectiveTime };
}

function subject(user_id, email, display_name, roles) {
  return { user_id, email, display_name, roles };
}

function user(id, email, display_name) {
  return { id, email, display_name, is_active: true };
}

function membership(id, world_id, user_id, role) {
  return { id, world_id, user_id, role };
}

function expandMembership(currentMembership) {
  return {
    ...currentMembership,
    user: users.find((item) => item.id === currentMembership.user_id),
  };
}

function sessionCookie(token) {
  return `noveland_session=${token}; Path=/; SameSite=Lax; HttpOnly`;
}

function csrfCookie() {
  return `noveland_csrf=${validCsrf}; Path=/; SameSite=Lax`;
}

function subjectForRequest(request) {
  const sessionCookieValue = (request.headers.cookie ?? "")
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith("noveland_session="));
  if (sessionCookieValue === undefined) {
    return null;
  }
  const token = sessionCookieValue.slice("noveland_session=".length);
  return sessionSubjects.get(token) ?? null;
}

function canReadWorld(currentSubject, worldId) {
  return isPlatformAdmin(currentSubject) || membershipFor(worldId, currentSubject.user_id) !== undefined;
}

function canManageWorld(currentSubject, worldId) {
  return (
    isPlatformAdmin(currentSubject)
    || membershipFor(worldId, currentSubject.user_id)?.role === "world_admin"
  );
}

function isReaderVisibleArtifact(artifact) {
  return artifact.publication?.status === "published" && artifact.publication.reader_visible;
}

function segmentsForArtifactAction(url) {
  return url.pathname.split("/").filter(Boolean);
}

function isPlatformAdmin(currentSubject) {
  return currentSubject.roles.includes("platform_admin");
}

function membershipFor(worldId, userId) {
  return memberships.find((item) => item.world_id === worldId && item.user_id === userId);
}

function observationsFor(worldId, agentId) {
  return agentObservations.filter((item) => item.world_id === worldId && item.agent_id === agentId);
}

function hasValidCsrf(request) {
  return hasCookie(request, "noveland_csrf", validCsrf) && request.headers["x-csrf-token"] === validCsrf;
}

function sendJson(response, status, body, setCookie = []) {
  response.writeHead(status, {
    "content-type": "application/json",
    ...(setCookie.length > 0 ? { "set-cookie": setCookie } : {}),
  });
  response.end(JSON.stringify(body));
}

function hasCookie(request, name, expectedValue) {
  return (request.headers.cookie ?? "")
    .split(";")
    .map((cookie) => cookie.trim())
    .some((cookie) => cookie === `${name}=${expectedValue}`);
}

function readJson(request) {
  return new Promise((resolve) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      const rawBody = Buffer.concat(chunks).toString("utf8");
      resolve(rawBody === "" ? {} : JSON.parse(rawBody));
    });
  });
}
