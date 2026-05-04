export type World = {
  id: string;
  owner_user_id: string;
  slug: string;
  name: string;
  description: string | null;
  rules_config: Record<string, unknown>;
  memory_backend_profile_id: string | null;
  memory_plugin_identifier: string;
  memory_plugin_config: Record<string, unknown>;
  world_rules_plugin_identifier: string;
  world_rules_plugin_config: Record<string, unknown>;
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
  source_preset_id: string | null;
  agent_key: string;
  display_name: string;
  kind: AgentKind;
  provider_profile_id: string | null;
  config: Record<string, unknown>;
  is_enabled: boolean;
};

export type AgentPresetCalendarEntry = {
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string | null;
  recurrence_rule: string | null;
  metadata: Record<string, unknown>;
};

export type AgentPreset = {
  id: string;
  preset_key: string;
  name: string;
  description: string | null;
  default_kind: AgentKind;
  default_provider_profile_key: string | null;
  persona_text: string;
  behavior_policy: Record<string, unknown>;
  calendar_blueprint: AgentPresetCalendarEntry[];
  advanced_config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorldCompositionWorld = {
  slug: string;
  name: string;
  description: string | null;
  rules_config: Record<string, unknown>;
  is_active: boolean;
};

export type WorldCompositionScene = {
  scene_key: string;
  name: string;
  description: string | null;
  is_active: boolean;
};

export type WorldCompositionAgent = {
  agent_key: string;
  display_name: string;
  kind: AgentKind;
  home_scene_key: string | null;
  source_preset_key: string | null;
  provider_profile_key: string | null;
  config: Record<string, unknown>;
  is_enabled: boolean;
};

export type WorldCompositionScheduleRule = {
  rule_key: string;
  name: string;
  kind: ScheduleRuleKind;
  config: Record<string, unknown>;
  is_enabled: boolean;
};

export type WorldCompositionPresetReference = {
  preset_key: string;
  name: string;
  default_kind: AgentKind;
  default_provider_profile_key: string | null;
  is_active: boolean;
};

export type WorldCompositionExport = {
  world: WorldCompositionWorld;
  scenes: WorldCompositionScene[];
  agents: WorldCompositionAgent[];
  schedule_rules: WorldCompositionScheduleRule[];
  preset_references: WorldCompositionPresetReference[];
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

export type ConversationSpeakerPolicy =
  | "round_robin"
  | "least_recent"
  | "priority_order"
  | "manual_next";

export type ConversationPolicy = {
  error_policy: ConversationErrorPolicy;
  max_consecutive_failed_turns: number;
  loop_guard_window: number;
  repeat_output_threshold: number;
  speaker_policy: ConversationSpeakerPolicy;
  manual_next_agent_id: string | null;
  participant_repeat_cooldown: number;
  min_enabled_participants: number;
  max_turn_budget: number | null;
};

export type ConversationSpeakerCandidate = {
  agent_id: string;
  display_name: string;
  turn_order: number;
  is_enabled: boolean;
  score: number;
  reasons: string[];
  last_spoke_turn_index: number | null;
};

export type ConversationSpeakerPreview = {
  session_id: string;
  policy_mode: ConversationSpeakerPolicy;
  selected_agent_id: string | null;
  selected_reason: string;
  candidates: ConversationSpeakerCandidate[];
};

export type ConversationWriterConfig = {
  provider_profile_id: string | null;
  writer_plugin_identifier: string;
  writer_plugin_config: Record<string, unknown>;
  auto_generate_on_complete: boolean;
  generate_summary: boolean;
  generate_chapter: boolean;
  style_guide: string;
  target_length: "brief" | "standard" | "expanded";
  source_constraints: string;
  include_prompt_preview: boolean;
};

export type ConversationNarrativePromptPreview = {
  world_id: string;
  conversation_id: string;
  artifact_set: ConversationNarrativeArtifactSet;
  provider_profile_id: string;
  provider_profile_key: string;
  writer_plugin_identifier: string;
  prompt_text: string;
  source_turn_count: number;
  existing_artifact_count: number;
  warnings: string[];
};

export type ConversationMemoryConfig = {
  write_turn_memory: boolean;
  retrieve_memory: boolean;
  max_context_items: number;
  query_window: number;
  include_recent_turns: boolean;
  include_agent_observations: boolean;
  memory_query_strategy: "prompt" | "objective" | "transcript";
};

export type ConversationMemorySummary = ConversationMemoryConfig & {
  latest_backend: string | null;
  latest_hit_count: number;
  latest_retrieval_enabled: boolean;
  latest_write_enabled: boolean;
  recent_memory_diagnostics: RuntimeDiagnostic[];
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
  memory_config: ConversationMemoryConfig;
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

export type ConversationDiagnosticsSummary = {
  session_status: ConversationSessionStatus;
  terminal_reason: ConversationTerminalReason | null;
  last_turn_status: ConversationTurnStatus | null;
  last_turn_error: string | null;
  provider_diagnostic_count: number;
  memory_diagnostic_count: number;
  recent_diagnostics: RuntimeDiagnostic[];
  operator_message: string;
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

export type WorldClockTransition = {
  id: string;
  world_id: string;
  transition_type: string;
  previous_status: string | null;
  new_status: string;
  previous_world_time: string | null;
  new_world_time: string;
  wall_time: string;
  previous_revision: number | null;
  new_revision: number;
  actor_ref: string | null;
  correlation_id: string | null;
  reason: string | null;
  created_at: string;
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

export type WorldSnapshotIntegrity = {
  world_id: string;
  status: "ok" | "warning" | "error";
  latest_event_sequence: number;
  latest_snapshot_id: string | null;
  covers_event_sequence: number | null;
  schema_version: string | null;
  event_gap: number | null;
  issues: string[];
};

export type WorldEventAuditEntry = {
  id: string;
  world_id: string;
  sequence: number;
  event_name: string;
  payload: Record<string, unknown>;
  wall_time: string;
  world_time: string | null;
  actor_ref: string;
  causation_event_id: string | null;
  correlation_id: string | null;
  created_at: string;
};

export type WorldEventAuditFilters = {
  event_name?: string | null;
  actor_ref?: string | null;
  sequence_after?: number | null;
  sequence_before?: number | null;
  wall_time_from?: string | null;
  wall_time_to?: string | null;
  limit?: number;
};

export type CalendarConflictSource = {
  source_kind: "calendar_entry" | "schedule_rule";
  source_id: string;
  agent_id: string | null;
  label: string;
};

export type CalendarConflict = {
  conflict_type:
    | "calendar_entry_overlap"
    | "schedule_rule_overlap"
    | "schedule_rule_calendar_overlap";
  world_id: string;
  agent_id: string | null;
  starts_at: string;
  ends_at: string;
  reason: string;
  sources: CalendarConflictSource[];
};

export type CalendarConflictReport = {
  world_id: string;
  start_world_time: string;
  horizon_hours: number;
  conflict_count: number;
  conflicts: CalendarConflict[];
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
  backend: string;
  created_at: string | null;
  score: number | null;
};

export type MemoryProfileSnapshot = {
  id: string;
  world_id: string;
  agent_id: string;
  aliases: string[];
  identity_notes: string[];
  durable_preferences: string[];
  long_lived_goals: string[];
  language_style_preferences: string[];
  refreshed_at: string;
  created_at: string;
  updated_at: string;
};

export type MemoryBackendProfile = {
  id: string;
  profile_key: string;
  name: string;
  backend_kind: "mem0_oss" | "local_pgvector";
  vector_store_config: Record<string, unknown>;
  llm_config: Record<string, unknown>;
  embedder_config: Record<string, unknown>;
  reranker_config: Record<string, unknown>;
  secret_refs: Record<string, string>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type MemoryBackendHealth = {
  backend: string;
  status: "ok" | "degraded" | "unavailable";
  details: Record<string, unknown>;
};

export type MemoryWriteLog = {
  id: string;
  job_id: string;
  backend: string;
  success: boolean;
  latency_ms: number | null;
  request_summary: Record<string, unknown>;
  response_summary: Record<string, unknown>;
  correlation_ids: Record<string, unknown>;
  occurred_at: string;
};

export type MemoryWriteJobStatus = "pending" | "processing" | "succeeded" | "failed";

export type MemoryWriteJobStatusSummary = {
  pending_count: number;
  processing_count: number;
  succeeded_count: number;
  failed_count: number;
  due_count: number;
  retryable_failed_count: number;
  terminal_failed_count: number;
  stalled_processing_count: number;
};

export type MemoryWriteJob = {
  id: string;
  world_id: string;
  agent_id: string;
  backend_profile_id: string;
  backend_profile_key: string;
  backend_profile_name: string;
  backend_kind: "mem0_oss" | "local_pgvector";
  source_kind: "agent_run" | "conversation_turn" | "world_event";
  source_id: string;
  dedupe_key: string;
  status: MemoryWriteJobStatus;
  attempt_count: number;
  next_attempt_at: string;
  last_error: string | null;
  processed_at: string | null;
  is_retryable: boolean;
  terminal_reason: string | null;
  last_log_success: boolean | null;
  age_seconds: number;
  created_at: string;
  updated_at: string;
};

export type MemoryWriteJobList = {
  jobs: MemoryWriteJob[];
};

export type MemoryRetrievalLog = {
  id: string;
  world_id: string;
  agent_id: string;
  backend_profile_id: string | null;
  backend: string;
  query_text: string;
  hit_count: number;
  selected_item_ids: string[];
  latency_ms: number | null;
  context_item_count: number;
  occurred_at: string;
};

export type MemoryBackendLogs = {
  write_logs: MemoryWriteLog[];
  retrieval_logs: MemoryRetrievalLog[];
};

export type MemoryEvalCaseResult = {
  label: string;
  query_text: string;
  backend: string;
  hit_count: number;
  context_item_count: number;
  latency_ms: number | null;
};

export type MemoryEvalResult = {
  backend: string;
  case_count: number;
  hit_case_count: number;
  average_latency_ms: number | null;
  average_context_items: number;
  cases: MemoryEvalCaseResult[];
};

export type MemoryBackfillSourceSummary = {
  source_kind: "agent_run" | "conversation_turn" | "world_event";
  candidate_count: number;
  skipped_existing_count: number;
  skipped_no_profile_count: number;
  skipped_disabled_profile_count: number;
};

export type MemoryBackfillWorldSummary = {
  world_id: string;
  backend_profile_id: string | null;
  backend_profile_key: string | null;
  candidate_count: number;
  skipped_existing_count: number;
  skipped_no_profile_count: number;
  skipped_disabled_profile_count: number;
};

export type MemoryBackfillDryRun = {
  candidate_count: number;
  skipped_existing_count: number;
  skipped_no_profile_count: number;
  skipped_disabled_profile_count: number;
  source_summaries: MemoryBackfillSourceSummary[];
  world_summaries: MemoryBackfillWorldSummary[];
};

export type RuntimeControl = {
  desired_state: "running" | "stopped";
  last_heartbeat_at: string | null;
  last_run_started_at: string | null;
  last_run_finished_at: string | null;
  last_error: string | null;
};

export type RuntimeHealth = {
  status: "healthy" | "stopped" | "degraded" | "failed";
  reason: string;
  recent_diagnostic_count: number;
  recent_error_count: number;
  heartbeat_age_seconds: number | null;
};

export type RuntimeStatus = RuntimeControl & {
  runtime_loop_interval_seconds: number;
  runtime_batch_limit: number;
  memory_write_jobs: MemoryWriteJobStatusSummary;
  runtime_health: RuntimeHealth;
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
  plugin_identifier: string;
  plugin_config: Record<string, unknown>;
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

export type ProviderHealthStatus =
  | "ok"
  | "untested"
  | "configuration_error"
  | "degraded"
  | "disabled";

export type ProviderSecretRefStatus = "configured" | "missing" | "empty";

export type ProviderHealth = {
  id: string;
  profile_key: string;
  name: string;
  provider_type: ProviderType;
  is_enabled: boolean;
  health: ProviderHealthStatus;
  api_key_ref: string;
  secret_ref_status: ProviderSecretRefStatus;
  secret_ref_message: string | null;
  last_tested_at: string | null;
  last_test_status: "success" | "failed" | null;
  last_test_error: string | null;
  missing_secret_ref: boolean;
  recent_diagnostic_count: number;
  recent_error_count: number;
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
  trigger_source: string;
  source_calendar_entry_id: string | null;
  source_schedule_rule_id: string | null;
  created_event_id: string | null;
  diagnostics: Record<string, unknown>;
  started_at: string;
  finished_at: string | null;
};

export type AgentRunProviderSummary = {
  id: string;
  profile_key: string;
  name: string;
  provider_type: ProviderType;
  model_name: string;
  is_enabled: boolean;
};

export type AgentRunConversationTurn = {
  id: string;
  session_id: string;
  turn_index: number;
  speaker_kind: string;
  speaker_agent_id: string | null;
  status: string;
  error_text: string | null;
  created_at: string;
};

export type AgentRunDetail = {
  run: AgentRun;
  provider_profile: AgentRunProviderSummary | null;
  conversation_turns: AgentRunConversationTurn[];
};

export type AgentPersona = {
  id: string;
  world_id: string;
  agent_id: string;
  persona_text: string;
  behavior_policy: Record<string, unknown>;
  policy_plugin_identifier: string;
  policy_plugin_config: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type PersonaPolicyValidationIssue = {
  field: string;
  message: string;
};

export type PersonaPolicyValidation = {
  valid: boolean;
  issues: PersonaPolicyValidationIssue[];
};

export type PluginCategory =
  | "model_provider"
  | "memory_backend"
  | "world_rules"
  | "persona_policy"
  | "narrative_writer";

export type PluginCatalogEntry = {
  identifier: string;
  category: PluginCategory;
  version: string;
  config_schema: Record<string, unknown>;
  capabilities: string[];
  built_in: boolean;
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
  confidence_score: number | null;
  review_status: "unreviewed" | "approved" | "rejected";
  runtime_use_count: number;
  last_used_run_id: string | null;
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
  publication: NarrativePublication | null;
};

export type NarrativePublication = {
  id: string;
  world_id: string;
  artifact_id: string;
  source_draft_id: string | null;
  status: "published" | "unpublished";
  reader_visible: boolean;
  metadata: Record<string, unknown>;
  published_at: string | null;
  unpublished_at: string | null;
  published_by_user_id: string | null;
  created_at: string;
  updated_at: string;
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
  worldEventAudit: WorldEventAuditEntry[];
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
  memory_backend_profile_id?: string | null;
  memory_plugin_identifier?: string;
  memory_plugin_config?: Record<string, unknown>;
  world_rules_plugin_identifier?: string;
  world_rules_plugin_config?: Record<string, unknown>;
};

export type WorldUpdateInput = {
  name?: string;
  description?: string | null;
  rules_config?: Record<string, unknown>;
  memory_backend_profile_id?: string | null;
  memory_plugin_identifier?: string;
  memory_plugin_config?: Record<string, unknown>;
  world_rules_plugin_identifier?: string;
  world_rules_plugin_config?: Record<string, unknown>;
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
  kind?: AgentKind;
  home_scene_id?: string | null;
  preset_id?: string | null;
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

export type AgentPresetCreateInput = {
  preset_key: string;
  name: string;
  description?: string | null;
  default_kind: AgentKind;
  default_provider_profile_key?: string | null;
  persona_text?: string;
  behavior_policy?: Record<string, unknown>;
  calendar_blueprint?: AgentPresetCalendarEntry[];
  advanced_config?: Record<string, unknown>;
  is_active?: boolean;
};

export type AgentPresetUpdateInput = {
  preset_key?: string;
  name?: string;
  description?: string | null;
  default_kind?: AgentKind;
  default_provider_profile_key?: string | null;
  persona_text?: string;
  behavior_policy?: Record<string, unknown>;
  calendar_blueprint?: AgentPresetCalendarEntry[];
  advanced_config?: Record<string, unknown>;
  is_active?: boolean;
};

export type WorldCompositionImportInput = {
  slug: string;
  name: string;
  owner_user_id: string;
  description?: string | null;
  rules_config?: Record<string, unknown> | null;
  composition: WorldCompositionExport;
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
  memory_config: ConversationMemoryConfig;
};

export type ConversationUpdateInput = {
  title?: string;
  objective?: string;
  opening_prompt?: string;
  max_turns?: number;
  policy?: ConversationPolicy;
  writer_config?: ConversationWriterConfig;
  memory_config?: ConversationMemoryConfig;
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

export type ScheduleRulePreviewInput = {
  kind: ScheduleRuleKind;
  config?: Record<string, unknown>;
  start_world_time?: string | null;
  horizon_hours?: number;
  limit?: number;
};

export type CalendarConflictFilters = {
  start_world_time?: string | null;
  horizon_hours?: number;
  limit?: number;
};

export type ScheduleRulePreviewMatch = {
  world_time: string;
  reason: string;
  affected_agent_count: number;
  affected_agent_ids: string[];
};

export type ScheduleRulePreview = {
  world_id: string;
  kind: ScheduleRuleKind;
  config: Record<string, unknown>;
  start_world_time: string;
  horizon_hours: number;
  match_count: number;
  affected_agent_count: number;
  affected_agent_ids: string[];
  matches: ScheduleRulePreviewMatch[];
};

export type MemorySearchInput = {
  query_text: string;
  limit?: number;
};

export type MemoryBackendProfileCreateInput = {
  profile_key: string;
  name: string;
  backend_kind: "mem0_oss" | "local_pgvector";
  vector_store_config?: Record<string, unknown>;
  llm_config?: Record<string, unknown>;
  embedder_config?: Record<string, unknown>;
  reranker_config?: Record<string, unknown>;
  secret_refs?: Record<string, string>;
  is_enabled?: boolean;
};

export type MemoryBackendProfileUpdateInput = {
  name?: string;
  vector_store_config?: Record<string, unknown>;
  llm_config?: Record<string, unknown>;
  embedder_config?: Record<string, unknown>;
  reranker_config?: Record<string, unknown>;
  secret_refs?: Record<string, string>;
  is_enabled?: boolean;
};

export type RuntimeControlUpdateInput = {
  desired_state: "running" | "stopped";
};

export type ProviderProfileCreateInput = {
  profile_key: string;
  name: string;
  provider_type: ProviderType;
  plugin_identifier?: string | null;
  plugin_config?: Record<string, unknown>;
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
  plugin_identifier?: string | null;
  plugin_config?: Record<string, unknown>;
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
  policy_plugin_identifier?: string;
  policy_plugin_config?: Record<string, unknown>;
  is_enabled?: boolean;
};

export type AgentObservationCreateInput = {
  observation_type?: string;
  content: string;
  metadata?: Record<string, unknown>;
  observed_at?: string | null;
  confidence_score?: number | null;
  review_status?: "unreviewed" | "approved" | "rejected";
};

export type NarrativeArtifactCreateInput = {
  title: string;
  content: string;
  artifact_kind?: NarrativeArtifactKind;
  agent_id?: string | null;
};

export type NarrativePublicationInput = {
  reader_visible?: boolean;
  metadata?: Record<string, unknown>;
};

export type NarrativeArtifactFilters = {
  artifact_kind?: string | null;
  source_conversation_id?: string | null;
  q?: string | null;
  source_kind?: "world" | "agent" | "agent_run" | "conversation" | null;
  publication_status?: "draft" | "published" | null;
  limit?: number;
};

export type ConversationNarrativeArtifactSet =
  | "summary_and_chapter"
  | "summary_only"
  | "chapter_only";
