export type BetaFeedbackIssueType =
  | "dialogue"
  | "persona"
  | "memory"
  | "sprite"
  | "background"
  | "voice"
  | "playback"
  | "provider"
  | "quota"
  | "session_recovery"
  | "ux"
  | "worldline"
  | "other";

export type BetaFeedbackSeverity = "low" | "medium" | "high" | "critical";

export type BetaFeedbackReportStatus =
  | "submitted"
  | "triaged"
  | "investigating"
  | "linked_to_repair"
  | "resolved"
  | "dismissed";

export type BetaFeedbackEvidenceKind =
  | "worldline"
  | "scene"
  | "conversation"
  | "turn"
  | "presentation"
  | "media_asset"
  | "media_job"
  | "invocation"
  | "persona"
  | "memory"
  | "voice_profile"
  | "sprite_set"
  | "sprite_variant"
  | "background_profile"
  | "provider"
  | "player_actor"
  | "quota"
  | "session"
  | "ux"
  | "other";

export type BetaFeedbackEvidenceRef = {
  kind: BetaFeedbackEvidenceKind;
  id?: string | null;
  label?: string | null;
  worldline_id?: string | null;
  role?: string | null;
  metadata?: Record<string, unknown>;
};

export type BetaFeedbackRepairProposalRef = {
  proposal_id: string;
  proposal_kind: string;
  status: string;
  metadata?: Record<string, unknown>;
};

export type BetaFeedbackReport = {
  id: string;
  world_id: string;
  worldline_id: string;
  reporter_user_id: string;
  player_actor_id: string | null;
  issue_type: BetaFeedbackIssueType;
  severity: BetaFeedbackSeverity;
  status: BetaFeedbackReportStatus;
  title: string;
  description: string;
  reporter_note: string | null;
  evidence_refs: BetaFeedbackEvidenceRef[];
  repair_proposal_refs: BetaFeedbackRepairProposalRef[];
  triage_note: string | null;
  triaged_by_actor_ref: string | null;
  triaged_at: string | null;
  moderation_report_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BetaFeedbackReportCreateInput = {
  worldline_id: string;
  issue_type: BetaFeedbackIssueType;
  severity: BetaFeedbackSeverity;
  title: string;
  description: string;
  reporter_note?: string | null;
  player_actor_id?: string | null;
  evidence_refs?: BetaFeedbackEvidenceRef[];
  metadata?: Record<string, unknown>;
};

export type BetaFeedbackReportTriageInput = {
  status: BetaFeedbackReportStatus;
  severity?: BetaFeedbackSeverity | null;
  triage_note?: string | null;
  repair_proposal_refs?: BetaFeedbackRepairProposalRef[] | null;
};

export const betaFeedbackIssueTypes: BetaFeedbackIssueType[] = [
  "dialogue",
  "persona",
  "memory",
  "sprite",
  "background",
  "voice",
  "playback",
  "provider",
  "quota",
  "session_recovery",
  "ux",
  "worldline",
  "other",
];

export const betaFeedbackSeverities: BetaFeedbackSeverity[] = [
  "low",
  "medium",
  "high",
  "critical",
];

export const betaFeedbackStatuses: BetaFeedbackReportStatus[] = [
  "submitted",
  "triaged",
  "investigating",
  "linked_to_repair",
  "resolved",
  "dismissed",
];
