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
const primaryWorldlineId = "11000000-0000-4000-8000-000000000001";
const sceneHomeId = "20000000-0000-4000-8000-000000000001";
const agentGuideId = "30000000-0000-4000-8000-000000000001";
const membershipOwnerId = "40000000-0000-4000-8000-000000000001";
const membershipMemberId = "40000000-0000-4000-8000-000000000002";
const providerOpenAiId = "71000000-0000-4000-8000-000000000001";
const memoryProfilePrimaryId = "71500000-0000-4000-8000-000000000001";
const seedConversationId = "76000000-0000-4000-8000-000000000001";
const seedSnapshotId = "74500000-0000-4000-8000-000000000001";
const seedEvalId = "83800000-0000-4000-8000-000000000001";
const seedPublicationId = "73500000-0000-4000-8000-000000000001";
const seedContinuityReviewId = "84300000-0000-4000-8000-000000000001";
const seedChecklistRunId = "84100000-0000-4000-8000-000000000001";
const seedEvidenceRefs = [
  {
    kind: "snapshot",
    id: seedSnapshotId,
    label: "seed snapshot",
    worldline_id: primaryWorldlineId,
    api_path: `/worlds/${worldOneId}/snapshots/latest`,
  },
  {
    kind: "worldline",
    id: primaryWorldlineId,
    label: "primary worldline",
    worldline_id: primaryWorldlineId,
    api_path: `/worlds/${worldOneId}/worldlines`,
  },
  {
    kind: "publication",
    id: seedPublicationId,
    label: "seed publication",
    api_path: `/worlds/${worldOneId}/reader`,
  },
  {
    kind: "continuity_review",
    id: seedContinuityReviewId,
    label: "seed continuity review",
    worldline_id: primaryWorldlineId,
    api_path: `/worlds/${worldOneId}/narrative-continuity-reviews`,
  },
  {
    kind: "beta_checklist",
    id: seedChecklistRunId,
    label: "seed checklist",
    worldline_id: primaryWorldlineId,
    api_path: `/worlds/${worldOneId}/beta-checklists`,
  },
  {
    kind: "long_run_eval",
    id: seedEvalId,
    label: "seed long-run eval",
    worldline_id: primaryWorldlineId,
    api_path: `/worlds/${worldOneId}/long-run-evals`,
  },
];

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
const worldlines = [
  {
    id: primaryWorldlineId,
    world_id: worldOneId,
    worldline_key: "primary",
    name: "Primary Worldline",
    description: "Default branch for the living world.",
    parent_worldline_id: null,
    forked_from_snapshot_id: null,
    fork_event_sequence: null,
    status: "active",
    created_by_actor_ref: "system:runtime",
    metadata: { primary: true },
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const worldBibles = new Map([
  [
    worldOneId,
    {
      id: "10500000-0000-4000-8000-000000000001",
      world_id: worldOneId,
      source_material: "Original ending and sequel boundary notes.",
      canon_timeline: ["Original story has concluded."],
      setting_rules: ["Keep continuity stable."],
      forbidden_changes: ["Do not erase canon relationships."],
      sequel_boundaries: ["Post-canon expansion only."],
      continuity_config: { status: "post_canon" },
      metadata: {},
      continuity_status: "post_canon",
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
]);
const scenes = [
  {
    id: sceneHomeId,
    world_id: worldOneId,
    scene_key: "home",
    name: "Home",
    description: null,
    region_key: "home-district",
    location_tags: ["indoors"],
    opening_rules: {},
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
    narrative_role: "supporting_cast",
    importance: "major",
    canon_status: "post_canon",
    character_category: "supporting_cast",
    character_profile: {
      speech_style_notes: ["Careful and direct."],
      current_goals: ["Help operators move the world forward."],
      secrets: [],
      daily_preferences: ["Morning check-ins."],
      emotional_baseline: "calm",
      story_function: "Guide operators through the sequel world.",
    },
    config: { provider_profile_id: providerOpenAiId },
    is_enabled: true,
  },
];
const agentRelationships = [
  {
    id: "30500000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    source_agent_id: agentGuideId,
    source_agent_key: "guide",
    source_display_name: "Guide",
    target_agent_id: agentGuideId,
    target_agent_key: "guide",
    target_display_name: "Guide",
    relationship_type: "friendship",
    affection: 50,
    trust: 50,
    hostility: 0,
    intimacy: 10,
    obligation: 0,
    rivalry: 0,
    debt: 0,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const locationEdges = [
  {
    id: "20500000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    source_scene_id: sceneHomeId,
    target_scene_id: sceneHomeId,
    source_scene_key: "home",
    target_scene_key: "home",
    travel_label: "same building",
    traversal_rules: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const organizations = [
  {
    id: "81000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    organization_key: "student-council",
    name: "Student Council",
    organization_type: "club",
    description: null,
    public_summary: "Coordinates daily school activity.",
    hidden_summary: null,
    metadata: {},
    is_active: true,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const organizationMemberships = [
  {
    id: "81100000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    organization_id: "81000000-0000-4000-8000-000000000001",
    organization_key: "student-council",
    organization_name: "Student Council",
    agent_id: agentGuideId,
    agent_key: "guide",
    agent_display_name: "Guide",
    role_title: "Advisor",
    visibility: "public",
    loyalty: 70,
    influence: 60,
    responsibilities: ["briefing"],
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const factionTracks = [
  {
    id: "81200000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    organization_id: "81000000-0000-4000-8000-000000000001",
    organization_key: "student-council",
    organization_name: "Student Council",
    track_key: "festival-plan",
    name: "Festival Plan",
    track_type: "goal",
    progress: 30,
    pressure: 20,
    summary: "Initial planning is open.",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const agentPresenceStates = [
  {
    id: "81300000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    agent_id: agentGuideId,
    agent_key: "guide",
    agent_display_name: "Guide",
    current_scene_id: sceneHomeId,
    current_scene_key: "home",
    current_scene_name: "Home",
    visibility_status: "visible",
    encounter_eligible: true,
    scheduled_movement: {},
    last_event_id: null,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const dailyLifeCandidates = [
  {
    id: "81400000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    agent_id: agentGuideId,
    agent_display_name: "Guide",
    scene_id: sceneHomeId,
    scene_name: "Home",
    title: "Guide daily life beat",
    summary: "Guide keeps the world moving from Home.",
    importance: "daily",
    starts_at: "2030-01-01T08:00:00.000Z",
    source_kind: "daily_life_scheduler",
    source_ref: agentGuideId,
    status: "candidate",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const offscreenEvents = [
  {
    id: "81500000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    source_candidate_id: "81400000-0000-4000-8000-000000000001",
    event_name: "living_world.daily_life",
    title: "Guide daily life beat",
    payload: { summary: "Guide keeps the world moving from Home." },
    due_at: "2030-01-01T08:00:00.000Z",
    importance: "daily",
    status: "pending",
    resolved_event_id: null,
    last_error: null,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const gmAgendas = [
  {
    id: "81600000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    title: "Festival route pressure",
    summary: "Keep the school festival route moving.",
    priority: 70,
    status: "active",
    focus_agents: ["guide"],
    focus_organizations: ["student-council"],
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const gmProposals = [
  {
    id: "81700000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    agenda_id: "81600000-0000-4000-8000-000000000001",
    title: "Late-night club room",
    reason: "Relationship tension is ready.",
    event_name: "gm.route_pressure",
    proposed_payload: {},
    importance: "route",
    risk_score: 20,
    affected_agents: ["guide"],
    affected_organizations: ["student-council"],
    source_context: {},
    status: "proposed",
    review_note: null,
    resolved_event_id: null,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const resolutionRules = [
  {
    id: "81800000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    rule_key: "trust-gate",
    name: "Trust Gate",
    description: null,
    priority: 50,
    status: "active",
    conditions: { min_relationship_trust: 30 },
    effects: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const playerActors = [
  {
    id: "81900000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    user_id: adminUserId,
    actor_ref: `player:${adminUserId}:primary`,
    display_name: "Admin Player",
    current_scene_id: sceneHomeId,
    profile: {},
    is_active: true,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const knowledgeFacts = [
  {
    id: "83200000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    agent_id: agentGuideId,
    fact_key: "festival-note",
    knowledge_kind: "fact",
    content: "Guide knows the festival plan is behind schedule.",
    source_event_id: null,
    source_ref: null,
    confidence: 90,
    visibility: "private",
    is_active: true,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const secrets = [
  {
    id: "83300000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    secret_key: "hidden-letter",
    title: "Hidden letter",
    content: "A letter was left in the club room.",
    holder_agent_ids: [agentGuideId],
    reveal_conditions: {},
    consequence_metadata: {},
    visibility: "holders",
    status: "hidden",
    revealed_event_id: null,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const emotionalStates = [
  {
    id: "83400000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    agent_id: agentGuideId,
    mood: "focused",
    stress: 20,
    fatigue: 10,
    anticipation: 40,
    jealousy: 0,
    anger: 0,
    source_event_id: null,
    expires_at: null,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const relationshipRepairs = [];
const playerChoices = [
  {
    id: "83500000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    user_id: adminUserId,
    player_actor_id: "81900000-0000-4000-8000-000000000001",
    choice_key: "help-festival",
    choice_kind: "route",
    prompt: "Help with festival preparations?",
    selected_option: "Stay after school.",
    context: {},
    consequence_preview: {},
    applied_event_id: "76000000-0000-4000-8000-000000000001",
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const playerJournal = [
  {
    id: "83300000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    user_id: adminUserId,
    player_actor_id: "81900000-0000-4000-8000-000000000001",
    entry_kind: "choice",
    title: "Festival prep",
    body: "The player helped with festival preparations.",
    source_event_id: "76000000-0000-4000-8000-000000000001",
    source_ref: "83500000-0000-4000-8000-000000000001",
    visibility: "player_private",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const notifications = [
  {
    id: "83500000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    user_id: adminUserId,
    notification_kind: "rumor",
    title: "Club room notice",
    body: "Someone mentioned the hidden letter.",
    source_event_id: null,
    source_ref: null,
    status: "unread",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const interventions = [];
const gmStyleReviews = [];
const narrativeContinuityReviews = [
  {
    id: seedContinuityReviewId,
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    artifact_id: "73000000-0000-4000-8000-000000000002",
    source_kind: "artifact",
    source_ref: "73000000-0000-4000-8000-000000000002",
    reviewed_text: "Seed continuity review",
    status: "warning",
    issues: [{ code: "manual_warning", severity: "warning" }],
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const seedWorldEventRef = {
  kind: "world_event",
  id: "76000000-0000-4000-8000-000000000001",
  label: "world.clock_advanced",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/events`,
};
const seedRelationshipRef = {
  kind: "relationship",
  id: "30500000-0000-4000-8000-000000000001",
  label: "friendship",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/agents/${agentGuideId}`,
};
const seedFactionTrackRef = {
  kind: "faction_track",
  id: "81200000-0000-4000-8000-000000000001",
  label: "festival-plan",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/organizations`,
};
const seedGMProposalRef = {
  kind: "gm_proposal",
  id: "81700000-0000-4000-8000-000000000001",
  label: "Festival route check",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/gm/proposals`,
};
const seedChoiceRef = {
  kind: "player_choice",
  id: "83500000-0000-4000-8000-000000000001",
  label: "help-festival",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/player-choices`,
};
const seedJournalRef = {
  kind: "journal_entry",
  id: "83300000-0000-4000-8000-000000000001",
  label: "Festival prep",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/player-journal`,
};
const seedNotificationRef = {
  kind: "notification",
  id: "83500000-0000-4000-8000-000000000001",
  label: "Festival invite",
  worldline_id: primaryWorldlineId,
  api_path: `/worlds/${worldOneId}/notifications`,
};
const storyHooks = [
  {
    id: "82100000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    hook_key: "festival-promise",
    title: "Festival promise",
    hook_type: "promise",
    summary: "Guide promised to help with the festival.",
    status: "open",
    priority: 70,
    owner_agent_id: agentGuideId,
    target_agent_id: null,
    source_event_id: null,
    due_at: "2030-01-01T18:00:00.000Z",
    resolution: null,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const plotThreads = [
  {
    id: "82200000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    thread_key: "festival-route",
    title: "Festival route",
    thread_type: "personal",
    status: "active",
    summary: "A post-canon festival route is opening.",
    stakes: "Keep the route grounded in daily life.",
    next_beats: ["prep", "rehearsal"],
    participant_agent_ids: [agentGuideId],
    organization_ids: ["81000000-0000-4000-8000-000000000001"],
    related_event_ids: [],
    priority: 60,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const routeAffinities = [
  {
    id: "82300000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    agent_id: agentGuideId,
    route_key: "guide-route",
    status: "available",
    affinity: 35,
    stage: 1,
    flags: ["festival"],
    last_choice_id: null,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const routeMilestones = [
  {
    id: "83600000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    route_affinity_id: "82300000-0000-4000-8000-000000000001",
    plot_thread_id: "82200000-0000-4000-8000-000000000001",
    agent_id: agentGuideId,
    milestone_key: "festival-confession-lock",
    title: "Festival confession lock",
    description: "The guide route can lock a confession branch.",
    stage: 2,
    status: "active",
    conditions: { min_route_stage: 1 },
    evidence_metadata: { route: "guide-route" },
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const endingCandidates = [
  {
    id: "83700000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    route_affinity_id: "82300000-0000-4000-8000-000000000001",
    plot_thread_id: "82200000-0000-4000-8000-000000000001",
    agent_id: agentGuideId,
    ending_key: "guide-normal",
    title: "Guide normal ending",
    ending_type: "normal",
    status: "available",
    requirements: { min_route_stage: 1 },
    outcome_summary: "The festival route closes in a quiet post-canon scene.",
    evidence_metadata: { route: "guide-route" },
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const longRunEvals = [
  {
    id: seedEvalId,
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    eval_key: "seven-day-beta-eval",
    horizon_days: 7,
    status: "completed",
    started_at: "2026-04-17T00:00:00.000Z",
    finished_at: "2026-04-17T00:00:01.000Z",
    metrics: {
      horizon_days: 7,
      events: 1,
      snapshots: 1,
      route_count: 1,
      distribution: {
        events_by_importance: { system: 1 },
        events_by_day: { "2030-01-01": 1 },
        events_by_actor: { system: 1 },
        day_coverage: 1,
      },
      traceability: {
        choice_event_count: 1,
        event_ref_count: 1,
        snapshot_ref_count: 1,
        refs: [
          seedWorldEventRef,
          seedEvidenceRefs[0],
          seedRelationshipRef,
          seedFactionTrackRef,
          seedGMProposalRef,
          seedChoiceRef,
          seedJournalRef,
          seedNotificationRef,
          seedEvidenceRefs[2],
          seedEvidenceRefs[3],
        ],
      },
      review_warnings: {
        continuity_or_style_warning_count: 1,
        continuity_fail_count: 0,
        publication_gate_warning_count: 0,
      },
    },
    recommendations: [],
    blockers: [],
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:01.000Z",
  },
];
const authoringTemplates = [
  {
    id: "83900000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    template_key: "sequel-world-bundle",
    template_kind: "world_bundle",
    name: "Sequel world bundle",
    description: "Source notes, character, event, and route template bundle.",
    content: { source_notes: [], characters: [], events: [], routes: [] },
    validation_issues: [],
    is_active: true,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const authoringImportJobs = [];
const releaseProfiles = new Map([
  [
    worldOneId,
    {
      id: "84000000-0000-4000-8000-000000000001",
      world_id: worldOneId,
      profile_key: "living-world-beta",
      status: "ready",
      branch_policy: { branch_review: true },
      backup_policy: { snapshot_before_beta: true },
      content_review_policy: { continuity_review_required: true },
      player_permission_policy: { invite_only: true },
      worldline_policy: { forks_allowed: true },
      checklist: {
        sample_world_required: true,
        worldline_id: primaryWorldlineId,
        evidence_refs: seedEvidenceRefs,
        warning_decisions: { style: "accepted" },
        gate_decision: {
          status: "ready",
          allowed: true,
          blockers: [],
          warnings: [],
          evidence_refs: seedEvidenceRefs,
          worldline_id: primaryWorldlineId,
        },
      },
      metadata: {
        gate_decision: {
          status: "ready",
          allowed: true,
          blockers: [],
          warnings: [],
          evidence_refs: seedEvidenceRefs,
          worldline_id: primaryWorldlineId,
        },
      },
      created_at: "2026-04-17T00:00:00.000Z",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
  ],
]);
const betaChecklistRuns = [
  {
    id: seedChecklistRunId,
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    run_key: "sample-world-beta",
    status: "passed",
    summary: "Sample world beta has structured release evidence.",
    evidence: {
      refs: seedEvidenceRefs,
      items: {
        "seven-day-simulation": { days: 7, refs: [seedWorldEventRef, seedEvidenceRefs[0]] },
      },
      worldline_id: primaryWorldlineId,
    },
    blocker_count: 0,
    created_by_actor_ref: `user:${adminUserId}`,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const betaChecklistItems = [
  {
    id: "84200000-0000-4000-8000-000000000001",
    run_id: "84100000-0000-4000-8000-000000000001",
    item_key: "seven-day-simulation",
    title: "7-day simulation",
    status: "passed",
    evidence: {
      eval_run_id: seedEvalId,
      refs: [seedWorldEventRef, seedEvidenceRefs[0], seedEvidenceRefs[5]],
    },
    recommendation: null,
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const triggerConditions = [
  {
    id: "82400000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    condition_key: "festival-flag",
    name: "Festival flag",
    description: "Requires at least one open hook.",
    status: "active",
    priority: 50,
    conditions: { min_open_hooks: 1 },
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const sceneBeatDrafts = [
  {
    id: "82500000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    source_kind: "manual",
    source_ref: null,
    title: "Festival prep scene",
    setup: "Guide notices the festival prep is behind schedule.",
    dialogue_beats: [{ speaker: "guide", intent: "surface the daily conflict" }],
    choice_points: [{ prompt: "Help with preparations?", options: ["Help", "Observe"] }],
    aftermath: "The route pressure becomes visible.",
    participant_agent_ids: [agentGuideId],
    scene_id: sceneHomeId,
    status: "draft",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const dailyEpisodeDrafts = [
  {
    id: "82600000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    source_candidate_id: "81400000-0000-4000-8000-000000000001",
    title: "Festival morning",
    summary: "Guide starts the day by checking the festival list.",
    scene_beat_draft_id: "82500000-0000-4000-8000-000000000001",
    participant_agent_ids: [agentGuideId],
    status: "draft",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const groupInteractions = [
  {
    id: "82700000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    context_key: "club-meeting",
    title: "Club meeting",
    interaction_type: "club",
    scene_id: sceneHomeId,
    organization_id: "81000000-0000-4000-8000-000000000001",
    participant_agent_ids: [agentGuideId],
    participant_roles: { [agentGuideId]: "advisor" },
    constraints: { location_required: true },
    status: "planned",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const relationshipSuggestions = [
  {
    id: "82800000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    relationship_id: "30500000-0000-4000-8000-000000000001",
    source_agent_id: agentGuideId,
    target_agent_id: agentGuideId,
    title: "Guide self-reflection",
    reason: "Trust is stable and an unresolved promise exists.",
    suggested_event_name: "living_world.relationship_reflection",
    score: 60,
    status: "suggested",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const organizationConflicts = [
  {
    id: "82900000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    organization_id: "81000000-0000-4000-8000-000000000001",
    faction_track_id: "81200000-0000-4000-8000-000000000001",
    title: "Festival budget pressure",
    summary: "Budget pressure rises around festival planning.",
    pressure_delta: 5,
    progress_delta: 2,
    status: "proposed",
    resolved_event_id: null,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const rumors = [
  {
    id: "83000000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    rumor_key: "late-rehearsal",
    title: "Late rehearsal rumor",
    content: "Someone saw the club room lights after closing.",
    source_agent_id: agentGuideId,
    source_organization_id: null,
    visibility: "group",
    known_agent_ids: [agentGuideId],
    status: "active",
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
  },
];
const rumorPropagations = [
  {
    id: "83100000-0000-4000-8000-000000000001",
    world_id: worldOneId,
    worldline_id: primaryWorldlineId,
    rumor_id: "83000000-0000-4000-8000-000000000001",
    source_agent_id: agentGuideId,
    target_agent_id: agentGuideId,
    target_organization_id: null,
    propagation_reason: "Shared after class.",
    status: "pending",
    delivered_event_id: null,
    metadata: {},
    created_at: "2026-04-17T00:00:00.000Z",
    updated_at: "2026-04-17T00:00:00.000Z",
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
    worldline_id: primaryWorldlineId,
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
    worldline_id: primaryWorldlineId,
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
    worldline_id: primaryWorldlineId,
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
    id: "73000000-0000-4000-8000-000000000004",
    world_id: worldOneId,
    agent_id: null,
    source_run_id: null,
    source_conversation_id: null,
    title: "Publication blocker draft",
    content: "Hidden secret leak exposes the route key before the reveal.",
    artifact_kind: "world_summary",
    metadata: {},
    created_at: "2026-04-17T00:03:02.500Z",
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
    id: "73000000-0000-4000-8000-000000000005",
    world_id: worldOneId,
    agent_id: agentGuideId,
    source_run_id: null,
    source_conversation_id: null,
    title: "Published agent field note",
    content: "Agent note visible in the reader.",
    artifact_kind: "agent_note",
    metadata: {},
    created_at: "2026-04-17T00:03:01.500Z",
    publication: {
      id: "73500000-0000-4000-8000-000000000005",
      world_id: worldOneId,
      artifact_id: "73000000-0000-4000-8000-000000000005",
      source_draft_id: "73000000-0000-4000-8000-000000000005",
      status: "published",
      reader_visible: true,
      metadata: { channel: "reader" },
      published_at: "2026-04-17T00:04:00.000Z",
      unpublished_at: null,
      published_by_user_id: adminUserId,
      created_at: "2026-04-17T00:04:00.000Z",
      updated_at: "2026-04-17T00:04:00.000Z",
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
const snapshots = new Map([
  [
    worldOneId,
    {
      id: seedSnapshotId,
      world_id: worldOneId,
      worldline_id: primaryWorldlineId,
      covers_event_sequence: 1,
      schema_version: "world_state.v1",
      status: "complete",
      payload: { clock: { revision: 1 }, agents: [] },
      payload_uri: `object://worlds/${worldOneId}/worldlines/${primaryWorldlineId}/snapshots/1.json`,
      metadata: {},
      created_by_event_id: "76000000-0000-4000-8000-000000000001",
      created_at: "2026-04-17T00:03:05.000Z",
      updated_at: "2026-04-17T00:03:05.000Z",
    },
  ],
]);
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
        worldline_id: primaryWorldlineId,
        sequence: 1,
        event_name: "world.clock_advanced",
        importance: "system",
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

  if (url.pathname === "/plugins/bindings") {
    handlePluginBindings(request, url, response);
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
    await handleAgentPresetItem(request, response, presetSegments[2], presetSegments[3]);
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
    worldlines.push(primaryWorldlineFor(world.id));
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
  if (resource === "location-edges") {
    await handleLocationEdges(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "organizations") {
    await handleOrganizations(request, response, currentSubject, worldId, segments[3], segments[4], segments[5]);
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
  if (resource === "bible") {
    await handleWorldBible(request, response, currentSubject, worldId);
    return;
  }
  if (resource === "worldlines") {
    await handleWorldlines(request, response, currentSubject, worldId, segments[3], segments[4], segments[5]);
    return;
  }
  if (resource === "gm") {
    await handleGM(request, response, currentSubject, worldId, segments[3], segments[4], segments[5]);
    return;
  }
  if (resource === "resolution-rules") {
    await handleResolutionRules(request, response, currentSubject, worldId, segments[3], segments[4]);
    return;
  }
  if (resource === "player-actors") {
    await handlePlayerActors(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "player-choices") {
    await handlePlayerChoices(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "living-world-dashboard") {
    handleLivingWorldDashboard(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "knowledge") {
    await handleKnowledgeFacts(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "secrets") {
    await handleSecrets(request, response, currentSubject, worldId, segments[3], segments[4], url);
    return;
  }
  if (resource === "emotional-states") {
    await handleEmotionalStates(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "relationship-repairs") {
    await handleRelationshipRepairs(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "player-journal") {
    await handlePlayerJournal(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "notifications") {
    await handleNotifications(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "interventions") {
    await handleInterventions(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "gm-style-reviews") {
    await handleGMStyleReviews(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "narrative-continuity-reviews") {
    await handleNarrativeContinuityReviews(request, response, currentSubject, worldId, url);
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
  if (resource === "daily-life") {
    await handleDailyLife(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "offscreen-events") {
    await handleOffscreenEvents(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "story-hooks") {
    await handleStoryHooks(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "plot-threads") {
    await handlePlotThreads(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "route-affinities") {
    await handleRouteAffinities(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "route-milestones") {
    await handleRouteMilestones(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "ending-candidates") {
    await handleEndingCandidates(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "long-run-evals") {
    await handleLongRunEvals(request, response, currentSubject, worldId, url);
    return;
  }
  if (resource === "authoring-templates") {
    await handleAuthoringTemplates(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "release-profile") {
    await handleReleaseProfile(request, response, currentSubject, worldId);
    return;
  }
  if (resource === "beta-checklists") {
    await handleBetaChecklists(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "event-trigger-conditions") {
    await handleEventTriggerConditions(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "scene-beats") {
    await handleSceneBeats(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "daily-episodes") {
    await handleDailyEpisodes(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "group-interactions") {
    await handleGroupInteractions(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "relationship-suggestions") {
    await handleRelationshipSuggestions(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      url,
    );
    return;
  }
  if (resource === "organization-conflicts") {
    await handleOrganizationConflicts(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
    return;
  }
  if (resource === "rumors") {
    await handleRumors(request, response, currentSubject, worldId, segments[3], url);
    return;
  }
  if (resource === "rumor-propagations") {
    await handleRumorPropagations(
      request,
      response,
      currentSubject,
      worldId,
      segments[3],
      segments[4],
      url,
    );
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

async function handleWorldBible(request, response, currentSubject, worldId) {
  if (request.method === "GET") {
    sendJson(response, 200, worldBibles.get(worldId) ?? null);
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
  if (request.method === "PUT") {
    const body = await readJson(request);
    const existing = worldBibles.get(worldId);
    const bible = {
      id: existing?.id ?? randomUUID(),
      world_id: worldId,
      source_material: body.source_material ?? "",
      canon_timeline: body.canon_timeline ?? [],
      setting_rules: body.setting_rules ?? [],
      forbidden_changes: body.forbidden_changes ?? [],
      sequel_boundaries: body.sequel_boundaries ?? [],
      continuity_config: body.continuity_config ?? {},
      metadata: body.metadata ?? {},
      continuity_status: body.continuity_config?.status ?? null,
      created_at: existing?.created_at ?? new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    worldBibles.set(worldId, bible);
    sendJson(response, 200, bible);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleWorldlines(request, response, currentSubject, worldId, action, baseId, compareId) {
  if (request.method === "GET" && action === undefined) {
    sendJson(response, 200, worldlines.filter((worldline) => worldline.world_id === worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && action !== undefined && baseId === "compare" && compareId !== undefined) {
    const choices = playerChoices.filter((choice) => choice.worldline_id === compareId);
    sendJson(response, 200, {
      base_worldline_id: action,
      compare_worldline_id: compareId,
      fork_event_sequence: worldlines.find((worldline) => worldline.id === compareId)?.fork_event_sequence ?? null,
      divergent_event_count: choices.length,
      relationship_delta_count: 0,
      faction_delta_count: 0,
      choice_delta_count: choices.length,
    });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === "fork") {
    const body = await readJson(request);
    const source = body.source_worldline_id === undefined || body.source_worldline_id === null
      ? worldlines.find((worldline) => worldline.world_id === worldId && worldline.parent_worldline_id === null)
      : worldlines.find((worldline) => worldline.id === body.source_worldline_id && worldline.world_id === worldId);
    const fork = {
      id: randomUUID(),
      world_id: worldId,
      worldline_key: body.worldline_key,
      name: body.name,
      description: body.description ?? null,
      parent_worldline_id: source?.id ?? null,
      forked_from_snapshot_id: body.forked_from_snapshot_id ?? null,
      fork_event_sequence: body.fork_event_sequence ?? replayForWorld(worldId).source_sequence,
      status: "active",
      created_by_actor_ref: `user:${currentSubject.user_id}`,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    worldlines.push(fork);
    sendJson(response, 201, fork);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleGM(request, response, currentSubject, worldId, resource, resourceId, action) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (resource === "agendas") {
    await handleGMAgendas(request, response, currentSubject, worldId, resourceId);
    return;
  }
  if (resource === "macro-plan") {
    await handleGMMacroPlan(request, response, worldId);
    return;
  }
  if (resource === "proposals") {
    await handleGMProposals(request, response, currentSubject, worldId, resourceId, action);
    return;
  }
  sendJson(response, 404, { detail: "not found" });
}

async function handleGMAgendas(request, response, currentSubject, worldId, agendaId) {
  if (request.method === "GET" && agendaId === undefined) {
    sendJson(response, 200, gmAgendas.filter((agenda) => agenda.world_id === worldId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && agendaId === undefined) {
    const body = await readJson(request);
    const agenda = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      title: body.title,
      summary: body.summary,
      priority: body.priority ?? 50,
      status: "active",
      focus_agents: body.focus_agents ?? [],
      focus_organizations: body.focus_organizations ?? [],
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    gmAgendas.push(agenda);
    sendJson(response, 201, agenda);
    return;
  }
  const agenda = gmAgendas.find((item) => item.id === agendaId && item.world_id === worldId);
  if (agenda === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(agenda, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, agenda);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleGMMacroPlan(request, response, worldId) {
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method !== "POST") {
    sendJson(response, 405, { detail: "method not allowed" });
    return;
  }
  const body = await readJson(request);
  const worldlineId = body.worldline_id ?? primaryWorldlineId;
  const plannedItems = resolutionRules
    .filter((rule) => rule.world_id === worldId && rule.status === "active")
    .flatMap((rule) => {
      const proposals = Array.isArray(rule.effects?.proposals) ? rule.effects.proposals : [];
      const offscreen = Array.isArray(rule.effects?.offscreen_events)
        ? rule.effects.offscreen_events
        : [];
      return [
        ...proposals.map((proposal, index) => ({
          item_kind: "proposal",
          rule_id: rule.id,
          rule_key: rule.rule_key,
          priority: rule.priority,
          title: proposal.title ?? rule.name,
          payload: proposal,
          source_context: {
            source: "gm_macro_planner",
            rule_id: rule.id,
            rule_key: rule.rule_key,
            effect_index: index,
          },
        })),
        ...offscreen.map((item, index) => ({
          item_kind: "offscreen_event",
          rule_id: rule.id,
          rule_key: rule.rule_key,
          priority: rule.priority,
          title: item.title ?? rule.name,
          payload: item,
          source_context: {
            source: "gm_macro_planner",
            rule_id: rule.id,
            rule_key: rule.rule_key,
            effect_index: index,
          },
        })),
      ];
    })
    .slice(0, body.limit ?? 20);
  const execution = body.execute
    ? {
        proposal_count: plannedItems.filter((item) => item.item_kind === "proposal").length,
        offscreen_event_count: plannedItems.filter((item) => item.item_kind === "offscreen_event").length,
        proposal_ids: [],
        offscreen_event_ids: [],
      }
    : null;
  sendJson(response, 200, {
    world_id: worldId,
    worldline_id: worldlineId,
    planned_items: plannedItems,
    diagnostics: plannedItems.length === 0 ? ["No matched GM macro effects."] : [],
    execution,
  });
}

async function handleGMProposals(request, response, currentSubject, worldId, proposalId, action) {
  if (request.method === "GET" && proposalId === undefined) {
    sendJson(response, 200, gmProposals.filter((proposal) => proposal.world_id === worldId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && proposalId === undefined) {
    const body = await readJson(request);
    const proposal = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      agenda_id: body.agenda_id ?? null,
      title: body.title,
      reason: body.reason,
      event_name: body.event_name,
      proposed_payload: body.proposed_payload ?? {},
      importance: body.importance ?? "daily",
      risk_score: body.risk_score ?? 0,
      affected_agents: body.affected_agents ?? [],
      affected_organizations: body.affected_organizations ?? [],
      source_context: body.source_context ?? {},
      status: "proposed",
      review_note: null,
      resolved_event_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    gmProposals.push(proposal);
    sendJson(response, 201, proposal);
    return;
  }
  const proposal = gmProposals.find((item) => item.id === proposalId && item.world_id === worldId);
  if (proposal === undefined || action !== "review") {
    if (proposal !== undefined && action === "draft-low-risk" && request.method === "POST") {
      if (proposal.risk_score > 25 || proposal.importance !== "daily") {
        sendJson(response, 422, {
          detail: "only low-risk daily proposals can become deterministic drafts",
        });
        return;
      }
      const payload = proposal.proposed_payload ?? {};
      const participantAgentIds = Array.isArray(payload.participant_agent_ids)
        ? payload.participant_agent_ids
        : [agentGuideId];
      const sceneId = payload.scene_id ?? sceneHomeId;
      const now = new Date().toISOString();
      const beat = {
        id: randomUUID(),
        world_id: worldId,
        worldline_id: proposal.worldline_id ?? primaryWorldlineId,
        source_kind: "proposal",
        source_ref: proposal.id,
        title: proposal.title,
        setup: `Set up ${proposal.title}.`,
        dialogue_beats: participantAgentIds.map((agentId) => ({
          speaker: agentFor(agentId)?.agent_key ?? agentId,
          intent: "advance a low-risk daily beat",
        })),
        choice_points: [],
        aftermath: proposal.reason,
        participant_agent_ids: participantAgentIds,
        scene_id: sceneId,
        status: "draft",
        metadata: { source: "gm_low_risk_proposal", proposal_id: proposal.id },
        created_at: now,
        updated_at: now,
      };
      sceneBeatDrafts.push(beat);
      sendJson(response, 200, sceneBeatResponse(beat));
      return;
    }
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  const body = await readJson(request);
  proposal.status = body.status;
  proposal.review_note = body.review_note ?? null;
  proposal.resolved_event_id = body.status === "resolved" ? randomUUID() : proposal.resolved_event_id;
  proposal.updated_at = new Date().toISOString();
  sendJson(response, 200, proposal);
}

async function handleResolutionRules(request, response, currentSubject, worldId, ruleId, action) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && ruleId === undefined) {
    sendJson(response, 200, resolutionRules.filter((rule) => rule.world_id === worldId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && ruleId === undefined) {
    const body = await readJson(request);
    const rule = {
      id: randomUUID(),
      world_id: worldId,
      rule_key: body.rule_key,
      name: body.name,
      description: body.description ?? null,
      priority: body.priority ?? 50,
      status: "active",
      conditions: body.conditions ?? {},
      effects: body.effects ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    resolutionRules.push(rule);
    sendJson(response, 201, rule);
    return;
  }
  const rule = resolutionRules.find((item) => item.id === ruleId && item.world_id === worldId);
  if (rule === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "dry-run") {
    sendJson(response, 200, {
      rule_id: rule.id,
      rule_key: rule.rule_key,
      matched: true,
      reasons: ["Rule conditions are satisfied."],
      effects: rule.effects,
    });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(rule, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, rule);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleStoryHooks(request, response, currentSubject, worldId, hookId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && hookId === undefined) {
    sendJson(response, 200, storyHooks.filter((hook) => matchesWorldline(hook, worldId, url)));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && hookId === undefined) {
    const body = await readJson(request);
    const hook = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      hook_key: body.hook_key,
      title: body.title,
      hook_type: body.hook_type,
      summary: body.summary,
      status: "open",
      priority: body.priority ?? 50,
      owner_agent_id: body.owner_agent_id ?? null,
      target_agent_id: body.target_agent_id ?? null,
      source_event_id: null,
      due_at: body.due_at ?? null,
      resolution: null,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    storyHooks.push(hook);
    sendJson(response, 201, storyHookResponse(hook));
    return;
  }
  const hook = storyHooks.find((item) => item.id === hookId && item.world_id === worldId);
  if (hook === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(hook, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, storyHookResponse(hook));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handlePlotThreads(request, response, currentSubject, worldId, threadId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && threadId === undefined) {
    sendJson(
      response,
      200,
      plotThreads.filter((thread) => matchesWorldline(thread, worldId, url)),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && threadId === undefined) {
    const body = await readJson(request);
    const thread = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      thread_key: body.thread_key,
      title: body.title,
      thread_type: body.thread_type,
      status: "active",
      summary: body.summary,
      stakes: body.stakes ?? null,
      next_beats: body.next_beats ?? [],
      participant_agent_ids: body.participant_agent_ids ?? [],
      organization_ids: body.organization_ids ?? [],
      related_event_ids: [],
      priority: body.priority ?? 50,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    plotThreads.push(thread);
    sendJson(response, 201, thread);
    return;
  }
  const thread = plotThreads.find((item) => item.id === threadId && item.world_id === worldId);
  if (thread === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(thread, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, thread);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleRouteAffinities(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    const agentId = url.searchParams.get("agent_id");
    const status = url.searchParams.get("status");
    sendJson(
      response,
      200,
      routeAffinities
        .filter((route) => matchesWorldline(route, worldId, url))
        .filter((route) => agentId === null || route.agent_id === agentId)
        .filter((route) => status === null || route.status === status)
        .map(routeAffinityResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PUT") {
    const body = await readJson(request);
    const worldlineId = body.worldline_id ?? primaryWorldlineId;
    let route = routeAffinities.find(
      (item) =>
        item.world_id === worldId
        && item.worldline_id === worldlineId
        && item.agent_id === body.agent_id
        && item.route_key === body.route_key,
    );
    if (route === undefined) {
      route = {
        id: randomUUID(),
        world_id: worldId,
        worldline_id: worldlineId,
        agent_id: body.agent_id,
        route_key: body.route_key,
        status: body.status ?? "available",
        affinity: body.affinity ?? 0,
        stage: body.stage ?? 0,
        flags: body.flags ?? [],
        last_choice_id: null,
        metadata: body.metadata ?? {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      routeAffinities.push(route);
    } else {
      Object.assign(route, body, { updated_at: new Date().toISOString() });
    }
    sendJson(response, 200, routeAffinityResponse(route));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleRouteMilestones(request, response, currentSubject, worldId, milestoneId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && milestoneId === undefined) {
    const status = url.searchParams.get("status");
    sendJson(
      response,
      200,
      routeMilestones
        .filter((milestone) => matchesWorldline(milestone, worldId, url))
        .filter((milestone) => status === null || milestone.status === status)
        .map(routeMilestoneResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && milestoneId === undefined) {
    const body = await readJson(request);
    const milestone = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      route_affinity_id: body.route_affinity_id ?? null,
      plot_thread_id: body.plot_thread_id ?? null,
      agent_id: body.agent_id ?? null,
      milestone_key: body.milestone_key,
      title: body.title,
      description: body.description ?? null,
      stage: body.stage ?? 0,
      status: body.status ?? "planned",
      conditions: body.conditions ?? {},
      evidence_metadata: body.evidence_metadata ?? {},
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    routeMilestones.push(milestone);
    sendJson(response, 201, routeMilestoneResponse(milestone));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleEndingCandidates(
  request,
  response,
  currentSubject,
  worldId,
  endingId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && endingId === undefined) {
    const status = url.searchParams.get("status");
    const endingType = url.searchParams.get("ending_type");
    sendJson(
      response,
      200,
      endingCandidates
        .filter((ending) => matchesWorldline(ending, worldId, url))
        .filter((ending) => status === null || ending.status === status)
        .filter((ending) => endingType === null || ending.ending_type === endingType)
        .map(endingCandidateResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && endingId === undefined) {
    const body = await readJson(request);
    const ending = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      route_affinity_id: body.route_affinity_id ?? null,
      plot_thread_id: body.plot_thread_id ?? null,
      agent_id: body.agent_id ?? null,
      ending_key: body.ending_key,
      title: body.title,
      ending_type: body.ending_type ?? "normal",
      status: body.status ?? "planned",
      requirements: body.requirements ?? {},
      outcome_summary: body.outcome_summary ?? null,
      evidence_metadata: body.evidence_metadata ?? {},
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    endingCandidates.push(ending);
    sendJson(response, 201, endingCandidateResponse(ending));
    return;
  }
  const ending = endingCandidates.find((item) => item.id === endingId && item.world_id === worldId);
  if (ending === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "dry-run") {
    const route =
      ending.route_affinity_id === null
        ? null
        : routeAffinities.find((item) => item.id === ending.route_affinity_id);
    const minRouteStage = Number(ending.requirements.min_route_stage ?? 0);
    const stage = Number(route?.stage ?? 0);
    sendJson(response, 200, {
      ending_id: ending.id,
      ending_key: ending.ending_key,
      matched: stage >= minRouteStage,
      satisfied: stage >= minRouteStage ? [`route_stage >= ${minRouteStage}`] : [],
      unsatisfied: stage >= minRouteStage ? [] : [`route_stage < ${minRouteStage}`],
      evidence: { route_stage: stage, requirement: minRouteStage },
    });
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleLongRunEvals(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, longRunEvals.filter((run) => matchesWorldline(run, worldId, url)));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST") {
    const body = await readJson(request);
    const worldlineId = body.worldline_id ?? primaryWorldlineId;
    const eventCount = (worldEvents.get(worldId) ?? []).filter(
      (event) => event.worldline_id === worldlineId,
    ).length;
    const refs = evidenceRefsForWorldline(worldId, worldlineId);
    const eventsByImportance = {};
    const eventsByDay = {};
    const eventsByActor = {};
    for (const event of (worldEvents.get(worldId) ?? []).filter(
      (item) => item.worldline_id === worldlineId,
    )) {
      eventsByImportance[event.importance] = (eventsByImportance[event.importance] ?? 0) + 1;
      const day = event.world_time?.slice(0, 10) ?? "wall-time-only";
      eventsByDay[day] = (eventsByDay[day] ?? 0) + 1;
      const actorGroup = event.actor_ref.split(":", 1)[0];
      eventsByActor[actorGroup] = (eventsByActor[actorGroup] ?? 0) + 1;
    }
    const run = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: worldlineId,
      eval_key: body.eval_key,
      horizon_days: body.horizon_days ?? 7,
      status: eventCount === 0 ? "warning" : "completed",
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      metrics: {
        horizon_days: body.horizon_days ?? 7,
        events: eventCount,
        snapshots: refs.filter((ref) => ref.kind === "snapshot").length,
        route_count: routeAffinities.length,
        distribution: {
          events_by_importance: eventsByImportance,
          events_by_day: eventsByDay,
          events_by_actor: eventsByActor,
          day_coverage: Object.keys(eventsByDay).length,
        },
        traceability: {
          choice_event_count: refs.filter((ref) => ref.kind === "player_choice").length,
          event_ref_count: refs.filter((ref) => ref.kind === "world_event").length,
          snapshot_ref_count: refs.filter((ref) => ref.kind === "snapshot").length,
          refs,
        },
        review_warnings: {
          continuity_or_style_warning_count: narrativeContinuityReviews.filter(
            (review) => review.worldline_id === worldlineId && review.status === "warning",
          ).length,
          continuity_fail_count: narrativeContinuityReviews.filter(
            (review) => review.worldline_id === worldlineId && review.status === "fail",
          ).length,
          publication_gate_warning_count: 0,
        },
      },
      recommendations:
        eventCount === 0
          ? [{ action: "seed_world_events", reason: "no event activity in eval window" }]
          : [{ action: "review_daily_density", reason: "keep route and daily beats balanced" }],
      blockers: [],
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    longRunEvals.unshift(run);
    sendJson(response, 201, run);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAuthoringTemplates(
  request,
  response,
  currentSubject,
  worldId,
  templateId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && templateId === undefined) {
    const kind = url.searchParams.get("template_kind");
    sendJson(
      response,
      200,
      authoringTemplates
        .filter((template) => template.world_id === worldId)
        .filter((template) => kind === null || template.template_kind === kind),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && templateId === undefined) {
    const body = await readJson(request);
    const template = {
      id: randomUUID(),
      world_id: worldId,
      template_key: body.template_key,
      template_kind: body.template_kind,
      name: body.name,
      description: body.description ?? null,
      content: body.content ?? {},
      validation_issues: [],
      is_active: true,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    authoringTemplates.push(template);
    sendJson(response, 201, template);
    return;
  }
  const template = authoringTemplates.find(
    (item) => item.id === templateId && item.world_id === worldId,
  );
  if (template === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && (action === "preview" || action === "apply")) {
    const body = await readJson(request);
    const targetWorldlineId = body.target_worldline_id ?? primaryWorldlineId;
    const schemaVersion = template.content.schema_version ?? "living-world-template/v2";
    const characters = Array.isArray(template.content.characters) ? template.content.characters : [];
    const events = Array.isArray(template.content.events) ? template.content.events : [];
    const routes = Array.isArray(template.content.routes) ? template.content.routes : [];
    const appliedRefs =
      action === "apply"
        ? {
            template_id: template.id,
            target_worldline_id: targetWorldlineId,
            refs: [
              {
                kind: "authoring_template",
                id: template.id,
                label: template.template_key,
                worldline_id: targetWorldlineId,
                action: "applied",
              },
            ],
          }
        : {};
    const job = {
      id: randomUUID(),
      world_id: worldId,
      template_id: template.id,
      status: action === "apply" ? "applied" : "preview",
      preview_summary: {
        schema_version: schemaVersion,
        template_key: template.template_key,
        template_kind: template.template_kind,
        source_notes: Array.isArray(template.content.source_notes)
          ? template.content.source_notes.length
          : 0,
        character_count: characters.length,
        event_template_count: events.length,
        route_template_count: routes.length,
        validation_issue_count: template.validation_issues.length,
        target_worldline_id: targetWorldlineId,
        diff: {
          characters: characters.map((item) => item.agent_key ?? ""),
          events: events.map((item) => item.event_key ?? item.event_name ?? ""),
          routes: routes.map((item) => item.route_key ?? ""),
        },
        audit: {
          template_id: template.id,
          template_key: template.template_key,
          schema_version: schemaVersion,
        },
      },
      applied_refs: appliedRefs,
      validation_issues: template.validation_issues,
      metadata: {
        ...(body.metadata ?? {}),
        target_worldline_id: targetWorldlineId,
        duplicate_policy: body.duplicate_policy ?? "upsert",
        audit: {
          action,
          schema_version: schemaVersion,
          template_id: template.id,
          target_worldline_id: targetWorldlineId,
        },
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    authoringImportJobs.unshift(job);
    sendJson(response, 200, job);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleReleaseProfile(request, response, currentSubject, worldId) {
  if (request.method === "GET") {
    sendJson(response, 200, releaseProfiles.get(worldId) ?? null);
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
  if (request.method === "PUT") {
    const body = await readJson(request);
    const existing = releaseProfiles.get(worldId);
    const gateDecision = gateDecisionForRelease(worldId, body.status ?? existing?.status ?? "draft", body);
    if (!gateDecision.allowed) {
      const detail = gateDecision.blockers
        .map((blocker) =>
          blocker.code && blocker.message
            ? `${blocker.code}: ${blocker.message}`
            : String(blocker.message ?? blocker.code),
        )
        .join(", ");
      sendJson(response, 422, { detail: detail || "release gate blocked status change" });
      return;
    }
    const profile = {
      id: existing?.id ?? randomUUID(),
      world_id: worldId,
      profile_key: body.profile_key ?? existing?.profile_key ?? "living-world-beta",
      status: body.status ?? existing?.status ?? "draft",
      branch_policy: body.branch_policy ?? existing?.branch_policy ?? {},
      backup_policy: body.backup_policy ?? existing?.backup_policy ?? {},
      content_review_policy:
        body.content_review_policy ?? existing?.content_review_policy ?? {},
      player_permission_policy:
        body.player_permission_policy ?? existing?.player_permission_policy ?? {},
      worldline_policy: body.worldline_policy ?? existing?.worldline_policy ?? {},
      checklist: { ...(body.checklist ?? existing?.checklist ?? {}), gate_decision: gateDecision },
      metadata: { ...(body.metadata ?? existing?.metadata ?? {}), gate_decision: gateDecision },
      created_at: existing?.created_at ?? new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    releaseProfiles.set(worldId, profile);
    sendJson(response, 200, profile);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleBetaChecklists(
  request,
  response,
  currentSubject,
  worldId,
  runId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && runId === undefined) {
    sendJson(
      response,
      200,
      betaChecklistRuns.filter((run) => matchesWorldline(run, worldId, url)),
    );
    return;
  }
  if (request.method === "GET" && action === "items") {
    sendJson(response, 200, betaChecklistItems.filter((item) => item.run_id === runId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && runId === undefined) {
    const body = await readJson(request);
    const worldlineId = body.worldline_id ?? primaryWorldlineId;
    const refs = evidenceRefsForWorldline(worldId, worldlineId);
    const run = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: worldlineId,
      run_key: body.run_key ?? "sample-world-beta",
      status: longRunEvals.length === 0 ? "blocked" : "passed",
      summary:
        longRunEvals.length === 0
          ? "Beta checklist is blocked until a long-run eval exists."
          : "Sample world beta has structured release evidence.",
      evidence: {
        refs,
        items: { "seven-day-simulation": { eval_runs: longRunEvals.length, refs } },
        worldline_id: worldlineId,
      },
      blocker_count: longRunEvals.length === 0 ? 1 : 0,
      created_by_actor_ref: `user:${currentSubject.user_id}`,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    const item = {
      id: randomUUID(),
      run_id: run.id,
      item_key: "seven-day-simulation",
      title: "7-day simulation",
      status: run.blocker_count === 0 ? "passed" : "blocked",
      evidence: { eval_runs: longRunEvals.length, refs },
      recommendation:
        run.blocker_count === 0
          ? null
          : "Run a seven-day eval before beta validation.",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    betaChecklistRuns.unshift(run);
    betaChecklistItems.push(item);
    sendJson(response, 201, run);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleEventTriggerConditions(
  request,
  response,
  currentSubject,
  worldId,
  conditionId,
  action,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && conditionId === undefined) {
    sendJson(
      response,
      200,
      triggerConditions.filter((condition) => condition.world_id === worldId),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && conditionId === undefined) {
    const body = await readJson(request);
    const condition = {
      id: randomUUID(),
      world_id: worldId,
      condition_key: body.condition_key,
      name: body.name,
      description: body.description ?? null,
      status: "active",
      priority: body.priority ?? 50,
      conditions: body.conditions ?? {},
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    triggerConditions.push(condition);
    sendJson(response, 201, condition);
    return;
  }
  const condition = triggerConditions.find(
    (item) => item.id === conditionId && item.world_id === worldId,
  );
  if (condition === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "dry-run") {
    const openHookCount = storyHooks.filter(
      (hook) => hook.world_id === worldId && hook.status === "open",
    ).length;
    const minOpenHooks = Number(condition.conditions.min_open_hooks ?? 0);
    sendJson(response, 200, {
      condition_id: condition.id,
      condition_key: condition.condition_key,
      matched: openHookCount >= minOpenHooks,
      satisfied: openHookCount >= minOpenHooks ? [`open_hooks >= ${minOpenHooks}`] : [],
      unsatisfied: openHookCount >= minOpenHooks ? [] : [`open_hooks < ${minOpenHooks}`],
    });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(condition, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, condition);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleSceneBeats(request, response, currentSubject, worldId, beatId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && beatId === undefined) {
    sendJson(
      response,
      200,
      sceneBeatDrafts.filter((beat) => matchesWorldline(beat, worldId, url)).map(sceneBeatResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && beatId === undefined) {
    const body = await readJson(request);
    const beat = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      source_kind: body.source_kind ?? "manual",
      source_ref: body.source_ref ?? null,
      title: body.title,
      setup: `${body.title} setup`,
      dialogue_beats: [{ intent: "deterministic draft" }],
      choice_points: [{ prompt: "Respond?", options: ["Act", "Observe"] }],
      aftermath: `${body.title} aftermath`,
      participant_agent_ids: body.participant_agent_ids ?? [],
      scene_id: body.scene_id ?? null,
      status: "draft",
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    sceneBeatDrafts.push(beat);
    sendJson(response, 201, sceneBeatResponse(beat));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleDailyEpisodes(request, response, currentSubject, worldId, episodeId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && episodeId === undefined) {
    sendJson(
      response,
      200,
      dailyEpisodeDrafts.filter((episode) => matchesWorldline(episode, worldId, url)),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && episodeId === undefined) {
    const body = await readJson(request);
    const episode = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      source_candidate_id: body.source_candidate_id ?? null,
      title: body.title ?? "Daily episode draft",
      summary: body.title ?? "Daily episode draft",
      scene_beat_draft_id: null,
      participant_agent_ids: [agentGuideId],
      status: "draft",
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    dailyEpisodeDrafts.push(episode);
    sendJson(response, 201, episode);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleGroupInteractions(
  request,
  response,
  currentSubject,
  worldId,
  contextId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && contextId === undefined) {
    sendJson(
      response,
      200,
      groupInteractions
        .filter((context) => matchesWorldline(context, worldId, url))
        .map(groupInteractionResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && contextId === undefined) {
    const body = await readJson(request);
    const context = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      context_key: body.context_key,
      title: body.title,
      interaction_type: body.interaction_type,
      scene_id: body.scene_id ?? null,
      organization_id: body.organization_id ?? null,
      participant_agent_ids: body.participant_agent_ids ?? [],
      participant_roles: body.participant_roles ?? {},
      constraints: body.constraints ?? {},
      status: "planned",
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    groupInteractions.push(context);
    sendJson(response, 201, groupInteractionResponse(context));
    return;
  }
  const context = groupInteractions.find((item) => item.id === contextId && item.world_id === worldId);
  if (context === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "execute") {
    if (context.status === "completed" || context.status === "archived") {
      sendJson(response, 409, { detail: "group interaction cannot be executed from this status" });
      return;
    }
    if (context.participant_agent_ids.length === 0) {
      sendJson(response, 422, { detail: "group interaction requires participants" });
      return;
    }
    const body = await readJson(request);
    const now = new Date().toISOString();
    const groupContext = {
      group_interaction_context_id: context.id,
      context_key: context.context_key,
      title: context.title,
      interaction_type: context.interaction_type,
      scene_id: context.scene_id,
      organization_id: context.organization_id,
      participant_roles: context.participant_roles,
      constraints: context.constraints,
      metadata: context.metadata,
    };
    const session = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: context.worldline_id ?? primaryWorldlineId,
      scene_id: context.scene_id,
      session_key: body.session_key ?? `group-${context.context_key}`,
      title: context.title,
      scope_type: context.scene_id === null ? "world" : "scene",
      mode: body.mode ?? "manual_chain",
      status: "draft",
      objective:
        body.objective ??
        context.constraints?.objective ??
        `Run group interaction ${context.title} with configured participant roles.`,
      opening_prompt: body.opening_prompt ?? context.title,
      max_turns: body.max_turns ?? 12,
      next_turn_index: 0,
      policy: body.policy ?? {
        error_policy: "fail_session",
        max_consecutive_failed_turns: 1,
        loop_guard_window: 4,
        repeat_output_threshold: 2,
        speaker_policy: "round_robin",
        manual_next_agent_id: null,
        participant_repeat_cooldown: 0,
        min_enabled_participants: 1,
        max_turn_budget: null,
      },
      writer_config: body.writer_config ?? {
        provider_profile_id: null,
        writer_plugin_identifier: "builtin.default_narrative_writer",
        writer_plugin_config: { group_context: groupContext },
        auto_generate_on_complete: false,
        generate_summary: true,
        generate_chapter: true,
        style_guide: "",
        target_length: "standard",
        source_constraints: "",
        include_prompt_preview: true,
      },
      memory_config: body.memory_config ?? {
        write_turn_memory: true,
        retrieve_memory: true,
        max_context_items: 5,
        query_window: 8,
        include_recent_turns: true,
        include_agent_observations: true,
        memory_query_strategy: "prompt",
      },
      group_context: groupContext,
      terminal_reason: null,
      created_at: now,
      updated_at: now,
    };
    session.writer_config.writer_plugin_config = {
      ...(session.writer_config.writer_plugin_config ?? {}),
      group_context: groupContext,
    };
    conversations.push(session);
    conversationParticipants.push(
      ...context.participant_agent_ids.map((agentId, index) => ({
        id: randomUUID(),
        session_id: session.id,
        agent_id: agentId,
        turn_order: index,
        is_enabled: true,
        created_at: now,
        updated_at: now,
      })),
    );
    context.status = "active";
    context.metadata = { ...(context.metadata ?? {}), conversation_session_id: session.id };
    context.updated_at = now;
    sendJson(response, 200, {
      group_context: groupInteractionResponse(context),
      session,
    });
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleRelationshipSuggestions(request, response, currentSubject, worldId, action, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && action === undefined) {
    sendJson(
      response,
      200,
      relationshipSuggestions
        .filter((suggestion) => matchesWorldline(suggestion, worldId, url))
        .map(relationshipSuggestionResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === "generate") {
    const suggestion = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: url.searchParams.get("worldline_id") ?? primaryWorldlineId,
      relationship_id: "30500000-0000-4000-8000-000000000001",
      source_agent_id: agentGuideId,
      target_agent_id: agentGuideId,
      title: "Generated relationship beat",
      reason: "Deterministic mock suggestion from relationship tension.",
      suggested_event_name: "living_world.relationship_suggestion",
      score: 55,
      status: "suggested",
      metadata: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    relationshipSuggestions.push(suggestion);
    sendJson(response, 200, [relationshipSuggestionResponse(suggestion)]);
    return;
  }
  const suggestion = relationshipSuggestions.find(
    (item) => item.id === action && item.world_id === worldId,
  );
  if (suggestion === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(suggestion, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, relationshipSuggestionResponse(suggestion));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleOrganizationConflicts(
  request,
  response,
  currentSubject,
  worldId,
  conflictId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && conflictId === undefined) {
    sendJson(
      response,
      200,
      organizationConflicts
        .filter((conflict) => matchesWorldline(conflict, worldId, url))
        .map(organizationConflictResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && conflictId === undefined) {
    const body = await readJson(request);
    const conflict = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      organization_id: body.organization_id,
      faction_track_id: body.faction_track_id ?? null,
      title: body.title,
      summary: body.summary,
      pressure_delta: body.pressure_delta ?? 0,
      progress_delta: body.progress_delta ?? 0,
      status: "proposed",
      resolved_event_id: null,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    organizationConflicts.push(conflict);
    sendJson(response, 201, organizationConflictResponse(conflict));
    return;
  }
  const conflict = organizationConflicts.find(
    (item) => item.id === conflictId && item.world_id === worldId,
  );
  if (conflict === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "resolve") {
    const event = appendWorldEvent(worldId, {
      worldline_id: conflict.worldline_id,
      event_name: "living_world.organization_conflict_resolved",
      importance: "organization",
      payload: { conflict_id: conflict.id, title: conflict.title },
      actor_ref: `user:${currentSubject.user_id}`,
    });
    conflict.status = "resolved";
    conflict.resolved_event_id = event.id;
    conflict.updated_at = new Date().toISOString();
    sendJson(response, 200, organizationConflictResponse(conflict));
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(conflict, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, organizationConflictResponse(conflict));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleRumors(request, response, currentSubject, worldId, rumorId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && rumorId === undefined) {
    sendJson(
      response,
      200,
      rumors.filter((rumor) => matchesWorldline(rumor, worldId, url)).map(rumorResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && rumorId === undefined) {
    const body = await readJson(request);
    const rumor = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      rumor_key: body.rumor_key,
      title: body.title,
      content: body.content,
      source_agent_id: body.source_agent_id ?? null,
      source_organization_id: body.source_organization_id ?? null,
      visibility: body.visibility ?? "private",
      known_agent_ids: body.known_agent_ids ?? [],
      status: "active",
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    rumors.push(rumor);
    sendJson(response, 201, rumorResponse(rumor));
    return;
  }
  const rumor = rumors.find((item) => item.id === rumorId && item.world_id === worldId);
  if (rumor === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(rumor, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, rumorResponse(rumor));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleRumorPropagations(
  request,
  response,
  currentSubject,
  worldId,
  propagationId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && propagationId === undefined) {
    sendJson(
      response,
      200,
      rumorPropagations
        .filter((propagation) => matchesWorldline(propagation, worldId, url))
        .map(rumorPropagationResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && propagationId === undefined) {
    const body = await readJson(request);
    const propagation = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      rumor_id: body.rumor_id,
      source_agent_id: body.source_agent_id ?? null,
      target_agent_id: body.target_agent_id ?? null,
      target_organization_id: body.target_organization_id ?? null,
      propagation_reason: body.propagation_reason,
      status: "pending",
      delivered_event_id: null,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    rumorPropagations.push(propagation);
    sendJson(response, 201, rumorPropagationResponse(propagation));
    return;
  }
  const propagation = rumorPropagations.find(
    (item) => item.id === propagationId && item.world_id === worldId,
  );
  if (propagation === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "deliver") {
    const event = appendWorldEvent(worldId, {
      worldline_id: propagation.worldline_id,
      event_name: "rumor.delivered",
      importance: "daily",
      payload: { rumor_id: propagation.rumor_id, propagation_id: propagation.id },
      actor_ref: `user:${currentSubject.user_id}`,
    });
    propagation.status = "delivered";
    propagation.delivered_event_id = event.id;
    propagation.updated_at = new Date().toISOString();
    sendJson(response, 200, rumorPropagationResponse(propagation));
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(propagation, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, rumorPropagationResponse(propagation));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleLivingWorldDashboard(request, response, currentSubject, worldId, url) {
  if (!canReadWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const worldlineId = url.searchParams.get("worldline_id") ?? primaryWorldlineId;
  sendJson(response, 200, {
    world_id: worldId,
    worldline_id: worldlineId,
    knowledge_count: knowledgeFacts.filter((item) => item.world_id === worldId).length,
    hidden_secret_count: secrets.filter(
      (item) => item.world_id === worldId && item.status === "hidden",
    ).length,
    emotional_state_count: emotionalStates.filter((item) => item.world_id === worldId).length,
    open_hook_count: storyHooks.filter((item) => item.world_id === worldId && item.status === "open").length,
    unread_notification_count: notifications.filter(
      (item) => item.world_id === worldId && item.status === "unread",
    ).length,
    pending_intervention_count: interventions.filter(
      (item) => item.world_id === worldId && item.status === "recorded",
    ).length,
    active_route_count: routeAffinities.filter(
      (item) => item.world_id === worldId && item.status === "active",
    ).length,
    pressure_summary: { risk: 20 },
  });
}

async function handleKnowledgeFacts(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    const agentId = url.searchParams.get("agent_id");
    sendJson(
      response,
      200,
      knowledgeFacts
        .filter((fact) => matchesWorldline(fact, worldId, url))
        .filter((fact) => agentId === null || fact.agent_id === agentId)
        .map(knowledgeFactResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PUT") {
    const body = await readJson(request);
    const worldlineId = body.worldline_id ?? primaryWorldlineId;
    let fact = knowledgeFacts.find(
      (item) =>
        item.world_id === worldId
        && item.worldline_id === worldlineId
        && item.agent_id === body.agent_id
        && item.fact_key === body.fact_key,
    );
    if (fact === undefined) {
      fact = {
        id: randomUUID(),
        world_id: worldId,
        worldline_id: worldlineId,
        agent_id: body.agent_id,
        fact_key: body.fact_key,
        knowledge_kind: body.knowledge_kind ?? "fact",
        content: body.content,
        source_event_id: body.source_event_id ?? null,
        source_ref: body.source_ref ?? null,
        confidence: body.confidence ?? 80,
        visibility: body.visibility ?? "private",
        is_active: true,
        metadata: body.metadata ?? {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      knowledgeFacts.push(fact);
    } else {
      Object.assign(fact, body, { updated_at: new Date().toISOString() });
    }
    sendJson(response, 200, knowledgeFactResponse(fact));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleSecrets(request, response, currentSubject, worldId, secretId, action, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && secretId === undefined) {
    sendJson(response, 200, secrets.filter((secret) => matchesWorldline(secret, worldId, url)));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && secretId === undefined) {
    const body = await readJson(request);
    const secret = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      secret_key: body.secret_key,
      title: body.title,
      content: body.content,
      holder_agent_ids: body.holder_agent_ids ?? [],
      reveal_conditions: body.reveal_conditions ?? {},
      consequence_metadata: body.consequence_metadata ?? {},
      visibility: body.visibility ?? "holders",
      status: "hidden",
      revealed_event_id: null,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    secrets.push(secret);
    sendJson(response, 201, secret);
    return;
  }
  const secret = secrets.find((item) => item.id === secretId && item.world_id === worldId);
  if (secret === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "reveal") {
    const event = appendWorldEvent(worldId, {
      worldline_id: secret.worldline_id,
      event_name: "secret.revealed",
      importance: "route",
      payload: { secret_id: secret.id, title: secret.title },
      actor_ref: `user:${currentSubject.user_id}`,
    });
    secret.status = "revealed";
    secret.revealed_event_id = event.id;
    secret.updated_at = new Date().toISOString();
    sendJson(response, 200, secret);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleEmotionalStates(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    const agentId = url.searchParams.get("agent_id");
    sendJson(
      response,
      200,
      emotionalStates
        .filter((state) => matchesWorldline(state, worldId, url))
        .filter((state) => agentId === null || state.agent_id === agentId)
        .map(emotionalStateResponse),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PUT") {
    const body = await readJson(request);
    const worldlineId = body.worldline_id ?? primaryWorldlineId;
    let state = emotionalStates.find(
      (item) =>
        item.world_id === worldId && item.worldline_id === worldlineId && item.agent_id === body.agent_id,
    );
    if (state === undefined) {
      state = {
        id: randomUUID(),
        world_id: worldId,
        worldline_id: worldlineId,
        agent_id: body.agent_id,
        mood: body.mood ?? "neutral",
        stress: body.stress ?? 0,
        fatigue: body.fatigue ?? 0,
        anticipation: body.anticipation ?? 0,
        jealousy: body.jealousy ?? 0,
        anger: body.anger ?? 0,
        source_event_id: body.source_event_id ?? null,
        expires_at: body.expires_at ?? null,
        metadata: body.metadata ?? {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      emotionalStates.push(state);
    } else {
      Object.assign(state, body, { updated_at: new Date().toISOString() });
    }
    sendJson(response, 200, emotionalStateResponse(state));
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleRelationshipRepairs(
  request,
  response,
  currentSubject,
  worldId,
  repairId,
  action,
  url,
) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && repairId === undefined) {
    sendJson(
      response,
      200,
      relationshipRepairs.filter((repair) => matchesWorldline(repair, worldId, url)),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && repairId === undefined) {
    const body = await readJson(request);
    const repair = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      relationship_id: body.relationship_id,
      repair_kind: body.repair_kind,
      reason: body.reason,
      score_delta: body.score_delta ?? {},
      status: "proposed",
      applied_event_id: null,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    relationshipRepairs.push(repair);
    sendJson(response, 201, repair);
    return;
  }
  const repair = relationshipRepairs.find((item) => item.id === repairId && item.world_id === worldId);
  if (repair === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "POST" && action === "apply") {
    const event = appendWorldEvent(worldId, {
      worldline_id: repair.worldline_id,
      event_name: "relationship.repair_applied",
      importance: "relationship",
      payload: { repair_id: repair.id },
      actor_ref: `user:${currentSubject.user_id}`,
    });
    repair.status = "applied";
    repair.applied_event_id = event.id;
    repair.updated_at = new Date().toISOString();
    sendJson(response, 200, repair);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handlePlayerJournal(request, response, currentSubject, worldId, url) {
  if (!canReadWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(
      response,
      200,
      playerJournal
        .filter((entry) => matchesWorldline(entry, worldId, url))
        .filter((entry) => canManageWorld(currentSubject, worldId) || entry.user_id === currentSubject.user_id),
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
  const body = await readJson(request);
  const entry = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    user_id: body.user_id ?? currentSubject.user_id,
    player_actor_id: body.player_actor_id ?? null,
    entry_kind: body.entry_kind,
    title: body.title,
    body: body.body,
    source_event_id: body.source_event_id ?? null,
    source_ref: body.source_ref ?? null,
    visibility: body.visibility ?? "player_private",
    metadata: body.metadata ?? {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  playerJournal.push(entry);
  sendJson(response, 201, entry);
}

async function handleNotifications(request, response, currentSubject, worldId, url) {
  if (!canReadWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(
      response,
      200,
      notifications
        .filter((notification) => matchesWorldline(notification, worldId, url))
        .filter(
          (notification) =>
            canManageWorld(currentSubject, worldId) || notification.user_id === currentSubject.user_id,
        ),
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
  const body = await readJson(request);
  const notification = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    user_id: body.user_id ?? currentSubject.user_id,
    notification_kind: body.notification_kind,
    title: body.title,
    body: body.body,
    source_event_id: body.source_event_id ?? null,
    source_ref: body.source_ref ?? null,
    status: "unread",
    metadata: body.metadata ?? {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  notifications.push(notification);
  sendJson(response, 201, notification);
}

async function handleInterventions(request, response, currentSubject, worldId, url) {
  if (!canReadWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(
      response,
      200,
      interventions
        .filter((intervention) => matchesWorldline(intervention, worldId, url))
        .filter(
          (intervention) =>
            canManageWorld(currentSubject, worldId) || intervention.user_id === currentSubject.user_id,
        ),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  const body = await readJson(request);
  const event = appendWorldEvent(worldId, {
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    event_name: "player.intervention_recorded",
    importance: "daily",
    payload: { intervention_kind: body.intervention_kind, prompt: body.prompt },
    actor_ref: `user:${currentSubject.user_id}`,
  });
  const intervention = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    user_id: body.user_id ?? currentSubject.user_id,
    player_actor_id: body.player_actor_id,
    intervention_kind: body.intervention_kind,
    target_agent_id: body.target_agent_id ?? null,
    target_scene_id: body.target_scene_id ?? null,
    prompt: body.prompt,
    choice_id: null,
    event_id: event.id,
    status: "recorded",
    metadata: body.metadata ?? {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  interventions.push(intervention);
  sendJson(response, 201, intervention);
}

async function handleGMStyleReviews(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, gmStyleReviews.filter((review) => matchesWorldline(review, worldId, url)));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  const body = await readJson(request);
  const diagnostics = body.reviewed_text.includes("AI chatbot")
    ? [{ code: "generic_chatbot_drift", severity: "warning" }]
    : [];
  const review = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    source_kind: body.source_kind,
    source_ref: body.source_ref ?? null,
    reviewed_text: body.reviewed_text,
    status: diagnostics.length > 0 ? "warning" : "pass",
    diagnostics,
    metadata: body.metadata ?? {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  gmStyleReviews.push(review);
  sendJson(response, 201, review);
}

async function handleNarrativeContinuityReviews(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(
      response,
      200,
      narrativeContinuityReviews.filter((review) => matchesWorldline(review, worldId, url)),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  const body = await readJson(request);
  const issues = continuityIssuesForText(body.reviewed_text);
  const review = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    artifact_id: body.artifact_id ?? null,
    source_kind: body.source_kind,
    source_ref: body.source_ref ?? null,
    reviewed_text: body.reviewed_text,
    status: issues.length > 0 ? "warning" : "pass",
    issues,
    metadata: body.metadata ?? {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  narrativeContinuityReviews.push(review);
  sendJson(response, 201, review);
}

async function handlePlayerActors(request, response, currentSubject, worldId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET") {
    sendJson(response, 200, playerActors.filter((actor) => actor.world_id === worldId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  const body = await readJson(request);
  const actor = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    user_id: body.user_id ?? currentSubject.user_id,
    actor_ref: `player:${body.user_id ?? currentSubject.user_id}:primary`,
    display_name: body.display_name,
    current_scene_id: body.current_scene_id ?? null,
    profile: body.profile ?? {},
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  playerActors.push(actor);
  sendJson(response, 200, actor);
}

async function handlePlayerChoices(request, response, currentSubject, worldId, action) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && action === undefined) {
    sendJson(response, 200, playerChoices.filter((choice) => choice.world_id === worldId));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  const body = await readJson(request);
  const preview = {
    relationship_updates: body.effects?.relationship_updates ?? [],
    faction_updates: body.effects?.faction_updates ?? [],
    offscreen_events: body.effects?.offscreen_events ?? [],
    diagnostics: [
      `${(body.effects?.relationship_updates ?? []).length} relationship update(s)`,
      `${(body.effects?.faction_updates ?? []).length} faction update(s)`,
      `${(body.effects?.offscreen_events ?? []).length} offscreen event(s)`,
    ],
  };
  if (request.method === "POST" && action === "preview") {
    sendJson(response, 200, preview);
    return;
  }
  const choice = {
    id: randomUUID(),
    world_id: worldId,
    worldline_id: body.worldline_id ?? primaryWorldlineId,
    user_id: body.user_id ?? currentSubject.user_id,
    player_actor_id: body.player_actor_id,
    choice_key: body.choice_key,
    choice_kind: body.choice_kind,
    prompt: body.prompt,
    selected_option: body.selected_option,
    context: body.context ?? {},
    consequence_preview: preview,
    applied_event_id: randomUUID(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  playerChoices.unshift(choice);
  sendJson(response, 201, choice);
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
      region_key: body.region_key ?? null,
      location_tags: body.location_tags ?? [],
      opening_rules: body.opening_rules ?? {},
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

async function handleLocationEdges(request, response, currentSubject, worldId, edgeId) {
  if (request.method === "GET" && edgeId === undefined) {
    sendJson(response, 200, locationEdges.filter((edge) => edge.world_id === worldId));
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
  if (request.method === "POST" && edgeId === undefined) {
    const body = await readJson(request);
    const sourceScene = scenes.find((scene) => scene.id === body.source_scene_id);
    const targetScene = scenes.find((scene) => scene.id === body.target_scene_id);
    const edge = {
      id: randomUUID(),
      world_id: worldId,
      source_scene_id: body.source_scene_id,
      target_scene_id: body.target_scene_id,
      source_scene_key: sourceScene?.scene_key ?? "unknown",
      target_scene_key: targetScene?.scene_key ?? "unknown",
      travel_label: body.travel_label ?? null,
      traversal_rules: body.traversal_rules ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    locationEdges.push(edge);
    sendJson(response, 201, edge);
    return;
  }
  const edge = locationEdges.find((item) => item.id === edgeId && item.world_id === worldId);
  if (edge === undefined) {
    sendJson(response, 404, { detail: "Location edge not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(edge, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, edge);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleOrganizations(request, response, currentSubject, worldId, organizationId, childResource, childId) {
  if (organizationId !== undefined && childResource === "memberships") {
    await handleOrganizationMemberships(request, response, currentSubject, worldId, organizationId, childId);
    return;
  }
  if (organizationId !== undefined && childResource === "faction-tracks") {
    await handleFactionTracks(request, response, currentSubject, worldId, organizationId, childId);
    return;
  }
  if (request.method === "GET" && organizationId === undefined) {
    sendJson(response, 200, organizations.filter((organization) => organization.world_id === worldId));
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
  if (request.method === "POST" && organizationId === undefined) {
    const body = await readJson(request);
    const organization = {
      id: randomUUID(),
      world_id: worldId,
      organization_key: body.organization_key,
      name: body.name,
      organization_type: body.organization_type,
      description: body.description ?? null,
      public_summary: body.public_summary ?? null,
      hidden_summary: body.hidden_summary ?? null,
      metadata: body.metadata ?? {},
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    organizations.push(organization);
    sendJson(response, 201, organization);
    return;
  }
  const organization = organizations.find(
    (item) => item.id === organizationId && item.world_id === worldId,
  );
  if (organization === undefined) {
    sendJson(response, 404, { detail: "Organization not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(organization, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, organization);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleOrganizationMemberships(request, response, currentSubject, worldId, organizationId, membershipId) {
  if (request.method === "GET" && membershipId === undefined) {
    sendJson(
      response,
      200,
      organizationMemberships.filter(
        (membership) =>
          membership.world_id === worldId && membership.organization_id === organizationId,
      ),
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
  if (request.method === "POST" && membershipId === undefined) {
    const body = await readJson(request);
    const organization = organizations.find((item) => item.id === organizationId);
    const agent = agents.find((item) => item.id === body.agent_id);
    const membership = {
      id: randomUUID(),
      world_id: worldId,
      organization_id: organizationId,
      organization_key: organization?.organization_key ?? "unknown",
      organization_name: organization?.name ?? "Unknown",
      agent_id: body.agent_id,
      agent_key: agent?.agent_key ?? "unknown",
      agent_display_name: agent?.display_name ?? "Unknown",
      role_title: body.role_title ?? null,
      visibility: body.visibility ?? "public",
      loyalty: body.loyalty ?? 50,
      influence: body.influence ?? 50,
      responsibilities: body.responsibilities ?? [],
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    organizationMemberships.push(membership);
    sendJson(response, 201, membership);
    return;
  }
  const membership = organizationMemberships.find(
    (item) => item.id === membershipId && item.world_id === worldId,
  );
  if (membership === undefined) {
    sendJson(response, 404, { detail: "Membership not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(membership, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, membership);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleFactionTracks(request, response, currentSubject, worldId, organizationId, trackId) {
  if (request.method === "GET" && trackId === undefined) {
    sendJson(
      response,
      200,
      factionTracks.filter(
        (track) => track.world_id === worldId && track.organization_id === organizationId,
      ),
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
  if (request.method === "POST" && trackId === undefined) {
    const body = await readJson(request);
    const organization = organizations.find((item) => item.id === organizationId);
    const track = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      organization_id: organizationId,
      organization_key: organization?.organization_key ?? "unknown",
      organization_name: organization?.name ?? "Unknown",
      track_key: body.track_key,
      name: body.name,
      track_type: body.track_type,
      progress: body.progress ?? 0,
      pressure: body.pressure ?? 0,
      summary: body.summary ?? null,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    factionTracks.push(track);
    sendJson(response, 201, track);
    return;
  }
  const track = factionTracks.find((item) => item.id === trackId && item.world_id === worldId);
  if (track === undefined) {
    sendJson(response, 404, { detail: "Faction track not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(track, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, track);
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
    if (segments[4] === "relationships") {
      await handleAgentRelationships(
        request,
        response,
        currentSubject,
        worldId,
        agentId,
        segments[5],
      );
      return;
    }
    if (segments[4] === "presence") {
      await handleAgentPresence(request, response, currentSubject, worldId, agentId);
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
      narrative_role: body.narrative_role ?? null,
      importance: body.importance ?? null,
      canon_status: body.canon_status ?? null,
      character_category: body.character_category ?? null,
      character_profile: body.character_profile ?? {},
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

async function handleAgentPresence(request, response, currentSubject, worldId, agentId) {
  const agent = agents.find((item) => item.id === agentId && item.world_id === worldId);
  if (agent === undefined) {
    sendJson(response, 404, { detail: "Agent not found" });
    return;
  }
  const existing = agentPresenceStates.find(
    (item) => item.world_id === worldId && item.agent_id === agentId,
  );
  if (request.method === "GET") {
    sendJson(response, 200, existing ?? null);
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
  if (request.method === "PUT") {
    const body = await readJson(request);
    const scene = scenes.find((item) => item.id === body.current_scene_id);
    const presence = existing ?? {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      agent_id: agentId,
      agent_key: agent.agent_key,
      agent_display_name: agent.display_name,
      created_at: new Date().toISOString(),
    };
    Object.assign(presence, {
      current_scene_id: body.current_scene_id ?? null,
      current_scene_key: scene?.scene_key ?? null,
      current_scene_name: scene?.name ?? null,
      visibility_status: body.visibility_status ?? "visible",
      encounter_eligible: body.encounter_eligible ?? true,
      scheduled_movement: body.scheduled_movement ?? {},
      last_event_id: presence.last_event_id ?? null,
      updated_at: new Date().toISOString(),
    });
    if (existing === undefined) {
      agentPresenceStates.push(presence);
    }
    sendJson(response, 200, presence);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAgentRelationships(
  request,
  response,
  currentSubject,
  worldId,
  agentId,
  relationshipId,
) {
  const agent = agents.find((item) => item.id === agentId && item.world_id === worldId);
  if (agent === undefined) {
    sendJson(response, 404, { detail: "Agent not found" });
    return;
  }
  if (request.method === "GET" && relationshipId === undefined) {
    sendJson(
      response,
      200,
      agentRelationships.filter(
        (relationship) =>
          relationship.world_id === worldId && relationship.source_agent_id === agentId,
      ),
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
  if (request.method === "POST" && relationshipId === undefined) {
    const body = await readJson(request);
    const targetAgent = agents.find(
      (item) => item.id === body.target_agent_id && item.world_id === worldId,
    );
    if (targetAgent === undefined || body.source_agent_id !== agentId) {
      sendJson(response, 422, { detail: "Invalid relationship edge" });
      return;
    }
    const relationship = relationshipResponse({
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      source_agent_id: agentId,
      target_agent_id: targetAgent.id,
      relationship_type: body.relationship_type,
      affection: body.affection ?? 0,
      trust: body.trust ?? 0,
      hostility: body.hostility ?? 0,
      intimacy: body.intimacy ?? 0,
      obligation: body.obligation ?? 0,
      rivalry: body.rivalry ?? 0,
      debt: body.debt ?? 0,
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    agentRelationships.push(relationship);
    sendJson(response, 201, relationship);
    return;
  }
  const relationship = agentRelationships.find(
    (item) =>
      item.id === relationshipId
      && item.world_id === worldId
      && item.source_agent_id === agentId,
  );
  if (relationship === undefined) {
    sendJson(response, 404, { detail: "Relationship not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(relationship, await readJson(request), { updated_at: new Date().toISOString() });
    sendJson(response, 200, relationshipResponse(relationship));
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
        region_key: scene.region_key ?? null,
        location_tags: scene.location_tags ?? [],
        opening_rules: scene.opening_rules ?? {},
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
  const url = new URL(request.url, "http://mock.local");
  const component = url.searchParams.get("component");
  sendJson(
    response,
    200,
    component === null
      ? runtimeDiagnostics
      : runtimeDiagnostics.filter((diagnostic) => diagnostic.component === component),
  );
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

function handlePluginBindings(request, url, response) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const bindings = [
    ...providerProfiles.map((profile) => ({
      owner_kind: "provider_profile",
      owner_id: profile.id,
      owner_key: profile.profile_key,
      world_id: null,
      agent_id: null,
      conversation_id: null,
      provider_profile_id: profile.id,
      plugin_identifier: profile.plugin_identifier,
      category: "model_provider",
      config_present: Object.keys(profile.plugin_config ?? {}).length > 0,
      validation_status: "ok",
      issue_message: null,
    })),
    ...worlds.flatMap((world) => [
      {
        owner_kind: "world_memory",
        owner_id: world.id,
        owner_key: world.slug,
        world_id: world.id,
        agent_id: null,
        conversation_id: null,
        provider_profile_id: null,
        plugin_identifier: world.memory_plugin_identifier,
        category: "memory_backend",
        config_present: Object.keys(world.memory_plugin_config ?? {}).length > 0,
        validation_status: "ok",
        issue_message: null,
      },
      {
        owner_kind: "world_rules",
        owner_id: world.id,
        owner_key: world.slug,
        world_id: world.id,
        agent_id: null,
        conversation_id: null,
        provider_profile_id: null,
        plugin_identifier: world.world_rules_plugin_identifier,
        category: "world_rules",
        config_present: Object.keys(world.world_rules_plugin_config ?? {}).length > 0,
        validation_status: "ok",
        issue_message: null,
      },
    ]),
  ];
  const category = url.searchParams.get("category");
  sendJson(
    response,
    200,
    category === null ? bindings : bindings.filter((binding) => binding.category === category),
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

async function handleAgentPresetItem(request, response, presetId, action) {
  if (subjectForRequest(request)?.roles.includes("platform_admin") !== true) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const preset = agentPresets.find((item) => item.id === presetId);
  if (preset === undefined) {
    sendJson(response, 404, { detail: "Not found" });
    return;
  }
  if (request.method === "GET" && action === "update-preview") {
    const materializedAgents = agents.filter((agent) => agent.source_preset_id === presetId);
    const previewAgents = materializedAgents.map((agent) => ({
      agent_id: agent.id,
      world_id: agent.world_id,
      agent_key: agent.agent_key,
      display_name: agent.display_name,
      source_preset_version: agent.source_preset_version ?? null,
      status:
        agent.source_preset_version == null
          ? "unversioned"
          : agent.source_preset_version < preset.version
            ? "stale"
            : "current",
      changed_fields: [],
    }));
    sendJson(response, 200, {
      preset_id: preset.id,
      preset_key: preset.preset_key,
      current_version: preset.version,
      stale_agent_count: previewAgents.filter((agent) => agent.status === "stale").length,
      current_agent_count: previewAgents.filter((agent) => agent.status === "current").length,
      unversioned_agent_count: previewAgents.filter((agent) => agent.status === "unversioned").length,
      agents: previewAgents,
    });
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
      region_key: scene.region_key ?? null,
      location_tags: scene.location_tags ?? [],
      opening_rules: scene.opening_rules ?? {},
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
      worldline_id: body.worldline_id ?? primaryWorldlineId,
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
      worldline_id: primaryWorldlineId,
      covers_event_sequence: replay.source_sequence,
      schema_version: "world_state.v1",
      status: "valid",
      payload: null,
      payload_uri: `object://worlds/${worldId}/worldlines/${primaryWorldlineId}/snapshots/${replay.source_sequence}.json`,
      payload_location: "object",
      metadata: { source: "mock", storage: "local_object" },
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
  const importance = url.searchParams.get("importance");
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
  if (importance !== null) {
    events = events.filter((event) => event.importance === importance);
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

async function handleDailyLife(request, response, currentSubject, worldId, action, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (action === "preview" && request.method === "GET") {
    const candidates = dailyLifeCandidates.filter((candidate) => candidate.world_id === worldId);
    sendJson(response, 200, {
      world_id: worldId,
      start_world_time: url.searchParams.get("start_world_time") ?? "2030-01-01T08:00:00.000Z",
      horizon_hours: Number(url.searchParams.get("horizon_hours") ?? "24"),
      candidate_count: candidates.length,
      candidates: candidates.map((candidate) => ({ ...candidate, id: null, created_at: null, updated_at: null })),
    });
    return;
  }
  if (!hasValidCsrf(request) && action === "generate") {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (action === "generate" && request.method === "POST") {
    sendJson(response, 200, dailyLifeCandidates.filter((candidate) => candidate.world_id === worldId));
    return;
  }
  if (action === "candidates" && request.method === "GET") {
    const status = url.searchParams.get("status");
    const candidates = dailyLifeCandidates.filter(
      (candidate) =>
        candidate.world_id === worldId && (status === null || candidate.status === status),
    );
    sendJson(response, 200, candidates);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleOffscreenEvents(request, response, currentSubject, worldId, action, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && action === undefined) {
    const status = url.searchParams.get("status");
    sendJson(
      response,
      200,
      offscreenEvents.filter(
        (item) => item.world_id === worldId && (status === null || item.status === status),
      ),
    );
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && action === undefined) {
    const body = await readJson(request);
    const candidate = dailyLifeCandidates.find((item) => item.id === body.candidate_id);
    const item = {
      id: randomUUID(),
      world_id: worldId,
      worldline_id: body.worldline_id ?? primaryWorldlineId,
      source_candidate_id: candidate?.id ?? null,
      event_name: body.event_name ?? "living_world.offscreen_event",
      title: candidate?.title ?? body.title,
      payload: candidate === undefined ? body.payload ?? {} : { summary: candidate.summary },
      due_at: candidate?.starts_at ?? body.due_at,
      importance: candidate?.importance ?? body.importance ?? "daily",
      status: "pending",
      resolved_event_id: null,
      last_error: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    offscreenEvents.unshift(item);
    if (candidate !== undefined) {
      candidate.status = "queued";
    }
    sendJson(response, 201, item);
    return;
  }
  if (request.method === "POST" && action === "resolve") {
    const dueItems = offscreenEvents.filter(
      (item) => item.world_id === worldId && item.status === "pending",
    );
    const eventIds = [];
    for (const item of dueItems) {
      const event = appendWorldEvent(worldId, {
        event_name: item.event_name,
        importance: item.importance,
        payload: item.payload,
        world_time: item.due_at,
        actor_ref: "system:runtime",
      });
      item.status = "resolved";
      item.resolved_event_id = event.id;
      item.updated_at = new Date().toISOString();
      eventIds.push(event.id);
    }
    sendJson(response, 200, {
      processed_count: dueItems.length,
      resolved_count: dueItems.length,
      failed_count: 0,
      event_ids: eventIds,
    });
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
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
    const query = url.searchParams.get("q");
    const sourceKind = url.searchParams.get("source_kind");
    const publicationStatus = url.searchParams.get("publication_status");
    const orderBy = url.searchParams.get("order_by") ?? "created_at";
    const limitValue = Number.parseInt(url.searchParams.get("limit") ?? "", 10);
    let items = narrativeArtifacts
      .filter((artifact) => artifact.world_id === worldId)
      .sort((left, right) => compareNarrativeArtifacts(left, right, orderBy));
    if (!canManageWorld(currentSubject, worldId)) {
      items = items.filter(isReaderVisibleArtifact);
    }
    if (artifactKind !== null && artifactKind !== "") {
      items = items.filter((artifact) => artifact.artifact_kind === artifactKind);
    }
    if (sourceConversationId !== null && sourceConversationId !== "") {
      items = items.filter((artifact) => artifact.source_conversation_id === sourceConversationId);
    }
    if (query !== null && query !== "") {
      const needle = query.toLowerCase();
      items = items.filter(
        (artifact) =>
          artifact.title.toLowerCase().includes(needle)
          || artifact.content.toLowerCase().includes(needle),
      );
    }
    if (sourceKind !== null && sourceKind !== "") {
      items = items.filter((artifact) => sourceKindForNarrativeArtifact(artifact) === sourceKind);
    }
    if (canManageWorld(currentSubject, worldId) && publicationStatus !== null && publicationStatus !== "") {
      items = items.filter((artifact) =>
        publicationStatus === "published" ? isReaderVisibleArtifact(artifact) : !isReaderVisibleArtifact(artifact),
      );
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
    const publicationBlocker = publicationBlockerForArtifact(worldId, artifact, body);
    if (publicationBlocker !== null) {
      sendJson(response, 422, { detail: publicationBlocker });
      return;
    }
    const now = new Date().toISOString();
    const reviewId = randomUUID();
    artifact.publication = {
      id: artifact.publication?.id ?? randomUUID(),
      world_id: worldId,
      artifact_id: artifact.id,
      source_draft_id: artifact.id,
      status: "published",
      reader_visible: body.reader_visible ?? true,
      metadata: {
        ...(body.metadata ?? artifact.publication?.metadata ?? {}),
        publication_gate: {
          review_id: reviewId,
          status: "pass",
          override_style_warning: Boolean(body.override_style_warning),
          issue_count: 0,
        },
      },
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
    worldline_id: primaryWorldlineId,
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
    worldline_id: input.worldline_id ?? primaryWorldlineId,
    sequence: events.length + 1,
    event_name: input.event_name,
    importance: input.importance ?? "system",
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

function evidenceRef(kind, id, label, worldlineId, apiPath) {
  return {
    kind,
    id,
    label,
    worldline_id: worldlineId,
    api_path: apiPath,
  };
}

function eventEvidenceRef(worldId, event) {
  return evidenceRef(
    "world_event",
    event.id,
    event.event_name,
    event.worldline_id,
    `/worlds/${worldId}/events`,
  );
}

function evidenceRefsForWorldline(worldId, worldlineId) {
  const refs = [];
  refs.push(
    ...worldlines
      .filter((worldline) => worldline.world_id === worldId && worldline.id === worldlineId)
      .map((worldline) =>
        evidenceRef("worldline", worldline.id, worldline.name, worldlineId, `/worlds/${worldId}/worldlines`),
      ),
  );
  refs.push(
    ...(worldEvents.get(worldId) ?? [])
      .filter((event) => event.worldline_id === worldlineId)
      .slice(0, 3)
      .map((event) => eventEvidenceRef(worldId, event)),
  );
  const snapshot = snapshots.get(worldId);
  if (snapshot !== undefined && snapshot.worldline_id === worldlineId) {
    refs.push(
      evidenceRef(
        "snapshot",
        snapshot.id,
        snapshot.schema_version,
        worldlineId,
        `/worlds/${worldId}/snapshots/latest`,
      ),
    );
  }
  refs.push(
    ...agentRelationships
      .filter((relationship) => relationship.world_id === worldId && relationship.worldline_id === worldlineId)
      .slice(0, 2)
      .map((relationship) =>
        evidenceRef(
          "relationship",
          relationship.id,
          relationship.relationship_type,
          worldlineId,
          `/worlds/${worldId}/agents/${relationship.source_agent_id}`,
        ),
      ),
  );
  refs.push(
    ...factionTracks
      .filter((track) => track.world_id === worldId && track.worldline_id === worldlineId)
      .slice(0, 2)
      .map((track) =>
        evidenceRef("faction_track", track.id, track.track_key, worldlineId, `/worlds/${worldId}/organizations`),
      ),
  );
  refs.push(
    ...gmProposals
      .filter((proposal) => proposal.world_id === worldId && proposal.worldline_id === worldlineId)
      .slice(0, 2)
      .map((proposal) =>
        evidenceRef("gm_proposal", proposal.id, proposal.title, worldlineId, `/worlds/${worldId}/gm/proposals`),
      ),
  );
  refs.push(
    ...playerChoices
      .filter((choice) => choice.world_id === worldId && choice.worldline_id === worldlineId)
      .slice(0, 2)
      .map((choice) =>
        evidenceRef("player_choice", choice.id, choice.choice_key, worldlineId, `/worlds/${worldId}/player-choices`),
      ),
  );
  refs.push(
    ...playerJournal
      .filter((entry) => entry.world_id === worldId && entry.worldline_id === worldlineId)
      .slice(0, 2)
      .map((entry) =>
        evidenceRef("journal_entry", entry.id, entry.title, worldlineId, `/worlds/${worldId}/player-journal`),
      ),
  );
  refs.push(
    ...notifications
      .filter((notification) => notification.world_id === worldId && notification.worldline_id === worldlineId)
      .slice(0, 2)
      .map((notification) =>
        evidenceRef("notification", notification.id, notification.title, worldlineId, `/worlds/${worldId}/notifications`),
      ),
  );
  refs.push(
    ...narrativeArtifacts
      .flatMap((artifact) => (artifact.publication === null ? [] : [artifact.publication]))
      .filter((publication) => publication.world_id === worldId)
      .slice(0, 2)
      .map((publication) => ({
        kind: "publication",
        id: publication.id,
        label: "published narrative artifact",
        api_path: `/worlds/${worldId}/reader`,
      })),
  );
  refs.push(
    ...narrativeContinuityReviews
      .filter((review) => review.world_id === worldId && review.worldline_id === worldlineId)
      .slice(0, 2)
      .map((review) =>
        evidenceRef(
          "continuity_review",
          review.id,
          review.status,
          worldlineId,
          `/worlds/${worldId}/narrative-continuity-reviews`,
        ),
      ),
  );
  refs.push(
    ...betaChecklistRuns
      .filter((run) => run.world_id === worldId && run.worldline_id === worldlineId)
      .slice(0, 1)
      .map((run) =>
        evidenceRef("beta_checklist", run.id, run.run_key, worldlineId, `/worlds/${worldId}/beta-checklists`),
      ),
  );
  refs.push(
    ...longRunEvals
      .filter((run) => run.world_id === worldId && run.worldline_id === worldlineId)
      .slice(0, 1)
      .map((run) =>
        evidenceRef("long_run_eval", run.id, run.eval_key, worldlineId, `/worlds/${worldId}/long-run-evals`),
      ),
  );
  return refs;
}

function gateDecisionForRelease(worldId, status, body) {
  const worldlineId = body.checklist?.worldline_id ?? body.metadata?.worldline_id ?? primaryWorldlineId;
  const evidenceRefs = Array.isArray(body.checklist?.evidence_refs)
    ? body.checklist.evidence_refs
    : [];
  const requiredKinds = [
    "snapshot",
    "worldline",
    "publication",
    "continuity_review",
    "beta_checklist",
    "long_run_eval",
  ];
  const blockerKinds = requiredKinds.filter(
    (kind) => !evidenceRefs.some((ref) => ref.kind === kind),
  );
  const blockers = [];
  if (status === "released") {
    blockers.push({
      code: "release_launch_gate_missing",
      message: "Released status is blocked until a separate launch gate exists.",
    });
  }
  if (status === "ready" && blockerKinds.length > 0) {
    blockers.push({
      code: "missing_required_evidence_refs",
      message: `Ready status requires structured evidence refs for ${blockerKinds.join(", ")}.`,
      missing_kinds: blockerKinds,
    });
  }
  return {
    status,
    allowed: blockers.length === 0,
    blockers,
    warnings: body.checklist?.warning_decisions
      ? []
      : [
          {
            code: "warning_decisions_not_recorded",
            message: "Record explicit warning decisions before operator release.",
          },
        ],
    evidence_refs: evidenceRefs,
    worldline_id: worldlineId,
  };
}

function snapshotIntegrityForWorld(worldId) {
  const events = worldEvents.get(worldId) ?? [];
  const latestEventSequence = events.at(-1)?.sequence ?? 0;
  const latestSnapshot = snapshots.get(worldId) ?? null;
  if (latestSnapshot === null) {
    return {
      world_id: worldId,
      worldline_id: primaryWorldlineId,
      status: "warning",
      latest_event_sequence: latestEventSequence,
      latest_snapshot_id: null,
      covers_event_sequence: null,
      schema_version: null,
      payload_location: null,
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
    worldline_id: latestSnapshot.worldline_id ?? primaryWorldlineId,
    status: eventGap > 0 ? "warning" : "ok",
    latest_event_sequence: latestEventSequence,
    latest_snapshot_id: latestSnapshot.id,
    covers_event_sequence: latestSnapshot.covers_event_sequence,
    schema_version: latestSnapshot.schema_version,
    payload_location: latestSnapshot.payload_location ?? null,
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

function compareNarrativeArtifacts(left, right, orderBy) {
  const leftValue = orderBy === "published_at" ? timelineDateForNarrativeArtifact(left) : left.created_at;
  const rightValue = orderBy === "published_at" ? timelineDateForNarrativeArtifact(right) : right.created_at;
  return rightValue.localeCompare(leftValue);
}

function timelineDateForNarrativeArtifact(artifact) {
  return artifact.publication?.published_at ?? artifact.created_at;
}

function sourceKindForNarrativeArtifact(artifact) {
  if (artifact.source_conversation_id !== null) {
    return "conversation";
  }
  if (artifact.source_run_id !== null) {
    return "agent_run";
  }
  if (artifact.agent_id !== null) {
    return "agent";
  }
  return "world";
}

function publicationBlockerForArtifact(worldId, artifact, body) {
  const issues = continuityIssuesForText(artifact.content);
  const hasError = issues.some((issue) => issue.severity === "error");
  const overrideStyleWarning = Boolean(body.override_style_warning);
  if (issues.length === 0 || (!hasError && overrideStyleWarning)) {
    return null;
  }
  return {
    message: "Narrative publication blocked by continuity review",
    review_id: randomUUID(),
    review_status: hasError ? "fail" : "warning",
    issues: issues.map((issue) => ({ ...issue, world_id: worldId })),
  };
}

function continuityIssuesForText(text) {
  const lowered = text.toLowerCase();
  const issues = [];
  if (lowered.includes("out of character") || lowered.includes("ooc")) {
    issues.push({
      severity: "warning",
      code: "ooc_marker",
      message: "Text contains an OOC marker.",
    });
  }
  if (lowered.includes("everyone knows") || lowered.includes("all characters know")) {
    issues.push({
      severity: "warning",
      code: "knowledge_leak_risk",
      message: "Text may leak knowledge globally.",
    });
  }
  if (lowered.includes("time paradox") || lowered.includes("same time")) {
    issues.push({
      severity: "warning",
      code: "time_contradiction_risk",
      message: "Text may contain a time contradiction.",
    });
  }
  if (lowered.includes("hidden secret leak")) {
    issues.push({
      severity: "error",
      code: "hidden_secret_leak",
      message: "Text appears to expose a hidden secret outside its visibility boundary.",
    });
  }
  return issues;
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

function relationshipResponse(edge) {
  const sourceAgent = agents.find((agent) => agent.id === edge.source_agent_id);
  const targetAgent = agents.find((agent) => agent.id === edge.target_agent_id);
  return {
    ...edge,
    source_agent_key: sourceAgent?.agent_key ?? null,
    source_display_name: sourceAgent?.display_name ?? null,
    target_agent_key: targetAgent?.agent_key ?? null,
    target_display_name: targetAgent?.display_name ?? null,
  };
}

function knowledgeFactResponse(fact) {
  const agent = agentFor(fact.agent_id);
  return {
    ...fact,
    agent_key: agent?.agent_key ?? null,
    agent_display_name: agent?.display_name ?? null,
  };
}

function emotionalStateResponse(state) {
  const agent = agentFor(state.agent_id);
  return {
    ...state,
    agent_key: agent?.agent_key ?? null,
    agent_display_name: agent?.display_name ?? null,
  };
}

function matchesWorldline(item, worldId, url) {
  const worldlineId = url.searchParams.get("worldline_id") ?? primaryWorldlineId;
  return item.world_id === worldId && item.worldline_id === worldlineId;
}

function agentFor(agentId) {
  return agents.find((agent) => agent.id === agentId) ?? null;
}

function sceneFor(sceneId) {
  return scenes.find((scene) => scene.id === sceneId) ?? null;
}

function organizationFor(organizationId) {
  return organizations.find((organization) => organization.id === organizationId) ?? null;
}

function factionTrackFor(trackId) {
  return factionTracks.find((track) => track.id === trackId) ?? null;
}

function storyHookResponse(hook) {
  const owner = hook.owner_agent_id === null ? null : agentFor(hook.owner_agent_id);
  const target = hook.target_agent_id === null ? null : agentFor(hook.target_agent_id);
  return {
    ...hook,
    owner_agent_key: owner?.agent_key ?? null,
    owner_agent_display_name: owner?.display_name ?? null,
    target_agent_key: target?.agent_key ?? null,
    target_agent_display_name: target?.display_name ?? null,
  };
}

function routeAffinityResponse(route) {
  const agent = agentFor(route.agent_id);
  return {
    ...route,
    agent_key: agent?.agent_key ?? null,
    agent_display_name: agent?.display_name ?? null,
  };
}

function routeMilestoneResponse(milestone) {
  const agent = milestone.agent_id === null ? null : agentFor(milestone.agent_id);
  return {
    ...milestone,
    agent_key: agent?.agent_key ?? null,
    agent_display_name: agent?.display_name ?? null,
  };
}

function endingCandidateResponse(ending) {
  const agent = ending.agent_id === null ? null : agentFor(ending.agent_id);
  return {
    ...ending,
    agent_key: agent?.agent_key ?? null,
    agent_display_name: agent?.display_name ?? null,
  };
}

function sceneBeatResponse(beat) {
  const scene = beat.scene_id === null ? null : sceneFor(beat.scene_id);
  return {
    ...beat,
    scene_key: scene?.scene_key ?? null,
    scene_name: scene?.name ?? null,
  };
}

function groupInteractionResponse(context) {
  const scene = context.scene_id === null ? null : sceneFor(context.scene_id);
  const organization =
    context.organization_id === null ? null : organizationFor(context.organization_id);
  return {
    ...context,
    scene_key: scene?.scene_key ?? null,
    scene_name: scene?.name ?? null,
    organization_key: organization?.organization_key ?? null,
    organization_name: organization?.name ?? null,
  };
}

function relationshipSuggestionResponse(suggestion) {
  const source = suggestion.source_agent_id === null ? null : agentFor(suggestion.source_agent_id);
  const target = suggestion.target_agent_id === null ? null : agentFor(suggestion.target_agent_id);
  return {
    ...suggestion,
    source_agent_display_name: source?.display_name ?? null,
    target_agent_display_name: target?.display_name ?? null,
  };
}

function organizationConflictResponse(conflict) {
  const organization = organizationFor(conflict.organization_id);
  const track = conflict.faction_track_id === null ? null : factionTrackFor(conflict.faction_track_id);
  return {
    ...conflict,
    organization_key: organization?.organization_key ?? null,
    organization_name: organization?.name ?? null,
    faction_track_key: track?.track_key ?? null,
  };
}

function rumorResponse(rumor) {
  const sourceAgent = rumor.source_agent_id === null ? null : agentFor(rumor.source_agent_id);
  const sourceOrganization =
    rumor.source_organization_id === null ? null : organizationFor(rumor.source_organization_id);
  return {
    ...rumor,
    source_agent_display_name: sourceAgent?.display_name ?? null,
    source_organization_name: sourceOrganization?.name ?? null,
  };
}

function rumorPropagationResponse(propagation) {
  const rumor = rumors.find((item) => item.id === propagation.rumor_id);
  const sourceAgent =
    propagation.source_agent_id === null ? null : agentFor(propagation.source_agent_id);
  const targetAgent =
    propagation.target_agent_id === null ? null : agentFor(propagation.target_agent_id);
  const targetOrganization =
    propagation.target_organization_id === null
      ? null
      : organizationFor(propagation.target_organization_id);
  return {
    ...propagation,
    rumor_title: rumor?.title ?? "Unknown rumor",
    source_agent_display_name: sourceAgent?.display_name ?? null,
    target_agent_display_name: targetAgent?.display_name ?? null,
    target_organization_name: targetOrganization?.name ?? null,
  };
}

function primaryWorldlineFor(worldId) {
  return {
    id: randomUUID(),
    world_id: worldId,
    worldline_key: "primary",
    name: "Primary Worldline",
    description: "Default branch for the living world.",
    parent_worldline_id: null,
    forked_from_snapshot_id: null,
    fork_event_sequence: null,
    status: "active",
    created_by_actor_ref: "system:runtime",
    metadata: { primary: true },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
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
