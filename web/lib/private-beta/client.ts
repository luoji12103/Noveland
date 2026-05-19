import { readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from "@/lib/auth/types";
import type {
  PrivateBetaOnboardingStatus,
  PrivateBetaPlayerProfileInput,
  PrivateBetaPlayerProfileResult,
  PrivateBetaRedeemResult,
} from "@/lib/private-beta/types";
import { WorldClientError } from "@/lib/worlds/client";

export function redeemPrivateBetaInvite(token: string): Promise<PrivateBetaRedeemResult> {
  return privateBetaRequest<PrivateBetaRedeemResult>("/api/private-beta/invites/redeem", {
    method: "POST",
    body: { token },
    csrf: true,
  });
}

export function getPrivateBetaOnboardingStatus(): Promise<PrivateBetaOnboardingStatus> {
  return privateBetaRequest<PrivateBetaOnboardingStatus>("/api/private-beta/onboarding", {
    method: "GET",
  });
}

export function bootstrapPrivateBetaPlayerProfile(
  worldId: string,
  input: PrivateBetaPlayerProfileInput,
): Promise<PrivateBetaPlayerProfileResult> {
  return privateBetaRequest<PrivateBetaPlayerProfileResult>(
    `/api/worlds/${worldId}/private-beta/onboarding/player-profile`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

type RequestOptions = {
  method: "GET" | "POST";
  body?: unknown;
  csrf?: boolean;
};

async function privateBetaRequest<T>(path: string, options: RequestOptions): Promise<T> {
  const headers = new Headers();
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.csrf === true) {
    headers.set(CSRF_HEADER_NAME, await csrfToken());
  }

  const response = await fetch(path, {
    method: options.method,
    headers,
    credentials: "include",
    cache: "no-store",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (response.ok) {
    return (await response.json()) as T;
  }
  const detail = await errorDetail(response);
  throw new WorldClientError(detail ?? "Private beta request failed.", response.status);
}

async function csrfToken(): Promise<string> {
  const existingToken = readCookie(CSRF_COOKIE_NAME);
  if (existingToken !== null) {
    return existingToken;
  }
  const response = await requestCsrf();
  return response.csrf_token;
}

async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}
