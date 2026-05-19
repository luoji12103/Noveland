import { headers } from "next/headers";

import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import type { PrivateBetaOnboardingStatus } from "@/lib/private-beta/types";

export type PrivateBetaOnboardingData = {
  status: PrivateBetaOnboardingStatus | null;
  loadError: string | null;
};

export async function getPrivateBetaOnboardingData(): Promise<PrivateBetaOnboardingData> {
  const requestHeaders = await headers();
  const cookieHeader = requestHeaders.get("cookie");
  try {
    const response = await fetch(`${getAuthApiBaseUrl()}/private-beta/onboarding`, {
      headers: cookieHeader === null ? undefined : { cookie: cookieHeader },
      cache: "no-store",
    });
    if (response.status === 401) {
      throw new Error("unauthenticated");
    }
    if (!response.ok) {
      return { status: null, loadError: "Private beta onboarding is unavailable." };
    }
    return {
      status: (await response.json()) as PrivateBetaOnboardingStatus,
      loadError: null,
    };
  } catch {
    return { status: null, loadError: "Private beta onboarding is unavailable." };
  }
}
