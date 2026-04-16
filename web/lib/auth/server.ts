import { headers } from "next/headers";

import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import type { AuthSubject } from "@/lib/auth/types";

export async function getCurrentSubject(): Promise<AuthSubject | null> {
  const requestHeaders = await headers();
  const cookieHeader = requestHeaders.get("cookie");

  try {
    const response = await fetch(`${getAuthApiBaseUrl()}/auth/me`, {
      headers: cookieHeader === null ? undefined : { cookie: cookieHeader },
      cache: "no-store",
    });
    if (response.status === 401) {
      return null;
    }
    if (!response.ok) {
      throw new Error(`auth subject lookup failed with status ${response.status}`);
    }
    return (await response.json()) as AuthSubject;
  } catch {
    return null;
  }
}
