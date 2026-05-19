export type PrivateBetaInviteStatus =
  | "pending"
  | "accepted"
  | "waitlisted"
  | "redeemed"
  | "expired"
  | "revoked";

export type PrivateBetaRole = "tester" | "player_tester";

export type PrivateBetaPlayerProfile = {
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

export type PrivateBetaAccess = {
  invite_id: string;
  world_id: string;
  world_name: string;
  worldline_id: string | null;
  worldline_name: string | null;
  status: PrivateBetaInviteStatus;
  beta_role: PrivateBetaRole;
  expires_at: string;
  redeemed_at: string | null;
  player_profile: PrivateBetaPlayerProfile | null;
};

export type PrivateBetaOnboardingStatus = {
  access: PrivateBetaAccess[];
  guidance: string[];
};

export type PrivateBetaRedeemResult = {
  access: PrivateBetaAccess;
  membership_role: string;
  idempotent: boolean;
};

export type PrivateBetaPlayerProfileInput = {
  worldline_id?: string | null;
  display_name: string;
  current_scene_id?: string | null;
  profile?: Record<string, unknown>;
};

export type PrivateBetaPlayerProfileResult = {
  access: PrivateBetaAccess;
  player_profile: PrivateBetaPlayerProfile;
};
