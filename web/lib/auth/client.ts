import {
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
  type AuthSubject,
  type CsrfResponse,
  type LoginInput,
} from "@/lib/auth/types";

export class AuthClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AuthClientError";
  }
}

export async function requestCsrf(): Promise<CsrfResponse> {
  const response = await fetch("/api/auth/csrf", {
    credentials: "include",
    cache: "no-store",
  });
  return parseJsonResponse<CsrfResponse>(response, "Unable to prepare sign in.");
}

export async function login(input: LoginInput): Promise<AuthSubject> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(input),
  });
  return parseJsonResponse<AuthSubject>(response, "Sign in failed.");
}

export async function currentSubject(): Promise<AuthSubject> {
  const response = await fetch("/api/auth/me", {
    credentials: "include",
    cache: "no-store",
  });
  return parseJsonResponse<AuthSubject>(response, "Session is not active.");
}

export async function logout(): Promise<void> {
  const csrfToken = readCookie(CSRF_COOKIE_NAME) ?? "";
  const response = await fetch("/api/auth/logout", {
    method: "POST",
    headers: { [CSRF_HEADER_NAME]: csrfToken },
    credentials: "include",
  });
  if (!response.ok) {
    throw new AuthClientError("Sign out failed.", response.status);
  }
}

export function readCookie(name: string, cookieString = document.cookie): string | null {
  const cookiePrefix = `${name}=`;
  const cookie = cookieString
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(cookiePrefix));
  if (cookie === undefined) {
    return null;
  }
  return decodeURIComponent(cookie.slice(cookiePrefix.length));
}

async function parseJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T;
  }

  const detail = await errorDetail(response);
  throw new AuthClientError(detail ?? fallbackMessage, response.status);
}

async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}
