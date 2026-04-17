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
  config: Record<string, unknown>;
  is_enabled: boolean;
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

export type WorldDashboardData = {
  worlds: World[];
  selectedWorldId: string | null;
  scenes: Scene[];
  agents: Agent[];
  memberships: Membership[];
  clock: WorldClock | null;
  replayState: WorldReplayState | null;
  latestSnapshot: WorldSnapshot | null;
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
  config?: Record<string, unknown>;
};

export type AgentUpdateInput = {
  display_name?: string;
  home_scene_id?: string | null;
  config?: Record<string, unknown>;
  is_enabled?: boolean;
};
