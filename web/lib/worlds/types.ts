export type World = {
  id: string;
  owner_user_id: string;
  slug: string;
  name: string;
  description: string | null;
  rules_config: Record<string, unknown>;
  is_active: boolean;
};

export type Scene = {
  id: string;
  world_id: string;
  scene_key: string;
  name: string;
  description: string | null;
  is_active: boolean;
};

export type WorldRole = "world_admin" | "human_user";

export type UserSummary = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
};

export type Membership = {
  id: string;
  world_id: string;
  user_id: string;
  role: WorldRole;
  user: UserSummary;
};

export type MemberCandidate = UserSummary & {
  role: WorldRole | null;
};

export type AgentKind = "role_agent" | "narrative_agent";

export type Agent = {
  id: string;
  world_id: string;
  home_scene_id: string | null;
  agent_key: string;
  display_name: string;
  kind: AgentKind;
  provider_profile_id: string | null;
  config: Record<string, unknown>;
  is_enabled: boolean;
};

export type ConversationScopeType = "scene" | "world";

export type ConversationMode = "manual_chain" | "auto_dialogue";

export type ConversationSessionStatus =
  | "draft"
  | "running"
  | "paused"
  | "completed"
  | "stopped"
  | "failed";

export type ConversationTurnStatus = "succeeded" | "skipped" | "failed";

export type ConversationErrorPolicy =
  | "fail_session"
  | "skip_turn"
  | "retry_once_then_fail"
  | "retry_once_then_skip";

export type ConversationTerminalReason =
  | "max_turns_reached"
  | "loop_guard_repeated_output"
  | "no_enabled_participants"
  | "consecutive_failures_exceeded"
  | "operator_stopped"
  | "speaker_error";

export type ConversationPolicy = {
  error_policy: ConversationErrorPolicy;
  max_consecutive_failed_turns: number;
  loop_guard_window: number;
  repeat_output_threshold: number;
};

export type ConversationWriterConfig = {
  provider_profile_id: string | null;
  auto_generate_on_complete: boolean;
  generate_summary: boolean;
  generate_chapter: boolean;
};

export type ConversationSession = {
  id: string;
  world_id: string;
  scene_id: string | null;
  session_key: string;
  title: string;
  scope_type: ConversationScopeType;
  mode: ConversationMode;
  status: ConversationSessionStatus;
  objective: string;
  opening_prompt: string;
  max_turns: number;
  next_turn_index: number;
  policy: ConversationPolicy;
  writer_config: ConversationWriterConfig;
  terminal_reason: ConversationTerminalReason | null;
  created_at: string;
  updated_at: string;
};

export type ConversationParticipant = {
  id: string;
  session_id: string;
  agent_id: string;
  turn_order: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type ConversationTurn = {
  id: string;
  session_id: string;
  turn_index: number;
  speaker_kind: "operator" | "agent";
  speaker_agent_id: string | null;
  input_text: string;
  output_text: string | null;
  status: ConversationTurnStatus;
  run_id: string | null;
  error_text: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationAdvanceResult = {
  session: ConversationSession;
  turn: ConversationTurn;
};

export type WorldClock = {
  world_id: string;
  status: "running" | "paused";
  current_world_time: string;
  effective_world_time: string;
  wall_time_anchor: string | null;
  speed_multiplier: string;
  revision: number;
};

export type ReplayClock = {
  status: string;
  current_world_time: string | null;
  effective_world_time: string | null;
  wall_time_anchor: string | null;
  speed_multiplier: string | null;
  revision: number | null;
  last_event_id: string | null;
  last_event_sequence: number | null;
};

export type WorldReplayState = {
  world_id: string;
  schema_version: string;
  source_sequence: number;
  clock: ReplayClock | null;
  applied_event_count: number;
  unhandled_event_count: number;
};

export type WorldSnapshot = {
  id: string;
  world_id: string;
  covers_event_sequence: number;
  schema_version: string;
  status: string;
  payload: Record<string, unknown> | null;
  payload_uri: string | null;
  metadata: Record<string, unknown>;
  created_by_event_id: string;
  created_at: string;
};

export type CalendarEntry = {
  id: string;
  world_id: string;
  agent_id: string;
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string | null;
  recurrence_rule: string | null;
  status: "active" | "cancelled";
  metadata: Record<string, unknown>;
};

export type ScheduleRuleKind = "weekday" | "weekend" | "timetable";

export type ScheduleRule = {
  id: string;
  world_id: string;
  rule_key: string;
  name: string;
  kind: ScheduleRuleKind;
  config: Record<string, unknown>;
  is_enabled: boolean;
};

export type MemoryItem = {
  id: string;
  world_id: string;
  agent_id: string;
  content: string;
  metadata: Record<string, unknown>;
  embedding: number[];
  visibility: "private";
  is_active: boolean;
  source_event_id: string | null;
  score: number | null;
};

export type RuntimeControl = {
  desired_state: "running" | "stopped";
  last_heartbeat_at: string | null;
  last_run_started_at: string | null;
  last_run_finished_at: string | null;
  last_error: string | null;
};

export type RuntimeStatus = RuntimeControl & {
  runtime_loop_interval_seconds: number;
  runtime_batch_limit: number;
};

export type DiagnosticSeverity = "info" | "warning" | "error";

export type DiagnosticComponent =
  | "runtime"
  | "provider"
  | "agent"
  | "conversation"
  | "event_publisher"
  | "api";

export type RuntimeDiagnostic = {
  id: string;
  severity: DiagnosticSeverity;
  component: DiagnosticComponent;
  event_type: string;
  message: string;
  details: Record<string, unknown>;
  occurred_at: string;
  world_id: string | null;
  agent_id: string | null;
  run_id: string | null;
  provider_profile_id: string | null;
  created_at: string;
};

export type RuntimeProviderProfileSummary = {
  id: string;
  profile_key: string;
  name: string;
  provider_type: ProviderType;
  last_tested_at: string | null;
  last_test_status: "success" | "failed" | null;
  last_test_error: string | null;
  is_enabled: boolean;
};

export type StreamEnvelope<TPayload> = {
  cursor: string;
  event_type: string;
  occurred_at: string;
  world_id: string | null;
  conversation_id: string | null;
  payload: TPayload;
};

export type RuntimeStreamPayload = {
  runtime_control?: RuntimeControl;
  runtime_status?: RuntimeStatus;
  diagnostics: RuntimeDiagnostic[];
  provider_profiles: RuntimeProviderProfileSummary[];
};

export type WorldStreamPayload = {
  clock?: WorldClock;
  diagnostics: RuntimeDiagnostic[];
  agent_runs: AgentRun[];
  narrative_artifacts: NarrativeArtifact[];
  conversations: ConversationSession[];
};

export type ConversationStreamPayload = {
  session?: ConversationSession;
  turns: ConversationTurn[];
  diagnostics: RuntimeDiagnostic[];
};

export type ProviderType = "openai_compatible" | "anthropic_compatible";

export type ProviderProfile = {
  id: string;
  profile_key: string;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  model_name: string;
  capabilities: Record<string, unknown>;
  api_key_ref: string;
  timeout_seconds: number;
  retry_attempts: number;
  rate_limit_per_minute: number | null;
  last_tested_at: string | null;
  last_test_status: "success" | "failed" | null;
  last_test_error: string | null;
  is_enabled: boolean;
};

export type ProviderTestCallResult = {
  status: "success" | "failed";
  latency_ms: number;
  text_preview: string | null;
  error_code: string | null;
  error_message: string | null;
};

export type AgentRun = {
  run_id: string;
  world_id: string;
  agent_id: string;
  status: string;
  prompt_text: string;
  response_text: string | null;
  provider_profile_id: string | null;
  diagnostics: Record<string, unknown>;
  started_at: string;
  finished_at: string | null;
};

export type AgentPersona = {
  id: string;
  world_id: string;
  agent_id: string;
  persona_text: string;
  behavior_policy: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type AgentObservation = {
  id: string;
  world_id: string;
  agent_id: string;
  source_event_id: string | null;
  observation_type: string;
  content: string;
  metadata: Record<string, unknown>;
  observed_at: string;
  consumed_at: string | null;
  created_at: string;
};

export type NarrativeArtifactKind =
  | "agent_note"
  | "world_summary"
  | "conversation_summary"
  | "chapter_draft";

export type NarrativeArtifact = {
  id: string;
  world_id: string;
  agent_id: string | null;
  source_run_id: string | null;
  source_conversation_id: string | null;
  title: string;
  content: string;
  artifact_kind: NarrativeArtifactKind;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type WorldDashboardData = {
  worlds: World[];
  selectedWorldId: string | null;
  scenes: Scene[];
  agents: Agent[];
  memberships: Membership[];
  clock: WorldClock | null;
  replayState: WorldReplayState | null;
  latestSnapshot: WorldSnapshot | null;
  selectedAgentId: string | null;
  calendarEntries: CalendarEntry[];
  scheduleRules: ScheduleRule[];
  memoryItems: MemoryItem[];
  agentRuns: AgentRun[];
  agentPersona: AgentPersona | null;
  agentObservations: AgentObservation[];
  narrativeArtifacts: NarrativeArtifact[];
  providerProfiles: ProviderProfile[];
  runtimeControl: RuntimeControl | null;
  runtimeStatus: RuntimeStatus | null;
  runtimeDiagnostics: RuntimeDiagnostic[];
  worldDiagnostics: RuntimeDiagnostic[];
  canManageSelectedWorld: boolean;
  loadError: string | null;
};

export type WorldCreateInput = {
  slug: string;
  name: string;
  description?: string | null;
  rules_config?: Record<string, unknown>;
};

export type WorldUpdateInput = {
  name?: string;
  description?: string | null;
  rules_config?: Record<string, unknown>;
  is_active?: boolean;
};

export type SceneCreateInput = {
  scene_key: string;
  name: string;
  description?: string | null;
};

export type SceneUpdateInput = {
  name?: string;
  description?: string | null;
  is_active?: boolean;
};

export type AgentCreateInput = {
  agent_key: string;
  display_name: string;
  kind: AgentKind;
  home_scene_id?: string | null;
  provider_profile_id?: string | null;
  config?: Record<string, unknown>;
};

export type AgentUpdateInput = {
  display_name?: string;
  kind?: AgentKind;
  home_scene_id?: string | null;
  provider_profile_id?: string | null;
  config?: Record<string, unknown>;
  is_enabled?: boolean;
};

export type ConversationCreateInput = {
  session_key: string;
  title: string;
  scope_type: ConversationScopeType;
  mode: ConversationMode;
  scene_id?: string | null;
  objective?: string;
  opening_prompt?: string;
  max_turns?: number;
  policy: ConversationPolicy;
  writer_config: ConversationWriterConfig;
};

export type ConversationUpdateInput = {
  title?: string;
  objective?: string;
  opening_prompt?: string;
  max_turns?: number;
  policy?: ConversationPolicy;
  writer_config?: ConversationWriterConfig;
};

export type ConversationParticipantInput = {
  agent_id: string;
  turn_order: number;
  is_enabled?: boolean;
};

export type ConversationSeedInput = {
  input_text: string;
};

export type CalendarEntryCreateInput = {
  title: string;
  description?: string | null;
  starts_at: string;
  ends_at?: string | null;
  recurrence_rule?: string | null;
  metadata?: Record<string, unknown>;
};

export type CalendarEntryUpdateInput = {
  title?: string;
  description?: string | null;
  starts_at?: string;
  ends_at?: string | null;
  recurrence_rule?: string | null;
  status?: "active" | "cancelled";
  metadata?: Record<string, unknown>;
};

export type ScheduleRuleCreateInput = {
  rule_key: string;
  name: string;
  kind: ScheduleRuleKind;
  config?: Record<string, unknown>;
};

export type ScheduleRuleUpdateInput = {
  name?: string;
  kind?: ScheduleRuleKind;
  config?: Record<string, unknown>;
  is_enabled?: boolean;
};

export type MemoryItemCreateInput = {
  content: string;
  embedding: number[];
  metadata?: Record<string, unknown>;
  source_event_id?: string | null;
};

export type MemorySearchInput = {
  embedding: number[];
  limit?: number;
};

export type RuntimeControlUpdateInput = {
  desired_state: "running" | "stopped";
};

export type ProviderProfileCreateInput = {
  profile_key: string;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  model_name: string;
  capabilities?: Record<string, unknown>;
  api_key_ref: string;
  timeout_seconds?: number;
  retry_attempts?: number;
  rate_limit_per_minute?: number | null;
};

export type ProviderProfileUpdateInput = {
  name?: string;
  base_url?: string;
  model_name?: string;
  capabilities?: Record<string, unknown>;
  api_key_ref?: string;
  timeout_seconds?: number;
  retry_attempts?: number;
  rate_limit_per_minute?: number | null;
  is_enabled?: boolean;
};

export type AgentRunCreateInput = {
  prompt?: string;
  provider_profile_id?: string | null;
  create_memory?: boolean;
  create_narrative_artifact?: boolean;
};

export type AgentPersonaUpdateInput = {
  persona_text: string;
  behavior_policy?: Record<string, unknown>;
  is_enabled?: boolean;
};

export type AgentObservationCreateInput = {
  observation_type?: string;
  content: string;
  metadata?: Record<string, unknown>;
  observed_at?: string | null;
};

export type NarrativeArtifactCreateInput = {
  title: string;
  content: string;
  artifact_kind?: NarrativeArtifactKind;
  agent_id?: string | null;
};

export type ConversationNarrativeArtifactSet =
  | "summary_and_chapter"
  | "summary_only"
  | "chapter_only";
