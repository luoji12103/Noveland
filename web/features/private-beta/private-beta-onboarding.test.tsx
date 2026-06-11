import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PrivateBetaOnboarding } from "@/features/private-beta/private-beta-onboarding";
import {
  bootstrapPrivateBetaPlayerProfile,
  redeemPrivateBetaInvite,
} from "@/lib/private-beta/client";
import type { PrivateBetaOnboardingData } from "@/lib/private-beta/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/lib/private-beta/client", () => ({
  bootstrapPrivateBetaPlayerProfile: vi.fn(),
  redeemPrivateBetaInvite: vi.fn(),
}));

describe("PrivateBetaOnboarding", () => {
  it("renders invited worlds and guidance without invite token leakage", () => {
    render(<PrivateBetaOnboarding data={onboardingData} />);

    expect(screen.getByRole("heading", { name: "Redeem invite" })).toBeVisible();
    expect(screen.getByText("Demo World")).toBeVisible();
    expect(screen.getAllByText("redeemed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("tester").length).toBeGreaterThan(0);
    expect(screen.getByText("Use the player surface after identity setup.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open player surface" })).toHaveAttribute(
      "href",
      "/worlds/world%2Fprivate%3Fbeta%3Dtrue%23frag/player",
    );
    expect(serializedDocument()).not.toMatch(/token-secret|storage_uri|raw_prompt|raw_output/i);
  });

  it("redeems an invite and creates a player identity", async () => {
    vi.mocked(redeemPrivateBetaInvite).mockResolvedValue({
      access: onboardingData.status!.access[0],
      membership_role: "human_user",
      idempotent: false,
    });
    vi.mocked(bootstrapPrivateBetaPlayerProfile).mockResolvedValue({
      access: {
        ...onboardingData.status!.access[0],
        player_profile: playerProfile,
      },
      player_profile: playerProfile,
    });
    render(<PrivateBetaOnboarding data={onboardingData} />);

    fireEvent.change(screen.getByLabelText("Invite token"), {
      target: { value: "token-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Redeem invite" }));

    await waitFor(() => {
      expect(redeemPrivateBetaInvite).toHaveBeenCalledWith("token-secret");
    });

    fireEvent.change(screen.getByLabelText("Player display name"), {
      target: { value: "Beta Tester" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create identity" }));

    await waitFor(() => {
      expect(bootstrapPrivateBetaPlayerProfile).toHaveBeenCalledWith("world-1", {
        worldline_id: "worldline-1",
        display_name: "Beta Tester",
        profile: {},
      });
    });
  });
});

function serializedDocument(): string {
  return document.body.textContent ?? "";
}

const playerProfile = {
  id: "profile-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  user_id: "user-1",
  actor_ref: "player:user-1:primary",
  display_name: "Beta Tester",
  current_scene_id: null,
  profile: {},
  is_active: true,
  created_at: "2026-05-17T00:00:00.000Z",
  updated_at: "2026-05-17T00:00:00.000Z",
};

const readyWorldId = "world/private?beta=true#frag";

const playerProfileReady = {
  ...playerProfile,
  id: "profile-2",
  world_id: readyWorldId,
  display_name: "Ready Tester",
};

const onboardingData: PrivateBetaOnboardingData = {
  status: {
    access: [
      {
        invite_id: "invite-1",
        world_id: "world-1",
        world_name: "Demo World",
        worldline_id: "worldline-1",
        worldline_name: "Primary",
        status: "redeemed",
        beta_role: "tester",
        expires_at: "2026-05-18T00:00:00.000Z",
        redeemed_at: "2026-05-17T00:00:00.000Z",
        player_profile: null,
      },
      {
        invite_id: "invite-2",
        world_id: readyWorldId,
        world_name: "Ready World",
        worldline_id: "worldline-2",
        worldline_name: "Primary",
        status: "redeemed",
        beta_role: "tester",
        expires_at: "2026-05-19T00:00:00.000Z",
        redeemed_at: "2026-05-17T00:00:00.000Z",
        player_profile: playerProfileReady,
      },
    ],
    guidance: [
      "Use the player surface after identity setup.",
      "Report playback or generation failures to the operator.",
    ],
  },
  loadError: null,
};
