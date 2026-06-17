import { readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from "@/lib/auth/types";
import { normalizeBackendErrorDetail } from "@/lib/safe-error-detail";

export class AdminClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AdminClientError";
  }
}

export type AdminRequestOptions = {
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  csrf?: boolean;
};

export async function adminRequest<T>(
  path: string,
  options: AdminRequestOptions,
): Promise<T> {
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

  if (response.status === 204) {
    return undefined as T;
  }
  if (response.ok) {
    return (await response.json()) as T;
  }

  throw new AdminClientError((await errorDetail(response)) ?? "Admin request failed.", response.status);
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
    if (typeof body.detail === "string") {
      return normalizeBackendErrorDetail(body.detail, "Admin request failed.");
    }
    if (body.detail !== null && typeof body.detail === "object" && !Array.isArray(body.detail)) {
      const detail = body.detail as Record<string, unknown>;
      if (typeof detail.message === "string") {
        return normalizeBackendErrorDetail(detail.message, "Admin request failed.");
      }
    }
  } catch {
    return null;
  }
  return null;
}
