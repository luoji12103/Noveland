import { afterEach, describe, expect, it, vi } from "vitest";

import { login, logout, readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_HEADER_NAME } from "@/lib/auth/types";

describe("auth client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("maps csrf and login responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "csrf-token" }))
      .mockResolvedValueOnce(
        jsonResponse({
          user_id: "user-1",
          email: "admin@example.test",
          display_name: "Admin",
          roles: ["platform_admin"],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestCsrf()).resolves.toEqual({ csrf_token: "csrf-token" });
    await expect(
      login({ email: "admin@example.test", password: "correct-password" }),
    ).resolves.toMatchObject({ email: "admin@example.test" });

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({
          email: "admin@example.test",
          password: "correct-password",
        }),
      }),
    );
  });

  it("raises typed status errors for failed login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Invalid email or password" }, 401)),
    );

    await expect(
      login({ email: "admin@example.test", password: "wrong-password" }),
    ).rejects.toMatchObject({ status: 401 });
  });

  it("sends csrf header when logging out", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await logout();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: { [CSRF_HEADER_NAME]: "csrf-token" },
      }),
    );
  });

  it("reads cookies by exact name", () => {
    expect(readCookie("noveland_csrf", "other=1; noveland_csrf=token%201")).toBe("token 1");
    expect(readCookie("missing", "other=1; noveland_csrf=token")).toBeNull();
  });
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
