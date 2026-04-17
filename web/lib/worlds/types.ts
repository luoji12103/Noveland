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

export type WorldDashboardData = {
  worlds: World[];
  selectedWorldId: string | null;
  scenes: Scene[];
  agents: Agent[];
  memberships: Membership[];
  clock: WorldClock | null;
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
