import { afterEach, describe, expect, it, vi } from "vitest";

import { bootstrapPrivateBetaPlayerProfile } from "@/lib/private-beta/client";

describe("private beta client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("encodes world API path segments when bootstrapping player profiles", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(playerProfileResult));
    vi.stubGlobal("fetch", fetchMock);

    const input = {
      worldline_id: "worldline-1",
      display_name: "Beta Tester",
      profile: { route: "private" },
    };

    await bootstrapPrivateBetaPlayerProfile("world/private?beta=true#frag", input);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe(
      "/api/worlds/world%2Fprivate%3Fbeta%3Dtrue%23frag/private-beta/onboarding/player-profile",
    );
    expect(request.method).toBe("POST");
    expect(request.credentials).toBe("include");
    expect(request.cache).toBe("no-store");
    expect((request.headers as Headers).get("Content-Type")).toBe("application/json");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(request.body).toBe(JSON.stringify(input));
  });

  it("normalizes sensitive backend error details", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          { detail: "Invite failed with promptSnapshotId snapshot-1 and rawPrompt in /models/private.gguf" },
          { status: 500 },
        ),
      ),
    );

    const input = {
      worldline_id: "worldline-1",
      display_name: "Beta Tester",
      profile: {},
    };

    await expect(bootstrapPrivateBetaPlayerProfile("world-1", input)).rejects.toMatchObject({
      message: "Private beta request failed.",
      status: 500,
    });
  });
});

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
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

const playerProfileResult = {
  access: {
    invite_id: "invite-1",
    world_id: "world-1",
    world_name: "Demo World",
    worldline_id: "worldline-1",
    worldline_name: "Primary",
    status: "redeemed",
    beta_role: "tester",
    expires_at: "2026-05-18T00:00:00.000Z",
    redeemed_at: "2026-05-17T00:00:00.000Z",
    player_profile: playerProfile,
  },
  player_profile: playerProfile,
};
