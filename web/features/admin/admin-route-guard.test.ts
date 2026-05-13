import { describe, expect, it } from "vitest";

import { requirePlatformAdmin } from "@/features/admin/admin-route-guard";
import type { AuthSubject } from "@/lib/auth/types";

describe("admin route guard", () => {
  it("redirects anonymous actors to login", () => {
    expect(requirePlatformAdmin(null, "Runtime control")).toEqual({
      status: "redirect",
      href: "/login",
    });
  });

  it("returns a forbidden result for non-platform admins", () => {
    const subject: AuthSubject = {
      user_id: "user-1",
      email: "member@example.test",
      display_name: "Member",
      roles: [],
    };

    expect(requirePlatformAdmin(subject, "Provider management")).toEqual({
      status: "forbidden",
      message: "Provider management is available to platform administrators.",
      subject,
    });
  });

  it("allows platform admins", () => {
    const subject: AuthSubject = {
      user_id: "user-1",
      email: "admin@example.test",
      display_name: "Admin",
      roles: ["platform_admin"],
    };

    expect(requirePlatformAdmin(subject, "Provider management")).toEqual({
      status: "allowed",
      subject,
    });
  });
});
