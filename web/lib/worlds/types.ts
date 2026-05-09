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
  region_key: string | null;
  location_tags: string[];
  opening_rules: Record<string, unknown>;
  is_active: boolean;
};

export type WorldRole = "world_admin" | "human_user";

export type ContinuityStatus = "canon" | "post_canon" | "alternate" | "original_expansion";

export type NarrativeRole =
  | "protagonist"
  | "main_character"
  | "side_character"
  | "supporting_cast"
  | "ordinary_member"
  | "organization_member"
  | "original_character"
  | "narrative_agent";

export type CharacterImportance = "lead" | "major" | "minor" | "background";

export type CharacterCategory =
  | "player"
  | "main_character"
  | "side_character"
  | "ordinary_member"
  | "organization_member"
  | "original_character"
  | "narrative_agent";

export type RelationshipType =
  | "affection"
  | "friendship"
  | "rivalry"
  | "family"
  | "alliance"
  | "hostility"
  | "obligation"
  | "debt"
  | "secret"
  | "custom";

export type EventImportance =
  | "system"
  | "daily"
  | "relationship"
  | "organization"
  | "route"
  | "main_plot";

export type WorldlineStatus = "active" | "archived";

export type Worldline = {
  id: string;
  world_id: string;
  worldline_key: string;
  name: string;
  description: string | null;
  parent_worldline_id: string | null;
  forked_from_snapshot_id: string | null;
  fork_event_sequence: number | null;
  status: WorldlineStatus;
  created_by_actor_ref: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type WorldlineComparison = {
  base_worldline_id: string;
  compare_worldline_id: string;
  fork_event_sequence: number | null;
  divergent_event_count: number;
  relationship_delta_count: number;
  faction_delta_count: number;
  choice_delta_count: number;
};

export type SceneLocationEdge = {
  id: string;
  world_id: string;
  source_scene_id: string;
  target_scene_id: string;
  source_scene_key: string;
  target_scene_key: string;
  travel_label: string | null;
  traversal_rules: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type OrganizationType =
  | "school"
  | "club"
  | "family"
  | "company"
  | "faction"
  | "secret_group"
  | "other";

export type OrganizationVisibility = "public" | "hidden";

export type WorldOrganization = {
  id: string;
  world_id: string;
  organization_key: string;
  name: string;
  organization_type: OrganizationType;
  description: string | null;
  public_summary: string | null;
  hidden_summary: string | null;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type OrganizationMembership = {
  id: string;
  world_id: string;
  organization_id: string;
  organization_key: string;
  organization_name: string;
  agent_id: string;
  agent_key: string;
  agent_display_name: string;
  role_title: string | null;
  visibility: OrganizationVisibility;
  loyalty: number;
  influence: number;
  responsibilities: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type FactionTrackType = "goal" | "conflict" | "resource" | "reputation" | "risk";

export type FactionProgressTrack = {
  id: string;
  world_id: string;
  worldline_id?: string | null;
  organization_id: string;
  organization_key: string;
  organization_name: string;
  track_key: string;
  name: string;
  track_type: FactionTrackType;
  progress: number;
  pressure: number;
  summary: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PresenceVisibilityStatus = "visible" | "offscreen" | "hidden" | "unavailable";

export type AgentPresence = {
  id: string;
  world_id: string;
  worldline_id?: string | null;
  agent_id: string;
  agent_key: string;
  agent_display_name: string;
  current_scene_id: string | null;
  current_scene_key: string | null;
  current_scene_name: string | null;
  visibility_status: PresenceVisibilityStatus;
  encounter_eligible: boolean;
  scheduled_movement: Record<string, unknown>;
  last_event_id: string | null;
  created_at: string;
  updated_at: string;
};

export type DailyLifeCandidateStatus = "candidate" | "queued" | "dismissed";

export type DailyLifeEventCandidate = {
  id: string | null;
  world_id: string;
  worldline_id?: string | null;
  agent_id: string | null;
  agent_display_name: string | null;
  scene_id: string | null;
  scene_name: string | null;
  title: string;
  summary: string;
  importance: "daily" | "relationship" | "organization";
  starts_at: string;
  source_kind: string;
  source_ref: string | null;
  status: DailyLifeCandidateStatus;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type DailyLifePreview = {
  world_id: string;
  start_world_time: string;
  horizon_hours: number;
  candidate_count: number;
  candidates: DailyLifeEventCandidate[];
};

export type OffscreenEventStatus = "pending" | "resolved" | "cancelled" | "failed";

export type OffscreenEventQueueItem = {
  id: string;
  world_id: string;
  worldline_id?: string | null;
  source_candidate_id: string | null;
  event_name: string;
  title: string;
  payload: Record<string, unknown>;
  due_at: string;
  importance: Exclude<EventImportance, "system">;
  status: OffscreenEventStatus;
  resolved_event_id: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type OffscreenResolution = {
  processed_count: number;
  resolved_count: number;
  failed_count: number;
  event_ids: string[];
};

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
  source_preset_version: number | null;
  agent_key: string;
  display_name: string;
  kind: AgentKind;
  provider_profile_id: string | null;
  narrative_role?: NarrativeRole | null;
  importance?: CharacterImportance | null;
  canon_status?: ContinuityStatus | null;
  character_category?: CharacterCategory | null;
  character_profile?: Record<string, unknown>;
  config: Record<string, unknown>;
  is_enabled: boolean;
};

export type WorldBible = {
  id: string;
  world_id: string;
  source_material: string;
  canon_timeline: Record<string, unknown>[];
  setting_rules: Record<string, unknown>;
  forbidden_changes: Record<string, unknown>[];
  sequel_boundaries: Record<string, unknown>;
  continuity_config: Record<string, unknown>;
  metadata: Record<string, unknown>;
  continuity_status: ContinuityStatus | null;
  created_at: string;
  updated_at: string;
};

export type AgentRelationship = {
  id: string;
  world_id: string;
  worldline_id?: string | null;
  source_agent_id: string;
  source_agent_key: string;
  source_display_name: string;
  target_agent_id: string;
  target_agent_key: string;
  target_display_name: string;
  relationship_type: RelationshipType;
  affection: number;
  trust: number;
  hostility: number;
  intimacy: number;
  obligation: number;
  rivalry: number;
  debt: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
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
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AgentPresetUpdatePreviewAgent = {
  agent_id: string;
  world_id: string;
  agent_key: string;
  display_name: string;
  source_preset_version: number | null;
  status: "current" | "stale" | "unversioned";
  changed_fields: string[];
};

export type AgentPresetUpdatePreview = {
  preset_id: string;
  preset_key: string;
  current_version: number;
  stale_agent_count: number;
  current_agent_count: number;
  unversioned_agent_count: number;
  agents: AgentPresetUpdatePreviewAgent[];
};

export type WorldCompositionWorld = {
  slug: string;
  name: string;
  description: string | null;
  rules_config: Record<string, unknown>;
  memory_backend_profile_key?: string | null;
  memory_plugin_identifier?: string | null;
  memory_plugin_config?: Record<string, unknown>;
  world_rules_plugin_identifier?: string | null;
  world_rules_plugin_config?: Record<string, unknown>;
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
  source_preset_version?: number | null;
  provider_profile_key: string | null;
  narrative_role?: NarrativeRole | null;
  importance?: CharacterImportance | null;
  canon_status?: ContinuityStatus | null;
  character_category?: CharacterCategory | null;
  character_profile?: Record<string, unknown>;
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
  version?: number;
  is_active: boolean;
};

export type WorldCompositionExport = {
  world: WorldCompositionWorld;
  scenes: WorldCompositionScene[];
  agents: WorldCompositionAgent[];
  schedule_rules: WorldCompositionScheduleRule[];
  preset_references: WorldCompositionPresetReference[];
};

export type WorldCompositionValidationIssue = {
  severity: "blocking" | "warning";
  code: string;
  field: string;
  message: string;
};

export type WorldCompositionValidation = {
  valid: boolean;
  blocking_issue_count: number;
  warning_issue_count: number;
  issues: WorldCompositionValidationIssue[];
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
  worldline_id?: string | null;
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
  group_context?: Record<string, unknown>;
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
  worldline_id?: string | null;
  schema_version: string;
  source_sequence: number;
  clock: ReplayClock | null;
  applied_event_count: number;
  unhandled_event_count: number;
};

export type WorldSnapshot = {
  id: string;
  world_id: string;
  worldline_id?: string | null;
  covers_event_sequence: number;
  schema_version: string;
  status: string;
  payload: Record<string, unknown> | null;
  payload_uri: string | null;
  payload_location: "inline" | "object" | null;
  metadata: Record<string, unknown>;
  created_by_event_id: string;
  created_at: string;
};

export type WorldSnapshotIntegrity = {
  world_id: string;
  worldline_id?: string | null;
  status: "ok" | "warning" | "error";
  latest_event_sequence: number;
  latest_snapshot_id: string | null;
  covers_event_sequence: number | null;
  schema_version: string | null;
  payload_location: "inline" | "object" | null;
  event_gap: number | null;
  issues: string[];
};

export type WorldEventAuditEntry = {
  id: string;
  world_id: string;
  worldline_id?: string | null;
  sequence: number;
  event_name: string;
  importance: EventImportance;
  payload: Record<string, unknown>;
  wall_time: string;
  world_time: string | null;
  actor_ref: string;
  continuity_metadata?: Record<string, unknown>;
  continuity_status?: ContinuityStatus | null;
  causation_event_id: string | null;
  correlation_id: string | null;
  created_at: string;
};

export type WorldEventAuditFilters = {
  worldline_id?: string | null;
  event_name?: string | null;
  actor_ref?: string | null;
  importance?: EventImportance | null;
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

export type GMAgendaStatus = "active" | "paused" | "completed" | "archived";

export type GMAgenda = {
  id: string;
  world_id: string;
  worldline_id: string;
  title: string;
  summary: string;
  priority: number;
  status: GMAgendaStatus;
  focus_agents: string[];
  focus_organizations: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type GMProposalStatus = "proposed" | "accepted" | "rejected" | "resolved";

export type GMEventProposal = {
  id: string;
  world_id: string;
  worldline_id: string;
  agenda_id: string | null;
  title: string;
  reason: string;
  event_name: string;
  proposed_payload: Record<string, unknown>;
  importance: Exclude<EventImportance, "system">;
  risk_score: number;
  affected_agents: string[];
  affected_organizations: string[];
  source_context: Record<string, unknown>;
  status: GMProposalStatus;
  review_note: string | null;
  resolved_event_id: string | null;
  created_at: string;
  updated_at: string;
};

export type GMMacroPlanItem = {
  item_kind: string;
  rule_id: string;
  rule_key: string;
  priority: number;
  title: string;
  payload: Record<string, unknown>;
  source_context: Record<string, unknown>;
};

export type GMMacroPlan = {
  world_id: string;
  worldline_id: string;
  planned_items: GMMacroPlanItem[];
  diagnostics: string[];
  execution: Record<string, unknown> | null;
};

export type ResolutionRuleStatus = "active" | "inactive";

export type EventResolutionRule = {
  id: string;
  world_id: string;
  rule_key: string;
  name: string;
  description: string | null;
  priority: number;
  status: ResolutionRuleStatus;
  conditions: Record<string, unknown>;
  effects: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ResolutionRuleDryRun = {
  rule_id: string;
  rule_key: string;
  matched: boolean;
  reasons: string[];
  effects: Record<string, unknown>;
};

export type PlayerActor = {
  id: string;
  world_id: string;
  worldline_id: string;
  user_id: string;
  actor_ref: string;
  display_name: string;
  current_scene_id: string | null;
  profile: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PlayerChoiceKind = "dialogue" | "travel" | "contact" | "intervention" | "route";

export type PlayerChoice = {
  id: string;
  world_id: string;
  worldline_id: string;
  user_id: string;
  player_actor_id: string;
  choice_key: string;
  choice_kind: PlayerChoiceKind;
  prompt: string;
  selected_option: string;
  context: Record<string, unknown>;
  consequence_preview: Record<string, unknown>;
  applied_event_id: string | null;
  created_at: string;
  updated_at: string;
};

export type StoryHookType = "promise" | "foreshadowing" | "mystery" | "agreement" | "flag";
export type StoryHookStatus = "open" | "resolved" | "cancelled";

export type StoryHook = {
  id: string;
  world_id: string;
  worldline_id: string;
  hook_key: string;
  title: string;
  hook_type: StoryHookType;
  summary: string;
  status: StoryHookStatus;
  priority: number;
  owner_agent_id: string | null;
  owner_agent_key: string | null;
  owner_agent_display_name: string | null;
  target_agent_id: string | null;
  target_agent_key: string | null;
  target_agent_display_name: string | null;
  source_event_id: string | null;
  due_at: string | null;
  resolution: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PlotThreadType = "personal" | "organization" | "daily" | "main" | "hidden";
export type PlotThreadStatus = "active" | "dormant" | "completed" | "archived";

export type PlotThread = {
  id: string;
  world_id: string;
  worldline_id: string;
  thread_key: string;
  title: string;
  thread_type: PlotThreadType;
  status: PlotThreadStatus;
  summary: string;
  stakes: string | null;
  next_beats: string[];
  participant_agent_ids: string[];
  organization_ids: string[];
  related_event_ids: string[];
  priority: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RouteStatus = "locked" | "available" | "active" | "completed" | "blocked";

export type RouteAffinity = {
  id: string;
  world_id: string;
  worldline_id: string;
  agent_id: string;
  agent_key: string;
  agent_display_name: string;
  route_key: string;
  status: RouteStatus;
  affinity: number;
  stage: number;
  flags: string[];
  last_choice_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RouteMilestoneStatus = "planned" | "active" | "completed" | "blocked";

export type RouteMilestone = {
  id: string;
  world_id: string;
  worldline_id: string;
  route_affinity_id: string | null;
  plot_thread_id: string | null;
  agent_id: string | null;
  agent_key: string | null;
  agent_display_name: string | null;
  milestone_key: string;
  title: string;
  description: string | null;
  stage: number;
  status: RouteMilestoneStatus;
  conditions: Record<string, unknown>;
  evidence_metadata: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EndingType = "normal" | "bad" | "hidden" | "epilogue";
export type EndingStatus = "planned" | "available" | "locked" | "achieved" | "retired";

export type EndingCandidate = {
  id: string;
  world_id: string;
  worldline_id: string;
  route_affinity_id: string | null;
  plot_thread_id: string | null;
  agent_id: string | null;
  agent_key: string | null;
  agent_display_name: string | null;
  ending_key: string;
  title: string;
  ending_type: EndingType;
  status: EndingStatus;
  requirements: Record<string, unknown>;
  outcome_summary: string | null;
  evidence_metadata: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EndingDryRun = {
  ending_id: string;
  ending_key: string;
  matched: boolean;
  satisfied: string[];
  unsatisfied: string[];
  evidence: Record<string, unknown>;
};

export type LongRunEvalStatus = "completed" | "warning" | "failed";

export type LongRunEvalRun = {
  id: string;
  world_id: string;
  worldline_id: string;
  eval_key: string;
  horizon_days: number;
  status: LongRunEvalStatus;
  started_at: string;
  finished_at: string;
  metrics: Record<string, unknown>;
  recommendations: Record<string, unknown>[];
  blockers: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AuthoringTemplateKind =
  | "source_notes"
  | "character"
  | "event"
  | "route"
  | "world_bundle";

export type AuthoringTemplate = {
  id: string;
  world_id: string;
  template_key: string;
  template_kind: AuthoringTemplateKind;
  name: string;
  description: string | null;
  content: Record<string, unknown>;
  validation_issues: Record<string, unknown>[];
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AuthoringImportStatus = "preview" | "applied" | "failed";

export type AuthoringImportJob = {
  id: string;
  world_id: string;
  template_id: string | null;
  status: AuthoringImportStatus;
  preview_summary: Record<string, unknown>;
  applied_refs: Record<string, unknown>;
  validation_issues: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReleaseProfileStatus = "draft" | "ready" | "blocked" | "released";

export type LivingWorldReleaseProfile = {
  id: string;
  world_id: string;
  profile_key: string;
  status: ReleaseProfileStatus;
  branch_policy: Record<string, unknown>;
  backup_policy: Record<string, unknown>;
  content_review_policy: Record<string, unknown>;
  player_permission_policy: Record<string, unknown>;
  worldline_policy: Record<string, unknown>;
  checklist: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BetaChecklistStatus = "pending" | "passed" | "warning" | "blocked";

export type BetaChecklistRun = {
  id: string;
  world_id: string;
  worldline_id: string;
  run_key: string;
  status: BetaChecklistStatus;
  summary: string;
  evidence: Record<string, unknown>;
  blocker_count: number;
  created_by_actor_ref: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BetaChecklistItem = {
  id: string;
  run_id: string;
  item_key: string;
  title: string;
  status: BetaChecklistStatus;
  evidence: Record<string, unknown>;
  recommendation: string | null;
  created_at: string;
  updated_at: string;
};

export type TriggerConditionStatus = "active" | "inactive";

export type EventTriggerCondition = {
  id: string;
  world_id: string;
  condition_key: string;
  name: string;
  description: string | null;
  status: TriggerConditionStatus;
  priority: number;
  conditions: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type TriggerConditionDryRun = {
  condition_id: string;
  condition_key: string;
  matched: boolean;
  satisfied: string[];
  unsatisfied: string[];
};

export type SceneBeatStatus = "draft" | "approved" | "published" | "archived";

export type SceneBeatDraft = {
  id: string;
  world_id: string;
  worldline_id: string;
  source_kind: "event" | "proposal" | "daily_episode" | "manual";
  source_ref: string | null;
  title: string;
  setup: string;
  dialogue_beats: Record<string, unknown>[];
  choice_points: Record<string, unknown>[];
  aftermath: string;
  participant_agent_ids: string[];
  scene_id: string | null;
  scene_key: string | null;
  scene_name: string | null;
  status: SceneBeatStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DailyEpisodeStatus = "draft" | "queued" | "published" | "archived";

export type DailyEpisodeDraft = {
  id: string;
  world_id: string;
  worldline_id: string;
  source_candidate_id: string | null;
  title: string;
  summary: string;
  scene_beat_draft_id: string | null;
  participant_agent_ids: string[];
  status: DailyEpisodeStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type GroupInteractionType =
  | "club"
  | "class"
  | "organization_meeting"
  | "conflict"
  | "casual";
export type GroupInteractionStatus = "planned" | "active" | "completed" | "archived";

export type GroupInteractionContext = {
  id: string;
  world_id: string;
  worldline_id: string;
  context_key: string;
  title: string;
  interaction_type: GroupInteractionType;
  scene_id: string | null;
  scene_key: string | null;
  scene_name: string | null;
  organization_id: string | null;
  organization_key: string | null;
  organization_name: string | null;
  participant_agent_ids: string[];
  participant_roles: Record<string, unknown>;
  constraints: Record<string, unknown>;
  status: GroupInteractionStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SuggestionStatus = "suggested" | "accepted" | "dismissed";

export type RelationshipEventSuggestion = {
  id: string;
  world_id: string;
  worldline_id: string;
  relationship_id: string | null;
  source_agent_id: string | null;
  source_agent_display_name: string | null;
  target_agent_id: string | null;
  target_agent_display_name: string | null;
  title: string;
  reason: string;
  suggested_event_name: string;
  score: number;
  status: SuggestionStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type OrganizationConflictStatus = "proposed" | "resolved" | "dismissed";

export type OrganizationConflict = {
  id: string;
  world_id: string;
  worldline_id: string;
  organization_id: string;
  organization_key: string;
  organization_name: string;
  faction_track_id: string | null;
  faction_track_key: string | null;
  title: string;
  summary: string;
  pressure_delta: number;
  progress_delta: number;
  status: OrganizationConflictStatus;
  resolved_event_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RumorStatus = "active" | "resolved" | "false" | "archived";
export type RumorVisibility = "private" | "group" | "public";

export type Rumor = {
  id: string;
  world_id: string;
  worldline_id: string;
  rumor_key: string;
  title: string;
  content: string;
  source_agent_id: string | null;
  source_agent_display_name: string | null;
  source_organization_id: string | null;
  source_organization_name: string | null;
  visibility: RumorVisibility;
  known_agent_ids: string[];
  status: RumorStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RumorPropagationStatus = "pending" | "delivered" | "blocked";

export type RumorPropagation = {
  id: string;
  world_id: string;
  worldline_id: string;
  rumor_id: string;
  rumor_title: string;
  source_agent_id: string | null;
  source_agent_display_name: string | null;
  target_agent_id: string | null;
  target_agent_display_name: string | null;
  target_organization_id: string | null;
  target_organization_name: string | null;
  propagation_reason: string;
  status: RumorPropagationStatus;
  delivered_event_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type KnowledgeKind = "fact" | "secret" | "guess" | "misbelief";
export type KnowledgeVisibility = "private" | "shared" | "public";

export type CharacterKnowledgeFact = {
  id: string;
  world_id: string;
  worldline_id: string;
  agent_id: string;
  agent_key: string;
  agent_display_name: string;
  fact_key: string;
  knowledge_kind: KnowledgeKind;
  content: string;
  source_event_id: string | null;
  source_ref: string | null;
  confidence: number;
  visibility: KnowledgeVisibility;
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SecretStatus = "hidden" | "revealed" | "archived";
export type SecretVisibility = "private" | "holders" | "public";

export type SecretRecord = {
  id: string;
  world_id: string;
  worldline_id: string;
  secret_key: string;
  title: string;
  content: string;
  holder_agent_ids: string[];
  reveal_conditions: Record<string, unknown>;
  consequence_metadata: Record<string, unknown>;
  visibility: SecretVisibility;
  status: SecretStatus;
  revealed_event_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CharacterEmotionalState = {
  id: string;
  world_id: string;
  worldline_id: string;
  agent_id: string;
  agent_key: string;
  agent_display_name: string;
  mood: string;
  stress: number;
  fatigue: number;
  anticipation: number;
  jealousy: number;
  anger: number;
  source_event_id: string | null;
  expires_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RelationshipRepairKind =
  | "decay"
  | "repair"
  | "conflict"
  | "apology"
  | "kept_promise"
  | "shared_event";
export type RelationshipRepairStatus = "proposed" | "applied" | "dismissed";

export type RelationshipRepairRecord = {
  id: string;
  world_id: string;
  worldline_id: string;
  relationship_id: string;
  repair_kind: RelationshipRepairKind;
  reason: string;
  score_delta: Record<string, unknown>;
  status: RelationshipRepairStatus;
  applied_event_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type JournalEntryKind = "choice" | "relationship" | "event" | "narrative" | "private_note";
export type JournalVisibility = "player_private" | "world_admin";

export type PlayerJournalEntry = {
  id: string;
  world_id: string;
  worldline_id: string;
  user_id: string;
  player_actor_id: string | null;
  entry_kind: JournalEntryKind;
  title: string;
  body: string;
  source_event_id: string | null;
  source_ref: string | null;
  visibility: JournalVisibility;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NotificationKind =
  | "message"
  | "invitation"
  | "rumor"
  | "promise"
  | "incident"
  | "intervention";
export type NotificationStatus = "unread" | "read" | "archived";

export type InWorldNotification = {
  id: string;
  world_id: string;
  worldline_id: string;
  user_id: string;
  notification_kind: NotificationKind;
  title: string;
  body: string;
  source_event_id: string | null;
  source_ref: string | null;
  status: NotificationStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type InterventionKind = "observe" | "reply" | "travel" | "contact" | "push_event";
export type InterventionStatus = "recorded" | "resolved" | "cancelled";

export type PlayerInterventionRecord = {
  id: string;
  world_id: string;
  worldline_id: string;
  user_id: string;
  player_actor_id: string;
  intervention_kind: InterventionKind;
  target_agent_id: string | null;
  target_scene_id: string | null;
  prompt: string;
  choice_id: string | null;
  event_id: string | null;
  status: InterventionStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReviewStatus = "pass" | "warning" | "fail";

export type GMStyleReview = {
  id: string;
  world_id: string;
  worldline_id: string;
  source_kind: string;
  source_ref: string | null;
  reviewed_text: string;
  status: ReviewStatus;
  diagnostics: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NarrativeContinuityReview = {
  id: string;
  world_id: string;
  worldline_id: string;
  artifact_id: string | null;
  source_kind: string;
  source_ref: string | null;
  reviewed_text: string;
  status: ReviewStatus;
  issues: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LivingWorldDashboard = {
  world_id: string;
  worldline_id: string;
  knowledge_count: number;
  hidden_secret_count: number;
  emotional_state_count: number;
  open_hook_count: number;
  unread_notification_count: number;
  pending_intervention_count: number;
  active_route_count: number;
  pressure_summary: Record<string, number>;
};

export type ChoiceConsequencePreview = {
  relationship_updates: Record<string, unknown>[];
  faction_updates: Record<string, unknown>[];
  offscreen_events: Record<string, unknown>[];
  diagnostics: string[];
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
  worldline_id: string | null;
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
  worldline_id: string | null;
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

export type ExternalToolPolicy = {
  policy_mode: "policy_only";
  execution_enabled: boolean;
  runtime_execution_enabled: boolean;
  supported_permission_modes: string[];
  default_permission_mode: string;
  deny_reasons: string[];
  audit_fields: string[];
  secret_handling: string[];
  data_exposure_rules: string[];
  operator_message: string;
};

export type ScaleReadinessSection = {
  area: string;
  status: "ok" | "watch" | "blocked";
  summary: string;
  metrics: Record<string, number | boolean | string | null>;
  blockers: string[];
  recommendations: string[];
};

export type ScaleReadiness = {
  status: "ok" | "watch" | "blocked";
  section_count: number;
  blocker_count: number;
  generated_at: string;
  sections: ScaleReadinessSection[];
};

export type DiagnosticSeverity = "info" | "warning" | "error";

export type DiagnosticComponent =
  | "runtime"
  | "provider"
  | "agent"
  | "conversation"
  | "event_publisher"
  | "api"
  | "plugin";

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

export type PluginBinding = {
  owner_kind:
    | "provider_profile"
    | "world_memory"
    | "world_rules"
    | "agent_persona"
    | "conversation_writer";
  owner_id: string;
  owner_key: string;
  world_id: string | null;
  agent_id: string | null;
  conversation_id: string | null;
  provider_profile_id: string | null;
  plugin_identifier: string;
  category: PluginCategory;
  config_present: boolean;
  validation_status: "ok" | "missing_plugin" | "category_mismatch" | "invalid_config";
  issue_message: string | null;
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
  continuity_metadata?: Record<string, unknown>;
  continuity_status?: ContinuityStatus | null;
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
  publication_gate?: Record<string, unknown> | null;
};

export type WorldDashboardData = {
  worlds: World[];
  selectedWorldId: string | null;
  scenes: Scene[];
  locationEdges: SceneLocationEdge[];
  agents: Agent[];
  organizations: WorldOrganization[];
  organizationMemberships: OrganizationMembership[];
  factionTracks: FactionProgressTrack[];
  agentPresenceStates: AgentPresence[];
  dailyLifePreview: DailyLifePreview | null;
  dailyLifeCandidates: DailyLifeEventCandidate[];
  offscreenEvents: OffscreenEventQueueItem[];
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
  region_key?: string | null;
  location_tags?: string[];
  opening_rules?: Record<string, unknown>;
};

export type SceneUpdateInput = {
  name?: string;
  description?: string | null;
  region_key?: string | null;
  location_tags?: string[];
  opening_rules?: Record<string, unknown>;
  is_active?: boolean;
};

export type SceneLocationEdgeCreateInput = {
  source_scene_id: string;
  target_scene_id: string;
  travel_label?: string | null;
  traversal_rules?: Record<string, unknown>;
};

export type SceneLocationEdgeUpdateInput = {
  travel_label?: string | null;
  traversal_rules?: Record<string, unknown>;
};

export type OrganizationCreateInput = {
  organization_key: string;
  name: string;
  organization_type: OrganizationType;
  description?: string | null;
  public_summary?: string | null;
  hidden_summary?: string | null;
  metadata?: Record<string, unknown>;
};

export type OrganizationUpdateInput = Partial<
  Pick<
    WorldOrganization,
    | "name"
    | "organization_type"
    | "description"
    | "public_summary"
    | "hidden_summary"
    | "metadata"
    | "is_active"
  >
>;

export type OrganizationMembershipCreateInput = {
  agent_id: string;
  role_title?: string | null;
  visibility?: OrganizationVisibility;
  loyalty?: number;
  influence?: number;
  responsibilities?: string[];
  metadata?: Record<string, unknown>;
};

export type OrganizationMembershipUpdateInput = Partial<
  Pick<
    OrganizationMembership,
    "role_title" | "visibility" | "loyalty" | "influence" | "responsibilities" | "metadata"
  >
>;

export type FactionProgressTrackCreateInput = {
  worldline_id?: string | null;
  track_key: string;
  name: string;
  track_type: FactionTrackType;
  progress?: number;
  pressure?: number;
  summary?: string | null;
  metadata?: Record<string, unknown>;
};

export type FactionProgressTrackUpdateInput = Partial<
  Pick<
    FactionProgressTrack,
    "name" | "track_type" | "progress" | "pressure" | "summary" | "metadata"
  >
>;

export type AgentPresenceInput = {
  worldline_id?: string | null;
  current_scene_id?: string | null;
  visibility_status?: PresenceVisibilityStatus;
  encounter_eligible?: boolean;
  scheduled_movement?: Record<string, unknown>;
};

export type DailyLifePreviewFilters = {
  worldline_id?: string | null;
  start_world_time?: string | null;
  horizon_hours?: number;
  limit?: number;
};

export type DailyLifeGenerateInput = {
  worldline_id?: string | null;
  horizon_hours?: number;
  limit?: number;
};

export type DailyLifeCandidateFilters = {
  worldline_id?: string | null;
  status?: DailyLifeCandidateStatus | null;
  limit?: number;
};

export type OffscreenEventCreateInput = {
  worldline_id?: string | null;
  candidate_id?: string | null;
  event_name?: string;
  title: string;
  payload?: Record<string, unknown>;
  due_at: string;
  importance?: Exclude<EventImportance, "system">;
};

export type OffscreenEventFilters = {
  worldline_id?: string | null;
  status?: OffscreenEventStatus | null;
  limit?: number;
};

export type AgentCreateInput = {
  agent_key: string;
  display_name: string;
  kind?: AgentKind;
  home_scene_id?: string | null;
  preset_id?: string | null;
  provider_profile_id?: string | null;
  narrative_role?: NarrativeRole | null;
  importance?: CharacterImportance | null;
  canon_status?: ContinuityStatus | null;
  character_category?: CharacterCategory | null;
  character_profile?: Record<string, unknown>;
  config?: Record<string, unknown>;
};

export type AgentUpdateInput = {
  display_name?: string;
  kind?: AgentKind;
  home_scene_id?: string | null;
  provider_profile_id?: string | null;
  narrative_role?: NarrativeRole | null;
  importance?: CharacterImportance | null;
  canon_status?: ContinuityStatus | null;
  character_category?: CharacterCategory | null;
  character_profile?: Record<string, unknown>;
  config?: Record<string, unknown>;
  is_enabled?: boolean;
};

export type WorldBibleInput = {
  source_material?: string;
  canon_timeline?: Record<string, unknown>[];
  setting_rules?: Record<string, unknown>;
  forbidden_changes?: Record<string, unknown>[];
  sequel_boundaries?: Record<string, unknown>;
  continuity_config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type AgentRelationshipCreateInput = {
  worldline_id?: string | null;
  source_agent_id: string;
  target_agent_id: string;
  relationship_type: RelationshipType;
  affection?: number;
  trust?: number;
  hostility?: number;
  intimacy?: number;
  obligation?: number;
  rivalry?: number;
  debt?: number;
  metadata?: Record<string, unknown>;
};

export type AgentRelationshipUpdateInput = Partial<
  Pick<
    AgentRelationship,
    | "affection"
    | "trust"
    | "hostility"
    | "intimacy"
    | "obligation"
    | "rivalry"
    | "debt"
    | "metadata"
  >
>;

export type WorldlineForkInput = {
  source_worldline_id?: string | null;
  worldline_key: string;
  name: string;
  description?: string | null;
  forked_from_snapshot_id?: string | null;
  fork_event_sequence?: number | null;
  metadata?: Record<string, unknown>;
};

export type WorldlineScopedFilters = {
  worldline_id?: string | null;
};

export type GMAgendaCreateInput = {
  worldline_id?: string | null;
  title: string;
  summary: string;
  priority?: number;
  focus_agents?: string[];
  focus_organizations?: string[];
  metadata?: Record<string, unknown>;
};

export type GMAgendaUpdateInput = Partial<
  Pick<
    GMAgenda,
    | "title"
    | "summary"
    | "priority"
    | "status"
    | "focus_agents"
    | "focus_organizations"
    | "metadata"
  >
>;

export type GMProposalCreateInput = {
  worldline_id?: string | null;
  agenda_id?: string | null;
  title: string;
  reason: string;
  event_name: string;
  proposed_payload?: Record<string, unknown>;
  importance?: Exclude<EventImportance, "system">;
  risk_score?: number;
  affected_agents?: string[];
  affected_organizations?: string[];
  source_context?: Record<string, unknown>;
};

export type GMProposalReviewInput = {
  status: GMProposalStatus;
  review_note?: string | null;
};

export type GMMacroPlanInput = {
  worldline_id?: string | null;
  limit?: number;
  execute?: boolean;
};

export type EventResolutionRuleCreateInput = {
  rule_key: string;
  name: string;
  description?: string | null;
  priority?: number;
  conditions?: Record<string, unknown>;
  effects?: Record<string, unknown>;
};

export type EventResolutionRuleUpdateInput = Partial<
  Pick<
    EventResolutionRule,
    "name" | "description" | "priority" | "status" | "conditions" | "effects"
  >
>;

export type PlayerActorBindInput = {
  worldline_id?: string | null;
  user_id?: string | null;
  display_name: string;
  current_scene_id?: string | null;
  profile?: Record<string, unknown>;
};

export type PlayerChoiceCreateInput = {
  worldline_id?: string | null;
  user_id?: string | null;
  player_actor_id: string;
  choice_key: string;
  choice_kind: PlayerChoiceKind;
  prompt: string;
  selected_option: string;
  context?: Record<string, unknown>;
  effects?: Record<string, unknown>;
  apply?: boolean;
};

export type StoryHookCreateInput = {
  worldline_id?: string | null;
  hook_key: string;
  title: string;
  hook_type: StoryHookType;
  summary: string;
  priority?: number;
  owner_agent_id?: string | null;
  target_agent_id?: string | null;
  due_at?: string | null;
  metadata?: Record<string, unknown>;
};

export type StoryHookUpdateInput = Partial<
  Pick<
    StoryHook,
    | "title"
    | "summary"
    | "status"
    | "priority"
    | "owner_agent_id"
    | "target_agent_id"
    | "due_at"
    | "resolution"
    | "metadata"
  >
>;

export type PlotThreadCreateInput = {
  worldline_id?: string | null;
  thread_key: string;
  title: string;
  thread_type: PlotThreadType;
  summary: string;
  stakes?: string | null;
  next_beats?: string[];
  participant_agent_ids?: string[];
  organization_ids?: string[];
  priority?: number;
  metadata?: Record<string, unknown>;
};

export type PlotThreadUpdateInput = Partial<
  Pick<
    PlotThread,
    | "title"
    | "thread_type"
    | "status"
    | "summary"
    | "stakes"
    | "next_beats"
    | "participant_agent_ids"
    | "organization_ids"
    | "related_event_ids"
    | "priority"
    | "metadata"
  >
>;

export type RouteAffinityUpsertInput = {
  worldline_id?: string | null;
  agent_id: string;
  route_key: string;
  status?: RouteStatus;
  affinity?: number;
  stage?: number;
  flags?: string[];
  metadata?: Record<string, unknown>;
};

export type EventTriggerConditionCreateInput = {
  condition_key: string;
  name: string;
  description?: string | null;
  priority?: number;
  conditions?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type EventTriggerConditionUpdateInput = Partial<
  Pick<
    EventTriggerCondition,
    "name" | "description" | "status" | "priority" | "conditions" | "metadata"
  >
>;

export type SceneBeatDraftCreateInput = {
  worldline_id?: string | null;
  source_kind?: "event" | "proposal" | "daily_episode" | "manual";
  source_ref?: string | null;
  title: string;
  participant_agent_ids?: string[];
  scene_id?: string | null;
  metadata?: Record<string, unknown>;
};

export type DailyEpisodeDraftCreateInput = {
  worldline_id?: string | null;
  source_candidate_id?: string | null;
  title?: string | null;
  metadata?: Record<string, unknown>;
};

export type GroupInteractionCreateInput = {
  worldline_id?: string | null;
  context_key: string;
  title: string;
  interaction_type: GroupInteractionType;
  scene_id?: string | null;
  organization_id?: string | null;
  participant_agent_ids?: string[];
  participant_roles?: Record<string, unknown>;
  constraints?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type GroupInteractionExecuteInput = {
  session_key?: string | null;
  mode?: ConversationMode;
  max_turns?: number;
  policy?: Partial<ConversationPolicy>;
  writer_config?: Partial<ConversationWriterConfig>;
  memory_config?: Partial<ConversationMemoryConfig>;
  opening_prompt?: string | null;
  objective?: string | null;
};

export type GroupInteractionExecution = {
  group_context: GroupInteractionContext;
  session: ConversationSession;
};

export type RelationshipSuggestionUpdateInput = {
  status?: SuggestionStatus | null;
  metadata?: Record<string, unknown>;
};

export type OrganizationConflictCreateInput = {
  worldline_id?: string | null;
  organization_id: string;
  faction_track_id?: string | null;
  title: string;
  summary: string;
  pressure_delta?: number;
  progress_delta?: number;
  metadata?: Record<string, unknown>;
};

export type RumorCreateInput = {
  worldline_id?: string | null;
  rumor_key: string;
  title: string;
  content: string;
  source_agent_id?: string | null;
  source_organization_id?: string | null;
  visibility?: RumorVisibility;
  known_agent_ids?: string[];
  metadata?: Record<string, unknown>;
};

export type RumorPropagationCreateInput = {
  worldline_id?: string | null;
  rumor_id: string;
  source_agent_id?: string | null;
  target_agent_id?: string | null;
  target_organization_id?: string | null;
  propagation_reason: string;
  metadata?: Record<string, unknown>;
};

export type KnowledgeFactUpsertInput = {
  worldline_id?: string | null;
  agent_id: string;
  fact_key: string;
  knowledge_kind?: KnowledgeKind;
  content: string;
  confidence?: number;
  visibility?: KnowledgeVisibility;
  source_event_id?: string | null;
  source_ref?: string | null;
  metadata?: Record<string, unknown>;
};

export type SecretCreateInput = {
  worldline_id?: string | null;
  secret_key: string;
  title: string;
  content: string;
  holder_agent_ids?: string[];
  reveal_conditions?: Record<string, unknown>;
  consequence_metadata?: Record<string, unknown>;
  visibility?: SecretVisibility;
  metadata?: Record<string, unknown>;
};

export type EmotionalStateUpsertInput = {
  worldline_id?: string | null;
  agent_id: string;
  mood?: string;
  stress?: number;
  fatigue?: number;
  anticipation?: number;
  jealousy?: number;
  anger?: number;
  source_event_id?: string | null;
  expires_at?: string | null;
  metadata?: Record<string, unknown>;
};

export type RelationshipRepairCreateInput = {
  worldline_id?: string | null;
  relationship_id: string;
  repair_kind: RelationshipRepairKind;
  reason: string;
  score_delta?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type JournalEntryCreateInput = {
  worldline_id?: string | null;
  user_id?: string | null;
  player_actor_id?: string | null;
  entry_kind: JournalEntryKind;
  title: string;
  body: string;
  source_event_id?: string | null;
  source_ref?: string | null;
  visibility?: JournalVisibility;
  metadata?: Record<string, unknown>;
};

export type NotificationCreateInput = {
  worldline_id?: string | null;
  user_id?: string | null;
  notification_kind: NotificationKind;
  title: string;
  body: string;
  source_event_id?: string | null;
  source_ref?: string | null;
  metadata?: Record<string, unknown>;
};

export type InterventionCreateInput = {
  worldline_id?: string | null;
  user_id?: string | null;
  player_actor_id: string;
  intervention_kind: InterventionKind;
  target_agent_id?: string | null;
  target_scene_id?: string | null;
  prompt: string;
  metadata?: Record<string, unknown>;
};

export type GMStyleReviewCreateInput = {
  worldline_id?: string | null;
  source_kind: string;
  source_ref?: string | null;
  reviewed_text: string;
  metadata?: Record<string, unknown>;
};

export type NarrativeContinuityReviewCreateInput = {
  worldline_id?: string | null;
  artifact_id?: string | null;
  source_kind: string;
  source_ref?: string | null;
  reviewed_text: string;
  metadata?: Record<string, unknown>;
};

export type RouteMilestoneCreateInput = {
  worldline_id?: string | null;
  milestone_key: string;
  title: string;
  description?: string | null;
  stage?: number;
  status?: RouteMilestoneStatus;
  route_affinity_id?: string | null;
  plot_thread_id?: string | null;
  agent_id?: string | null;
  conditions?: Record<string, unknown>;
  evidence_metadata?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type EndingCandidateCreateInput = {
  worldline_id?: string | null;
  ending_key: string;
  title: string;
  ending_type: EndingType;
  status?: EndingStatus;
  route_affinity_id?: string | null;
  plot_thread_id?: string | null;
  agent_id?: string | null;
  requirements?: Record<string, unknown>;
  outcome_summary?: string | null;
  evidence_metadata?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type LongRunEvalCreateInput = {
  worldline_id?: string | null;
  eval_key: string;
  horizon_days?: number;
  metadata?: Record<string, unknown>;
};

export type AuthoringTemplateCreateInput = {
  template_key: string;
  template_kind: AuthoringTemplateKind;
  name: string;
  description?: string | null;
  content?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type AuthoringTemplateApplyInput = {
  target_worldline_id?: string | null;
  duplicate_policy?: "upsert" | "skip" | "fail";
  metadata?: Record<string, unknown>;
};

export type ReleaseProfileUpsertInput = {
  profile_key?: string;
  status?: ReleaseProfileStatus;
  branch_policy?: Record<string, unknown>;
  backup_policy?: Record<string, unknown>;
  content_review_policy?: Record<string, unknown>;
  player_permission_policy?: Record<string, unknown>;
  worldline_policy?: Record<string, unknown>;
  checklist?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type BetaChecklistRunCreateInput = {
  worldline_id?: string | null;
  run_key?: string;
  metadata?: Record<string, unknown>;
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
  continuity_metadata?: Record<string, unknown>;
};

export type NarrativePublicationInput = {
  reader_visible?: boolean;
  metadata?: Record<string, unknown>;
  override_style_warning?: boolean;
};

export type NarrativeArtifactFilters = {
  artifact_kind?: string | null;
  source_conversation_id?: string | null;
  q?: string | null;
  source_kind?: "world" | "agent" | "agent_run" | "conversation" | null;
  publication_status?: "draft" | "published" | null;
  order_by?: "created_at" | "published_at";
  limit?: number;
};

export type ConversationNarrativeArtifactSet =
  | "summary_and_chapter"
  | "summary_only"
  | "chapter_only";
