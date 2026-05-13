import type { AuthSubject } from "@/lib/auth/types";

export type AdminRouteGuardResult =
  | {
      status: "redirect";
      href: string;
    }
  | {
      status: "forbidden";
      message: string;
      subject: AuthSubject;
    }
  | {
      status: "allowed";
      subject: AuthSubject;
    };

export function requirePlatformAdmin(
  subject: AuthSubject | null,
  resourceLabel: string,
): AdminRouteGuardResult {
  if (subject === null) {
    return { status: "redirect", href: "/login" };
  }
  if (!subject.roles.includes("platform_admin")) {
    return {
      status: "forbidden",
      message: `${resourceLabel} is available to platform administrators.`,
      subject,
    };
  }
  return { status: "allowed", subject };
}
